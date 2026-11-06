"""Fetch.ai uAgent: Language Agent.

Responsibilities:
- Receive structured research results.
- Simplify complicated official language.
- Translate into Hindi, Punjabi or English.
- Preserve important dates, eligibility criteria and conditions.
- Return both the simplified explanation and original official wording.

Runs independently:

    python -m agents.language_agent

Core logic is importable as `translate()` for the orchestrator and tests.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from uagents import Agent, Context

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.messages import LanguageRequest, LanguageResponse, ResearchResponse  # noqa: E402

log = logging.getLogger("accessbridge.language_agent")


LANG_LABELS = {"en": "English", "hi": "Hindi", "pa": "Punjabi"}


SYSTEM_PROMPT = """You are the Language Agent of AccessBridge AI.

You receive structured research about a scholarship and a target language
(en, hi, pa). Your job:

1. Simplify the official language so a student can understand it, without
   changing any fact, date, eligibility condition, amount, or document name.
2. Translate the simplified explanation into the target language.
3. Preserve the OFFICIAL wording for: deadline, income limit, eligibility
   conditions, and amounts — quote them in `original_snippets`.
4. Never add information that is not in the research input.
5. If `research.verification_status` is not "verified", add a short note in
   `notes` reminding that the source was not fully verified.
6. Output STRICT JSON. No prose outside JSON.

Target language names: en=English, hi=Hindi, pa=Punjabi."""


def _seed() -> str:
    return os.environ.get("ACCESSBRIDGE_LANGUAGE_SEED", "accessbridge-language-seed-v1")


agent = Agent(
    name="accessbridge-language-agent",
    seed=_seed(),
    port=int(os.environ.get("ACCESSBRIDGE_LANGUAGE_PORT", "8002")),
    endpoint=[os.environ.get("ACCESSBRIDGE_LANGUAGE_ENDPOINT", "http://localhost:8002/submit")],
)


@agent.on_message(model=LanguageRequest)
async def handle_language(ctx: Context, sender: str, msg: LanguageRequest) -> None:
    ctx.logger.info(f"Language request received for question {msg.question_id} ({LANG_LABELS.get(msg.target_language)})")
    result = await translate(msg)
    await ctx.send(sender, result)


async def translate(request: LanguageRequest) -> LanguageResponse:
    """Simplify + translate the research into the target language."""
    research: ResearchResponse = request.research
    if research.verification_status == "unverified" or not (
        research.scholarship_name or research.eligibility or research.application_steps
    ):
        return LanguageResponse(
            question_id=request.question_id,
            language=request.target_language,
            simplified_text=_unverified_text(request.target_language),
            original_snippets=[],
            source_ids=[],
            preserved_deadline=research.application_deadline,
            preserved_eligibility=research.eligibility,
            notes="Research Agent could not verify official information; no translation produced.",
            correlation_id=request.correlation_id,
            task_id=request.task_id,
        )

    extracted = await _llm_translate(request, research) or _deterministic_translate(request, research)
    return LanguageResponse(
        question_id=request.question_id,
        language=request.target_language,
        simplified_text=extracted.get("simplified_text", ""),
        original_snippets=extracted.get("original_snippets", []),
        source_ids=[],
        preserved_deadline=research.application_deadline,
        preserved_eligibility=research.eligibility,
        notes=extracted.get("notes"),
        correlation_id=request.correlation_id,
        task_id=request.task_id,
    )


async def _llm_translate(request: LanguageRequest, research: ResearchResponse) -> dict[str, Any] | None:
    try:
        from backend.app.services.llm import build_llm_client, chat_json
        from backend.app.config import settings
        if not settings.effective_llm_api_key():
            return None
        client = build_llm_client()
        research_json = research.model_dump_json(indent=2)
        user_prompt = (
            f"TARGET LANGUAGE: {LANG_LABELS[request.target_language]} ({request.target_language})\n\n"
            f"STRUCTURED RESEARCH:\n{research_json}\n\n"
            "Produce STRICT JSON with keys:\n"
            '{"simplified_text": string (the simplified explanation in the target language), '
            '"original_snippets": [string] (official wording for deadline, income limit, '
            'eligibility, amounts, quoted verbatim), '
            '"notes": string|null}\n\n'
            "Rules: keep all dates and amounts unchanged. Never invent. If a field was unknown, "
            "say so plainly in the target language."
        )
        raw = chat_json(client, SYSTEM_PROMPT, user_prompt, max_tokens=1000)
        return _parse_json(raw)
    except Exception as exc:
        log.warning("LLM translation failed, falling back to deterministic: %s", exc)
        return None


# --- Deterministic fallback -----------------------------------------------

_INTRO = {
    "en": "Here is a plain-language summary of this scholarship, based on official sources.",
    "hi": "यह छात्रवृत्ति का सरल भाषा में सारांश है, जो आधिकारिक स्रोतों पर आधारित है।",
    "pa": "ਇਹ ਸਕਾਲਰਸ਼ਿਪ ਦਾ ਸਧਾਰਨ ਭਾਸ਼ਾ ਵਿੱਚ ਸਾਰ ਹੈ, ਅਧਿਕਾਰਤ ਸਰੋਤਾਂ ਉੱਤੇ ਅਧਾਰਤ।",
}
_NAME_LABEL = {
    "en": "Scholarship",
    "hi": "छात्रवृत्ति",
    "pa": "ਸਕਾਲਰਸ਼ਿਪ",
}
_PROVIDER_LABEL = {
    "en": "Provider",
    "hi": "प्रदाता",
    "pa": "ਪ੍ਰਦਾਤਾ",
}
_ELIG_LABEL = {
    "en": "Who can apply",
    "hi": "कौन आवेदन कर सकता है",
    "pa": "ਕੌਣ ਅਪਲਾਈ ਕਰ ਸਕਦਾ ਹੈ",
}
_DOCS_LABEL = {
    "en": "Documents you will need",
    "hi": "आवश्यक दस्तावेज़",
    "pa": "ਲੋੜੀਂਦੇ ਦਸਤਾਵੇਜ਼",
}
_STEPS_LABEL = {
    "en": "How to apply",
    "hi": "आवेदन कैसे करें",
    "pa": "ਕਿਵੇਂ ਅਪਲਾਈ ਕਰੀਏ",
}
_DEADLINE_LABEL = {
    "en": "Deadline",
    "hi": "अंतिम तिथि",
    "pa": "ਅੰਤਿਮ ਤਾਰੀਖ",
}
_NOTE_LABEL = {
    "en": "Note",
    "hi": "ध्यान दें",
    "pa": "ਨੋਟ",
}


def _deterministic_translate(request: LanguageRequest, research: ResearchResponse) -> dict[str, Any]:
    """When no LLM is configured, produce a faithful template-based summary."""
    lang = request.target_language
    parts: list[str] = [_INTRO[lang], ""]

    if research.scholarship_name:
        parts.append(f"{_NAME_LABEL[lang]}: {research.scholarship_name}")
    if research.provider:
        parts.append(f"{_PROVIDER_LABEL[lang]}: {research.provider}")

    if research.eligibility:
        parts.append("")
        parts.append(_ELIG_LABEL[lang] + ":")
        for e in research.eligibility:
            parts.append(f"  - {e}")

    if research.required_documents:
        parts.append("")
        parts.append(_DOCS_LABEL[lang] + ":")
        for d in research.required_documents:
            parts.append(f"  - {d}")

    if research.application_steps:
        parts.append("")
        parts.append(_STEPS_LABEL[lang] + ":")
        for i, s in enumerate(research.application_steps, 1):
            parts.append(f"  {i}. {s}")

    if research.application_deadline:
        parts.append("")
        parts.append(f"{_DEADLINE_LABEL[lang]}: {research.application_deadline}")

    if research.verification_status != "verified":
        parts.append("")
        parts.append(
            _NOTE_LABEL[lang]
            + ": "
            + _UNVERIFIED_NOTE[lang]
        )

    snippets: list[str] = []
    if research.application_deadline:
        snippets.append(f"Deadline (official): {research.application_deadline}")
    snippets.extend(research.eligibility[:3])

    return {
        "simplified_text": "\n".join(parts),
        "original_snippets": snippets,
        "notes": "Produced by deterministic fallback (no LLM). Verify against the official source." if research.verification_status != "verified" else None,
    }


_UNVERIFIED_NOTE = {
    "en": "The official source could not be fully verified live. Please confirm details on the official portal before applying.",
    "hi": "आधिकारिक स्रोत का पूर्ण रूप से वेरिफिकेशन नहीं हो पाया। आवेदन से पहले आधिकारिक पोर्टल पर जानकारी की पुष्टि करें।",
    "pa": "ਅਧਿਕਾਰਤ ਸਰੋਤ ਪੂਰੀ ਤਰ੍ਹਾਂ ਵੈਰੀਫਾਈ ਨਹੀਂ ਹੋ ਸਕਿਆ। ਅਪਲਾਈ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਅਧਿਕਾਰਤ ਪੋਰਟਲ 'ਤੇ ਜਾਣਕਾਰੀ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ।",
}


def _unverified_text(lang: str) -> str:
    return _UNVERIFIED_NOTE.get(lang, _UNVERIFIED_NOTE["en"])


def _parse_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("Starting AccessBridge Language uAgent on port %s", agent.port if hasattr(agent, "port") else "?")
    agent.run()
