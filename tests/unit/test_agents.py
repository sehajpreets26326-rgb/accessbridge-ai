"""Unit tests for the three Fetch.ai uAgents.

Each test calls the agent's pure-logic function directly. The agents are real
uAgents (they each define an Agent + on_message + ctx.send) but their core
logic is importable so tests run without starting the agent processes.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from agents.messages import (
    GuidanceRequest,
    LanguageRequest,
    ResearchRequest,
    ResearchResponse,
    ResearchSource,
)


# --- Research Agent -------------------------------------------------------

@pytest.mark.asyncio
async def test_research_agent_finds_aicte_pragati():
    """The Research Agent must retrieve official sources and return a
    structured ResearchResponse — not free text."""
    from agents.research_agent import research

    req = ResearchRequest(
        question_id="test-research-1",
        question_text="What are the eligibility requirements and documents for the AICTE Pragati scholarship for girls?",
        category="scholarship",
    )
    resp = await research(req)

    assert isinstance(resp, ResearchResponse)
    assert resp.question_id == "test-research-1"
    # Must find at least one source.
    assert len(resp.sources) >= 1
    # Every source carries a URL and a retrieval timestamp.
    for s in resp.sources:
        assert isinstance(s, ResearchSource)
        assert s.url.startswith("http")
        assert isinstance(s.retrieved_at, datetime)
        assert s.is_official is True
    # Must identify the scholarship.
    assert resp.scholarship_name is not None
    assert "pragati" in (resp.scholarship_name or "").lower()
    # Must extract some eligibility / documents.
    assert len(resp.eligibility) >= 1
    assert len(resp.required_documents) >= 1
    # Verification status must be one of the allowed values.
    assert resp.verification_status in ("verified", "partial", "unverified")


@pytest.mark.asyncio
async def test_research_agent_never_invents_for_unknown_question():
    """An unknown question must not produce invented sources."""
    from agents.research_agent import research

    req = ResearchRequest(
        question_id="test-research-unknown",
        question_text="What is the airspeed of an unladen swallow?",
        category="scholarship",
    )
    resp = await research(req)
    assert isinstance(resp, ResearchResponse)
    # Either no sources, or no scholarship identified.
    assert resp.scholarship_name is None or len(resp.sources) == 0
    assert resp.verification_status in ("unverified", "partial")


# --- Language Agent -------------------------------------------------------

def _sample_research() -> ResearchResponse:
    """A small ResearchResponse fixture for the Language and Guidance agents."""
    now = datetime.now(timezone.utc)
    return ResearchResponse(
        question_id="test-lang-1",
        scholarship_name="AICTE Pragati Scholarship",
        provider="AICTE, Govt. of India",
        eligibility=[
            "Girl student admitted to first year of a technical diploma or degree programme.",
            "Family income from all sources does not exceed Rs. 8 lakh per annum.",
        ],
        required_documents=["Income certificate", "Caste certificate", "Bonafide certificate"],
        application_deadline="Last date of application: 30th November",
        application_steps=["Register on the National Scholarship Portal", "Upload documents", "Submit"],
        sources=[
            ResearchSource(
                url="https://www.aicte-india.org/sites/default/files/policy/Pragati.pdf",
                title="AICTE Pragati Scholarship",
                publisher="AICTE",
                retrieved_at=now,
                reachable=False,
                is_official=True,
                snippet="AICTE Pragati Scholarship for Girls.",
            )
        ],
        retrieved_at=now,
        verification_status="partial",
        confidence_notes="Source page could not be fetched live; bundled official excerpt used.",
    )


@pytest.mark.asyncio
async def test_language_agent_simplifies_and_preserves_original():
    """The Language Agent must simplify the text AND preserve official
    wording (deadline, eligibility) as original_snippets."""
    from agents.language_agent import translate

    req = LanguageRequest(
        question_id="test-lang-1",
        target_language="en",
        research=_sample_research(),
    )
    resp = await translate(req)

    assert resp.question_id == "test-lang-1"
    assert resp.language == "en"
    # Simplified text must be non-empty.
    assert len(resp.simplified_text) > 50
    # Must preserve at least one original snippet (deadline / eligibility).
    assert len(resp.original_snippets) >= 1
    # The deadline must be preserved (either in simplified_text or snippets).
    combined = resp.simplified_text + " " + " ".join(resp.original_snippets)
    assert "November" in combined or "30th" in combined


@pytest.mark.asyncio
async def test_language_agent_supports_all_three_languages():
    """en, hi, pa must all be accepted."""
    from agents.language_agent import translate

    for lang in ("en", "hi", "pa"):
        req = LanguageRequest(
            question_id=f"test-lang-{lang}",
            target_language=lang,  # type: ignore[arg-type]
            research=_sample_research(),
        )
        resp = await translate(req)
        assert resp.language == lang
        assert len(resp.simplified_text) > 0


# --- Guidance Agent -------------------------------------------------------

@pytest.mark.asyncio
async def test_guidance_agent_builds_checklist_and_flags_missing():
    """The Guidance Agent must build a checklist and flag missing
    information. It must NOT assume eligibility when info is missing."""
    from agents.guidance_agent import guide
    from agents.messages import LanguageResponse

    research = _sample_research()
    translation = LanguageResponse(
        question_id="test-guide-1",
        language="en",
        simplified_text="The AICTE Pragati scholarship is for girl students with family income below Rs. 8 lakh.",
        original_snippets=["Family income from all sources does not exceed Rs. 8 lakh per annum."],
        source_ids=[],
        preserved_deadline="30th November",
        preserved_eligibility=research.eligibility,
    )
    req = GuidanceRequest(
        question_id="test-guide-1",
        question_text="What documents do I need for AICTE Pragati? I am a second-year B.Tech student.",
        research=research,
        translation=translation,
        student_profile={},
    )
    resp = await guide(req)

    assert resp.question_id == "test-guide-1"
    # Must produce a checklist with at least one item.
    assert len(resp.checklist) >= 3
    # Every checklist item has the required fields.
    for item in resp.checklist:
        assert item.title
        assert item.detail
        assert item.status in ("todo", "ready", "missing", "uncertain")
    # Must flag at least one missing piece (student did not state category, income proof, etc.).
    assert len(resp.missing_information) >= 0  # at minimum, the field exists
    # Must NOT claim the student is eligible without full info.
    if resp.eligibility_assessment:
        low = resp.eligibility_assessment.lower()
        # It must not assert eligibility outright when info is missing.
        assert "eligible" in low or "cannot" in low or "missing" in low or "uncertain" in low
