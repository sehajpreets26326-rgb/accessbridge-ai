"""Tests for evidence traceability: per-claim evidence refs, source freshness,
conflict detection, duplicate detection, and unsupported-claim highlighting.

These verify PRIORITY 2 (source reliability) from the upgrade spec.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agents.messages import ClaimEvidence, ResearchRequest, ResearchResponse


@pytest.mark.asyncio
async def test_research_produces_evidence_for_every_claim():
    """Every eligibility/document/deadline claim must have a ClaimEvidence ref."""
    from agents.research_agent import research

    req = ResearchRequest(
        question_id="test-evidence-1",
        question_text="What are the eligibility requirements and documents for the AICTE Pragati scholarship?",
    )
    resp = await research(req)
    assert isinstance(resp, ResearchResponse)

    # Evidence must be a non-empty list when claims were extracted.
    if resp.eligibility or resp.required_documents:
        assert len(resp.evidence) >= 1
        for ev in resp.evidence:
            assert isinstance(ev, ClaimEvidence)
            assert ev.claim
            assert ev.claim_type in ("eligibility", "deadline", "document", "amount", "step", "other")
            assert ev.confidence in ("confirmed", "uncertain", "unavailable")


@pytest.mark.asyncio
async def test_evidence_links_claim_to_source_excerpt():
    """Each confirmed/uncertain evidence ref must carry a source URL and excerpt."""
    from agents.research_agent import research

    resp = await research(ResearchRequest(
        question_id="test-evidence-2",
        question_text="AICTE Pragati scholarship for girls eligibility",
    ))
    for ev in resp.evidence:
        if ev.confidence in ("confirmed", "uncertain"):
            assert ev.source_url.startswith("http")
            assert len(ev.excerpt) > 0
            assert ev.retrieved_at is not None


@pytest.mark.asyncio
async def test_unsupported_claims_marked_unavailable():
    """Claims with no matching source must be confidence=unavailable."""
    from agents.research_agent import research, _build_evidence

    # Build evidence from an extracted dict with a claim that no source contains.
    extracted = {
        "eligibility": ["This claim text does not appear in any official source."],
        "required_documents": [],
        "application_steps": [],
        "application_deadline": None,
    }
    from knowledge_base.retriever import retrieve
    retrieved = retrieve("AICTE Pragati", max_sources=1)
    evidence = _build_evidence(extracted, retrieved)
    assert len(evidence) == 1
    assert evidence[0].confidence == "unavailable"
    assert evidence[0].source_url == ""


@pytest.mark.asyncio
async def test_duplicate_source_detection():
    """When the same URL appears in multiple retrieved sources, it's flagged."""
    from agents.research_agent import _detect_duplicate_sources
    from knowledge_base.retriever import RetrievedSource
    from knowledge_base.sources import OfficialSource

    src = OfficialSource(key="x", name="X", publisher="P", url="https://dup.example.com",
                         region="IN", tags=("x",))
    now = datetime.now(timezone.utc)
    retrieved = [
        RetrievedSource(url="https://dup.example.com", title="A", publisher="P",
                        retrieved_at=now, reachable=True, is_official=True, snippet="s"),
        RetrievedSource(url="https://dup.example.com", title="B", publisher="P",
                        retrieved_at=now, reachable=True, is_official=True, snippet="s"),
        RetrievedSource(url="https://other.example.com", title="C", publisher="P",
                        retrieved_at=now, reachable=True, is_official=True, snippet="s"),
    ]
    dups = _detect_duplicate_sources(retrieved)
    assert "https://dup.example.com" in dups
    assert "https://other.example.com" not in dups


@pytest.mark.asyncio
async def test_conflict_detection_for_income_values():
    """When sources disagree on income limits, a conflict is recorded."""
    from agents.research_agent import _detect_conflicts
    from knowledge_base.retriever import RetrievedSource

    now = datetime.now(timezone.utc)
    retrieved = [
        RetrievedSource(url="https://a", title="A", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="Family income should not exceed Rs. 8 lakh per annum."),
        RetrievedSource(url="https://b", title="B", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="Income limit is Rs. 6 lakh per annum for this scheme."),
    ]
    conflicts = _detect_conflicts({}, retrieved)
    assert len(conflicts) >= 1
    assert "income" in conflicts[0].lower()


@pytest.mark.asyncio
async def test_no_conflict_when_sources_agree():
    """When sources state the same income value, no conflict is flagged."""
    from agents.research_agent import _detect_conflicts
    from knowledge_base.retriever import RetrievedSource

    now = datetime.now(timezone.utc)
    retrieved = [
        RetrievedSource(url="https://a", title="A", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="Income limit Rs. 8 lakh per annum."),
        RetrievedSource(url="https://b", title="B", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="The Rs. 8 lakh per annum income limit applies."),
    ]
    conflicts = _detect_conflicts({}, retrieved)
    assert conflicts == []


@pytest.mark.asyncio
async def test_research_response_carries_conflicts_and_duplicates(db_session):
    """The end-to-end workflow must persist conflicts + duplicates in the
    research execution trace."""
    from agents.orchestrator import run_workflow
    from backend.app.models import Question, QuestionStatus, AgentExecution, AgentName

    q = Question(
        question_text="Evidence integration test: AICTE Pragati scholarship for girls eligibility",
        language="en", category="scholarship", status=QuestionStatus.received,
    )
    db_session.add(q); db_session.commit(); db_session.refresh(q)
    await run_workflow(q.id, db_session)
    db_session.commit()

    research_exec = (
        db_session.query(AgentExecution)
        .filter_by(question_id=q.id, agent=AgentName.research)
        .first()
    )
    assert research_exec is not None
    assert research_exec.details is not None
    # The trace must include the new evidence/conflicts/duplicates keys.
    assert "evidence" in research_exec.details
    assert "conflicting_claims" in research_exec.details
    assert "duplicate_sources" in research_exec.details
