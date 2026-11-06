"""Fetch.ai uAgent: Guidance Agent.

Responsibilities:
- Receive verified research + simplified translation.
- Generate a personalised application checklist based ONLY on information the
  student has provided.
- Organise application steps, highlight missing information, identify
  unanswered questions.
- Prepare a final response for human review.
- NEVER assume a student is eligible if required information is missing.

Runs independently:

    python -m agents.guidance_agent

Core logic is importable as `guide()` for the orchestrator and tests.
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

from agents.messages import (  # noqa: E402
    ChecklistItem,
    GuidanceRequest,
    GuidanceResponse,
    LanguageResponse,
    ResearchResponse,
)

log = logging.getLogger("accessbridge.guidance_agent")


SYSTEM_PROMPT = """You are the Guidance Agent of AccessBridge AI.

You receive (a) the original student question, (b) structured research from the
Research Agent, and (c) the simplified translation from the Language Agent.

Your job is to build a personal application checklist that the student can act
on. Rules:

1. Use ONLY information present in the research. Do NOT invent documents,
   deadlines, or steps.
2. If the student has not stated their category, income, or domicile, mark the
   relevant checklist items as "missing" or "uncertain" — do NOT assume
   eligibility.
3. Highlight what is still unanswered (e.g. "Is the student a girl student?",
   "What is the family income?").
4. Add an `eligibility_assessment` that explicitly says whether the student
   appears eligible, appears ineligible, or cannot be assessed yet.
5. Add `uncertainty_warnings` whenever verification_status is not "verified"
   or a key field is missing.
6. Output STRICT JSON. No prose outside JSON."""


def _seed() -> str:
    return os.environ.get("ACCESSBRIDGE_GUIDANCE_SEED", "accessbridge-guidance-seed-v1")


agent = Agent(
    name="accessbridge-guidance-agent",
    seed=_seed(),
    port=int(os.environ.get("ACCESSBRIDGE_GUIDANCE_PORT", "8003")),
    endpoint=[os.environ.get("ACCESSBRIDGE_GUIDANCE_ENDPOINT", "http://localhost:8003/submit")],
)


@agent.on_message(model=GuidanceRequest)
async def handle_guidance(ctx: Context, sender: str, msg: GuidanceRequest) -> None:
    ctx.logger.info(f"Guidance request received for question {msg.question_id}")
    result = await guide(msg)
    await ctx.send(sender, result)


async def guide(request: GuidanceRequest) -> GuidanceResponse:
    """Build the application checklist for human review."""
    research: ResearchResponse = request.research
    translation: LanguageResponse = request.translation

    extracted = await _llm_guide(request, research, translation) or _deterministic_guide(request, research, translation)
    return GuidanceResponse(
        question_id=request.question_id,
        checklist=[ChecklistItem(**c) if isinstance(c, dict) else c for c in extracted.get("checklist", [])],
        missing_information=extracted.get("missing_information", []),
        unanswered_questions=extracted.get("unanswered_questions", []),
        eligibility_assessment=extracted.get("eligibility_assessment"),
        uncertainty_warnings=extracted.get("uncertainty_warnings", []),
        summary=extracted.get("summary"),
        correlation_id=request.correlation_id,
        task_id=request.task_id,
    )


async def _llm_guide(request: GuidanceRequest, research: ResearchResponse, translation: LanguageResponse) -> dict[str, Any] | None:
    try:
        from backend.app.services.llm import build_llm_client, chat_json
        from backend.app.config import settings
        if not settings.effective_llm_api_key():
            return None
        client = build_llm_client()
        user_prompt = (
            f"STUDENT QUESTION:\n{request.question_text}\n\n"
            f"STUDENT PROFILE:\n{json.dumps(request.student_profile, ensure_ascii=False)}\n\n"
            f"RESEARCH:\n{research.model_dump_json(indent=2)}\n\n"
            f"TRANSLATION:\n{translation.model_dump_json(indent=2)}\n\n"
            "Produce STRICT JSON with keys:\n"
            '{"checklist": [{"title": string, "detail": string, '
            '"status": "todo|ready|missing|uncertain", "source_url": string|null}], '
            '"missing_information": [string], "unanswered_questions": [string], '
            '"eligibility_assessment": string, "uncertainty_warnings": [string], '
            '"summary": string}\n\n'
            "Rules: be conservative. If you do not know the student's category/income/domicile, "
            "do not declare them eligible. Each checklist item should be actionable."
        )
        raw = chat_json(client, SYSTEM_PROMPT, user_prompt, max_tokens=1200)
        return _parse_json(raw)
    except Exception as exc:
        log.warning("LLM guidance failed, falling back to deterministic: %s", exc)
        return None


# --- Deterministic fallback -----------------------------------------------

def _deterministic_guide(request: GuidanceRequest, research: ResearchResponse, translation: LanguageResponse) -> dict[str, Any]:
    profile = request.student_profile or {}
    q = (request.question_text or "").lower()
    checklist: list[dict[str, Any]] = []
    missing: list[str] = []
    unanswered: list[str] = []
    warnings: list[str] = []

    primary_url = research.sources[0].url if research.sources else None

    # 1. Confirm the scholarship matches the student's situation.
    checklist.append({
        "title": "Confirm this is the right scholarship",
        "detail": (research.scholarship_name or "the identified scholarship") + " — read the official page.",
        "status": "todo",
        "source_url": primary_url,
    })

    # 2. Eligibility — gather what we don't know.
    elig_keywords = {
        "girl": ("girl", "female", "woman"),
        "category_sc": ("scheduled caste", " sc "),
        "category_obc": ("obc", "backward class"),
        "ner": ("north east", "arunachal", "assam", "manipur", "meghalaya", "mizoram", "nagaland", "sikkim", "tripura"),
        "disability": ("disability", "specially-abled", "saksham"),
        "wb": ("west bengal",),
    }
    research_text = (research.model_dump_json()).lower()
    if any(k in research_text for k in elig_keywords["girl"]) and "girl" not in q:
        unanswered.append("Is the student a girl student? (This scholarship is for girl students.)")
        missing.append("Gender / Pragati eligibility confirmation")
    if "income" in research_text and not profile.get("family_income"):
        unanswered.append("What is the student's family income? (This scholarship has an income limit.)")
        missing.append("Family income certificate")
    if any(k in research_text for k in elig_keywords["ner"]) and not profile.get("domicile"):
        unanswered.append("Is the student a domicile of a North-East state?")
        missing.append("NER domicile certificate")
    if any(k in research_text for k in elig_keywords["wb"]) and not profile.get("domicile"):
        unanswered.append("Is the student a domicile of West Bengal?")
        missing.append("West Bengal domicile certificate")

    # 3. Documents.
    for doc in research.required_documents or ["Income certificate", "Previous marksheet", "Bank account details"]:
        status = "missing" if "income" in doc.lower() and "income" in " ".join(missing).lower() else "todo"
        checklist.append({
            "title": f"Prepare: {doc}",
            "detail": doc,
            "status": status,
            "source_url": primary_url,
        })

    # 4. Application steps.
    for i, step in enumerate(research.application_steps or ["Apply on the official portal", "Upload documents", "Submit before deadline"], 1):
        checklist.append({
            "title": f"Step {i}",
            "detail": step,
            "status": "todo",
            "source_url": primary_url,
        })

    # 5. Deadline.
    if research.application_deadline:
        checklist.append({
            "title": "Submit before deadline",
            "detail": research.application_deadline,
            "status": "todo",
            "source_url": primary_url,
        })
    else:
        checklist.append({
            "title": "Confirm the deadline",
            "detail": "Deadline not stated in the official source. Check the official portal.",
            "status": "uncertain",
            "source_url": primary_url,
        })
        unanswered.append("What is the application deadline for this year?")
        warnings.append("Deadline not found in the retrieved official source.")

    # 6. Eligibility assessment.
    if missing:
        eligibility = (
            "We cannot confirm eligibility yet. The following information is still missing: "
            + "; ".join(missing)
            + ". Do not assume eligibility until these are provided."
        )
    elif research.verification_status == "verified":
        eligibility = "Based on the official source, the student appears to meet the stated criteria. Final confirmation is at the discretion of the scholarship authority."
    else:
        eligibility = "Eligibility cannot be confirmed automatically — the official source was not fully verified. A coordinator should review before advising the student."

    if research.verification_status != "verified":
        warnings.append("The official source was not fully verified live. Confirm on the official portal before advising.")

    summary = (
        f"Prepared a {len(checklist)}-step application checklist for "
        f"{research.scholarship_name or 'the requested scholarship'}. "
        f"{len(missing)} item(s) need clarification before eligibility can be confirmed."
    )

    return {
        "checklist": checklist,
        "missing_information": missing,
        "unanswered_questions": unanswered,
        "eligibility_assessment": eligibility,
        "uncertainty_warnings": warnings,
        "summary": summary,
    }


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
    log.info("Starting AccessBridge Guidance uAgent on port %s", agent.port if hasattr(agent, "port") else "?")
    agent.run()
