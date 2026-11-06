"""Integration test for the full AccessBridge orchestrator workflow.

Exercises the genuine end-to-end flow: question in → research → translate →
guide → awaiting_review. Verifies that every step is persisted to the
database with the right status transitions and audit events.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.app.models import (
    AgentExecution,
    AgentExecutionStatus,
    AuditEvent,
    GuidanceChecklist,
    Question,
    QuestionStatus,
    ResearchResult,
    Source,
    TranslationResult,
)


@pytest.mark.asyncio
async def test_full_workflow_reaches_awaiting_review(db_session):
    """The orchestrator must run all three agents and reach awaiting_review."""
    from agents.orchestrator import run_workflow

    q = Question(
        question_text="What documents do I need for the AICTE Pragati scholarship for girls?",
        language="en",
        category="scholarship",
        status=QuestionStatus.received,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    qid = q.id

    # Run the full workflow.
    await run_workflow(qid, db_session)
    db_session.commit()
    db_session.refresh(q)

    # --- Status transitions ---
    assert q.status == QuestionStatus.awaiting_review, f"expected awaiting_review, got {q.status}"

    # --- Research persisted ---
    rr = db_session.query(ResearchResult).filter_by(question_id=qid).first()
    assert rr is not None
    assert rr.scholarship_name is not None
    assert "pragati" in rr.scholarship_name.lower()
    assert len(rr.eligibility) >= 1
    assert len(rr.required_documents) >= 1
    assert rr.retrieved_at is not None

    # --- Sources persisted (each with URL + retrieval timestamp) ---
    sources = db_session.query(Source).filter(Source.research_result_id == rr.id).all()
    assert len(sources) >= 1
    for s in sources:
        assert s.url.startswith("http")
        assert s.retrieved_at is not None
        assert s.is_official is True

    # --- Translation persisted ---
    tr = db_session.query(TranslationResult).filter_by(question_id=qid).first()
    assert tr is not None
    assert tr.language == "en"
    assert len(tr.simplified_text) > 50
    assert len(tr.original_snippets) >= 1

    # --- Guidance checklist persisted ---
    gc = db_session.query(GuidanceChecklist).filter_by(question_id=qid).first()
    assert gc is not None
    assert len(gc.items) >= 3
    # missing_information and uncertainty_warnings fields exist.
    assert isinstance(gc.missing_information, list)
    assert isinstance(gc.uncertainty_warnings, list)

    # --- Agent executions persisted (one per agent, all success) ---
    execs = db_session.query(AgentExecution).filter_by(question_id=qid).all()
    assert len(execs) == 3
    statuses = {e.status for e in execs}
    assert AgentExecutionStatus.success in statuses
    agents_run = {e.agent.value for e in execs}
    assert agents_run == {"research", "language", "guidance"}

    # --- Audit events persisted ---
    audits = db_session.query(AuditEvent).filter_by(question_id=qid).all()
    events = {a.event for a in audits}
    assert "research_started" in events
    assert "translation_started" in events
    assert "guidance_started" in events
    assert "awaiting_human_review" in events


@pytest.mark.asyncio
async def test_workflow_failure_is_recorded(db_session):
    """A workflow against a non-existent question must fail cleanly and not
    leave the orchestrator hanging."""
    from agents.orchestrator import run_workflow

    with pytest.raises(ValueError):
        await run_workflow("non-existent-question-id", db_session)
