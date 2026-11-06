"""Fetch.ai uAgent: Research Agent.

Responsibilities:
- Understand the student question.
- Retrieve official scholarship sources (RAG via knowledge_base.retriever).
- Extract eligibility, documents, deadlines, application steps.
- Provide source URLs + retrieval timestamps.
- Distinguish verified vs uncertain information.

The agent is a real Fetch.ai uAgent (`Agent`, `on_message`, `ctx.send`) and can
run as an independent process:

    python -m agents.research_agent

Its core logic is also importable as `research()` so the orchestrator can run
it in-process for the demo and for tests.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uagents import Agent, Context

# Make sibling imports work both when run as a module and as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.messages import ResearchRequest, ResearchResponse, ResearchSource, ClaimEvidence  # noqa: E402
from knowledge_base import retrieve as kb_retrieve  # noqa: E402
from knowledge_base.sources import OfficialSource  # noqa: E402

log = logging.getLogger("accessbridge.research_agent")

SYSTEM_PROMPT = """You are the Research Agent of AccessBridge AI, a public-interest tool that helps
students understand scholarships and educational opportunities.

You receive (a) a student question and (b) text retrieved from one or more
official sources. Your job is to extract STRUCTURED, FACTUAL information from
the official text only. Rules:

1. Use ONLY information present in the provided official source text. If the
   text does not state a deadline, eligibility condition, document, or step,
   do NOT invent one — leave the field empty or mark it unknown.
2. Never invent a scholarship name, amount, or date.
3. Preserve exact official wording for important conditions (eligibility,
   deadline, income limit). Quote them verbatim where possible.
4. If the source text is empty or clearly not about the asked scholarship,
   return an empty structured object and set verification_status to "unverified".
5. Output STRICT JSON matching the requested schema. No prose outside JSON.

You are not the final answer to the student. Another agent simplifies your
output and a human coordinator reviews it before it reaches the student."""


def _seed() -> str:
    return os.environ.get("ACCESSBRIDGE_RESEARCH_SEED", "accessbridge-research-seed-v1")


agent = Agent(
    name="accessbridge-research-agent",
    seed=_seed(),
    port=int(os.environ.get("ACCESSBRIDGE_RESEARCH_PORT", "8001")),
    endpoint=[os.environ.get("ACCESSBRIDGE_RESEARCH_ENDPOINT", "http://localhost:8001/submit")],
)


@agent.on_message(model=ResearchRequest)
async def handle_research(ctx: Context, sender: str, msg: ResearchRequest) -> None:
    """Real uAgents on_message handler: runs the research and replies via ctx.send."""
    ctx.logger.info(f"Research request received for question {msg.question_id}")
    result = await research(msg)
    await ctx.send(sender, result)


async def research(request: ResearchRequest) -> ResearchResponse:
    """Pure business logic. Retrieves official sources and structures them.

    Uses an LLM (wrapped by Switch Trust guardrails) to extract structured
    fields from the retrieved official text. When no LLM is configured, falls
    back to a deterministic extractor so the workflow still completes.
    """
    retrieved = kb_retrieve(
        request.question_text,
        max_sources=3,
        timeout_seconds=_float_env("ACCESSBRIDGE_KB_TIMEOUT", 12.0),
        user_agent=os.environ.get(
            "ACCESSBRIDGE_KB_UA", "AccessBridgeAI/0.1 (+https://github.com/accessbridge-ai)"
        ),
        offline_fallback=_bool_env("ACCESSBRIDGE_KB_OFFLINE_FALLBACK", True),
    )

    sources = [
        ResearchSource(
            url=s.url,
            title=s.title,
            publisher=s.publisher,
            retrieved_at=s.retrieved_at,
            reachable=s.reachable,
            is_official=s.is_official,
            snippet=s.snippet,
        )
        for s in retrieved
    ]

    now = datetime.now(timezone.utc)

    if not sources:
        return ResearchResponse(
            question_id=request.question_id,
            retrieved_at=now,
            verification_status="unverified",
            confidence_notes="No official source matched this question in the curated knowledge base.",
            error=None,
        )

    corpus = "\n\n".join(
        f"--- SOURCE: {s.title or s.url} ({s.publisher or 'unknown'}) ---\n{s.raw_text or s.snippet or ''}"
        for s in retrieved
    )

    extracted = await _llm_extract(request, corpus, sources) or _deterministic_extract(retrieved)

    reachable = [s for s in sources if s.reachable]
    if reachable and all(s.reachable for s in sources):
        extracted["verification_status"] = extracted.get("verification_status") or "verified"
    elif reachable:
        extracted["verification_status"] = extracted.get("verification_status") or "partial"
    else:
        extracted["verification_status"] = extracted.get("verification_status") or "partial"
        extracted["confidence_notes"] = (
            (extracted.get("confidence_notes") or "")
            + " Source pages could not be fetched live; information is from bundled official excerpts."
        ).strip()

    # --- Evidence traceability: link each claim to its source excerpt ---
    evidence = _build_evidence(extracted, retrieved)
    # --- Duplicate source detection ---
    duplicates = _detect_duplicate_sources(retrieved)
    # --- Conflicting claim detection ---
    conflicts = _detect_conflicts(extracted, retrieved)

    return ResearchResponse(
        question_id=request.question_id,
        scholarship_name=extracted.get("scholarship_name"),
        provider=extracted.get("provider"),
        eligibility=extracted.get("eligibility", []),
        required_documents=extracted.get("required_documents", []),
        application_deadline=extracted.get("application_deadline"),
        application_steps=extracted.get("application_steps", []),
        sources=sources,
        evidence=evidence,
        retrieved_at=now,
        verification_status=extracted.get("verification_status", "partial"),
        confidence_notes=extracted.get("confidence_notes"),
        conflicting_claims=conflicts,
        duplicate_sources=duplicates,
        correlation_id=request.correlation_id,
        task_id=request.task_id,
    )


# --- Evidence traceability helpers ----------------------------------------

def _build_evidence(extracted: dict[str, Any], retrieved: list) -> list[ClaimEvidence]:
    """Link each extracted claim to the source excerpt it came from.

    For every eligibility condition, document, deadline and step, find the
    source whose raw text contains the claim text and record the exact
    excerpt. This is the trust contract: every claim has a source.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    evidence: list[ClaimEvidence] = []

    # Map claim_type → list of (claim_text) from the extracted dict.
    claim_groups = [
        ("eligibility", extracted.get("eligibility", [])),
        ("document", extracted.get("required_documents", [])),
        ("step", extracted.get("application_steps", [])),
    ]
    deadline = extracted.get("application_deadline")
    if deadline:
        claim_groups.append(("deadline", [deadline]))

    for claim_type, claims in claim_groups:
        for claim in claims:
            if not claim or not claim.strip():
                continue
            # Find the first source whose text contains this claim.
            best_src = None
            best_excerpt = None
            for src in retrieved:
                text = src.raw_text or src.snippet or ""
                if claim.strip().lower() in text.lower():
                    best_src = src
                    best_excerpt = _extract_snippet_around(text, claim, 200)
                    break
            if best_src:
                evidence.append(ClaimEvidence(
                    claim=claim.strip()[:300],
                    claim_type=claim_type,  # type: ignore[arg-type]
                    source_url=best_src.url,
                    source_title=best_src.title,
                    excerpt=best_excerpt or best_src.snippet or "",
                    retrieved_at=best_src.retrieved_at,
                    confidence="confirmed" if best_src.reachable else "uncertain",
                    notes=None if best_src.reachable else "Source not fetched live; from bundled excerpt.",
                ))
            else:
                # Claim has no matching source — mark as unavailable.
                evidence.append(ClaimEvidence(
                    claim=claim.strip()[:300],
                    claim_type=claim_type,  # type: ignore[arg-type]
                    source_url="",
                    source_title=None,
                    excerpt="",
                    retrieved_at=now,
                    confidence="unavailable",
                    notes="No supporting source excerpt found for this claim.",
                ))
    return evidence


def _extract_snippet_around(text: str, claim: str, width: int = 200) -> str:
    """Return a snippet of `width` chars centred on the first occurrence of `claim`."""
    idx = text.lower().find(claim.strip().lower())
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), idx + len(claim) + width // 2)
    return text[start:end].strip()


def _detect_duplicate_sources(retrieved: list) -> list[str]:
    """Return URLs that appear more than once in the retrieved sources."""
    from collections import Counter
    urls = [s.url for s in retrieved]
    return [url for url, count in Counter(urls).items() if count > 1]


def _detect_conflicts(extracted: dict[str, Any], retrieved: list) -> list[str]:
    """Detect claims where sources disagree on key values.

    For the MVP this checks: if the same key phrase (e.g. "income") appears
    with different numeric values across sources, flag it as a conflict.
    """
    conflicts: list[str] = []
    import re
    # Collect all income-like mentions across sources.
    income_pattern = re.compile(
        r"(?:rs\.?|₹|inr)\s?[\d,\.]+\s?(?:lakh|lakhs|crore)", re.IGNORECASE
    )
    seen_incomes: dict[str, set[str]] = {}
    for src in retrieved:
        text = src.raw_text or src.snippet or ""
        for m in income_pattern.finditer(text):
            key = "income_limit"
            seen_incomes.setdefault(key, set()).add(m.group(0).strip().lower())

    for key, values in seen_incomes.items():
        if len(values) > 1:
            conflicts.append(
                f"Multiple {key} values found across sources: {', '.join(sorted(values))}"
            )
    return conflicts


async def _llm_extract(request: ResearchRequest, corpus: str, sources: list[ResearchSource]) -> dict[str, Any] | None:
    """Use the LLM (Switch Trust-guarded) to extract a structured scholarship record."""
    try:
        from backend.app.services.llm import build_llm_client, chat_json
        from backend.app.config import settings
        if not settings.effective_llm_api_key():
            return None
        client = build_llm_client()
        user_prompt = (
            f"STUDENT QUESTION:\n{request.question_text}\n\n"
            f"OFFICIAL SOURCE TEXT:\n{corpus[:6000]}\n\n"
            "Extract a STRICT JSON object with these keys:\n"
            '{"scholarship_name": string|null, "provider": string|null, '
            '"eligibility": [string], "required_documents": [string], '
            '"application_deadline": string|null, "application_steps": [string], '
            '"verification_status": "verified|partial|unverified", '
            '"confidence_notes": string|null}\n\n'
            "Rules: only use facts present in the official source text. "
            "If a field is unknown, use null or an empty list. Never invent dates."
        )
        raw = chat_json(client, SYSTEM_PROMPT, user_prompt, max_tokens=900)
        return _parse_json(raw)
    except Exception as exc:
        log.warning("LLM extraction failed, falling back to deterministic extractor: %s", exc)
        return None


# --- Deterministic fallback (no LLM) --------------------------------------

_DEADLINE_RE = re.compile(
    r"\b(deadline|last date|closing date|apply by|on or before)\b[^.\n]{0,80}",
    re.IGNORECASE,
)
_INCOME_RE = re.compile(r"income[^.]{0,120}?(?:rs\.?|₹|inr)\s?[\d,\.]+\s?(?:lakh|lakhs|crore)", re.IGNORECASE)


def _deterministic_extract(retrieved: list) -> dict[str, Any]:
    """When no LLM is configured, extract obvious fields deterministically."""
    text = "\n".join((s.raw_text or s.snippet or "") for s in retrieved)
    eligibility: list[str] = []
    documents: list[str] = []
    steps: list[str] = []
    deadline: str | None = None
    name: str | None = None
    provider: str | None = None

    if retrieved:
        first = retrieved[0]
        name = first.title
        provider = first.publisher

    # Eligibility lines: lines mentioning "eligible", "should be", "must be".
    for line in text.splitlines():
        low = line.lower()
        if any(k in low for k in ("eligible", "should be", "must be", "family income")):
            eligibility.append(line.strip()[:200])
        if any(k in low for k in ("certificate", "marksheet", "bank", "income proof", "bonafide", "aadhaar")):
            documents.append(line.strip()[:200])
        if any(k in low for k in ("apply", "register", "submit", "upload", "verify")):
            steps.append(line.strip()[:200])

    m = _DEADLINE_RE.search(text)
    if m:
        deadline = m.group(0)[:120]

    income = _INCOME_RE.search(text)
    if income:
        eligibility.append(income.group(0).strip()[:200])

    return {
        "scholarship_name": name,
        "provider": provider,
        "eligibility": eligibility[:8],
        "required_documents": documents[:8],
        "application_deadline": deadline,
        "application_steps": steps[:8],
        "verification_status": "partial",
        "confidence_notes": "Extracted deterministically (no LLM). Verify against the official source.",
    }


def _parse_json(text: str) -> dict[str, Any] | None:
    """Parse the first {...} block out of an LLM response."""
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


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("Starting AccessBridge Research uAgent on port %s", agent.port if hasattr(agent, "port") else "?")
    agent.run()
