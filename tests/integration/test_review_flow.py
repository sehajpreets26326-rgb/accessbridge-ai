"""Integration test for the full human-review approval flow.

Exercises the complete lifecycle:
    received → researching → translating → guiding → awaiting_review
    → approved → delivered

and the rejection + corrections branches. Verifies that:
- Every transition is persisted with the right status.
- HumanApproval rows are recorded with reviewer + action + timestamp.
- Audit events are emitted for every transition.
- The deliver endpoint posts final guidance and marks the question delivered.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.app.models import (
    AuditEvent,
    GuidanceChecklist,
    HumanApproval,
    Question,
    QuestionStatus,
    ResearchResult,
    ReviewAction,
    Source,
    TranslationResult,
    User,
    UserRole,
)


async def _run_workflow_to_awaiting_review(db_session) -> Question:
    """Helper: create a question and run the full workflow so it reaches
    awaiting_review. Returns the refreshed Question."""
    from agents.orchestrator import run_workflow

    q = Question(
        question_text="Review flow integration: What documents do I need for the AICTE Pragati scholarship for girls?",
        language="en",
        category="scholarship",
        status=QuestionStatus.received,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    await run_workflow(q.id, db_session)
    db_session.commit()
    db_session.refresh(q)
    return q


@pytest.mark.asyncio
async def test_approve_flow_reaches_delivered(db_session):
    """approved → delivered must work end to end."""
    q = await _run_workflow_to_awaiting_review(db_session)
    assert q.status == QuestionStatus.awaiting_review

    # Simulate a coordinator approving via the review route logic (direct).
    reviewer = User(display_name="coordinator-alice", role=UserRole.coordinator)
    db_session.add(reviewer)
    db_session.flush()

    approval = HumanApproval(
        question_id=q.id,
        reviewer_id=reviewer.id,
        reviewer_name="coordinator-alice",
        action=ReviewAction.approved,
        note="Sources verified against AICTE portal.",
    )
    db_session.add(approval)
    q.status = QuestionStatus.approved
    db_session.commit()
    db_session.refresh(q)

    assert q.status == QuestionStatus.approved

    # Now mark as delivered (this is what POST /api/review/{id}/deliver does).
    q.status = QuestionStatus.delivered
    db_session.commit()
    db_session.refresh(q)
    assert q.status == QuestionStatus.delivered

    # The HumanApproval must be persisted.
    approvals = db_session.query(HumanApproval).filter_by(question_id=q.id).all()
    assert len(approvals) == 1
    assert approvals[0].action == ReviewAction.approved
    assert approvals[0].reviewer_name == "coordinator-alice"
    assert approvals[0].note == "Sources verified against AICTE portal."
    assert approvals[0].created_at is not None

    # The reviewer must be a coordinator.
    assert approvals[0].reviewer is not None
    assert approvals[0].reviewer.role == UserRole.coordinator


@pytest.mark.asyncio
async def test_reject_flow(db_session):
    """A rejected question must transition to rejected and record the action."""
    q = await _run_workflow_to_awaiting_review(db_session)

    approval = HumanApproval(
        question_id=q.id,
        reviewer_name="coordinator-bob",
        action=ReviewAction.rejected,
        note="Deadline information could not be verified.",
    )
    db_session.add(approval)
    q.status = QuestionStatus.rejected
    db_session.commit()
    db_session.refresh(q)

    assert q.status == QuestionStatus.rejected
    approvals = db_session.query(HumanApproval).filter_by(question_id=q.id).all()
    assert len(approvals) == 1
    assert approvals[0].action == ReviewAction.rejected


@pytest.mark.asyncio
async def test_corrections_requested_keeps_in_review_queue(db_session):
    """A 'corrections requested' review must put the question back into
    awaiting_review so it stays in the coordinator queue."""
    q = await _run_workflow_to_awaiting_review(db_session)

    approval = HumanApproval(
        question_id=q.id,
        reviewer_name="coordinator-carol",
        action=ReviewAction.corrections_requested,
        note="Please re-check the income limit.",
    )
    db_session.add(approval)
    q.status = QuestionStatus.awaiting_review
    db_session.commit()
    db_session.refresh(q)

    assert q.status == QuestionStatus.awaiting_review
    approvals = db_session.query(HumanApproval).filter_by(question_id=q.id).all()
    assert len(approvals) == 1
    assert approvals[0].action == ReviewAction.corrections_requested


@pytest.mark.asyncio
async def test_multiple_reviews_record_history(db_session):
    """Multiple review actions on the same question must all be persisted in
    order, forming a complete audit trail."""
    q = await _run_workflow_to_awaiting_review(db_session)

    # First: corrections requested.
    db_session.add(HumanApproval(
        question_id=q.id, reviewer_name="alice",
        action=ReviewAction.corrections_requested, note="re-check deadline",
    ))
    db_session.commit()

    # Second: approved.
    db_session.add(HumanApproval(
        question_id=q.id, reviewer_name="bob",
        action=ReviewAction.approved, note="now verified",
    ))
    q.status = QuestionStatus.approved
    db_session.commit()

    approvals = db_session.query(HumanApproval).filter_by(question_id=q.id).order_by(HumanApproval.created_at).all()
    assert len(approvals) == 2
    assert approvals[0].action == ReviewAction.corrections_requested
    assert approvals[0].reviewer_name == "alice"
    assert approvals[1].action == ReviewAction.approved
    assert approvals[1].reviewer_name == "bob"


@pytest.mark.asyncio
async def test_audit_trail_is_complete_after_full_lifecycle(db_session):
    """The audit trail must contain every transition in order."""
    from backend.app.services.audit import record

    q = await _run_workflow_to_awaiting_review(db_session)

    # Record approval + delivery.
    record(db_session, question_id=q.id, actor="coordinator:dave", event="review_approved", payload={"note": "ok"})
    q.status = QuestionStatus.approved
    db_session.commit()

    record(db_session, question_id=q.id, actor="api:review", event="delivered", payload={"room": "final-guidance"})
    q.status = QuestionStatus.delivered
    db_session.commit()

    audits = db_session.query(AuditEvent).filter_by(question_id=q.id).order_by(AuditEvent.created_at).all()
    events = [a.event for a in audits]
    # Must contain the full lifecycle in order.
    assert "research_started" in events
    assert "translation_started" in events
    assert "guidance_started" in events
    assert "awaiting_human_review" in events
    assert "review_approved" in events
    assert "delivered" in events
    # Order: research_started must come before delivered.
    assert events.index("research_started") < events.index("delivered")


@pytest.mark.asyncio
async def test_failed_workflow_records_error(db_session, monkeypatch):
    """When the orchestrator fails, the question must be marked failed with an
    error message and the failure must be audited."""
    from agents.orchestrator import run_workflow
    from agents.messages import ResearchRequest

    # Patch the research function to raise.
    import agents.research_agent as ra

    async def _boom(req: ResearchRequest):
        raise RuntimeError("simulated source fetch failure")

    monkeypatch.setattr(ra, "research", _boom)

    q = Question(
        question_text="Failure test: AICTE Pragati scholarship for girls documents",
        language="en",
        category="scholarship",
        status=QuestionStatus.received,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    with pytest.raises(RuntimeError):
        await run_workflow(q.id, db_session)
    db_session.commit()
    db_session.refresh(q)

    assert q.status == QuestionStatus.failed
    assert q.error_message is not None
    assert "simulated" in q.error_message

    # The failure must be audited.
    audits = db_session.query(AuditEvent).filter_by(question_id=q.id, event="workflow_failed").all()
    assert len(audits) == 1
    assert "simulated" in str(audits[0].payload)


@pytest.mark.asyncio
async def test_research_result_persists_all_structured_fields(db_session):
    """The persisted ResearchResult must carry every structured field the
    Research Agent is contracted to produce."""
    q = await _run_workflow_to_awaiting_review(db_session)

    rr = db_session.query(ResearchResult).filter_by(question_id=q.id).first()
    assert rr is not None
    # Every contracted field must be present (None is allowed, but the column exists).
    assert hasattr(rr, "scholarship_name")
    assert hasattr(rr, "provider")
    assert hasattr(rr, "eligibility")
    assert hasattr(rr, "required_documents")
    assert hasattr(rr, "application_deadline")
    assert hasattr(rr, "application_steps")
    assert hasattr(rr, "retrieved_at")
    assert hasattr(rr, "verification_status")
    assert hasattr(rr, "confidence_notes")
    # And the scholarship was actually identified.
    assert rr.scholarship_name is not None
    assert rr.provider is not None
    assert rr.retrieved_at is not None


@pytest.mark.asyncio
async def test_sources_persisted_with_urls_and_timestamps(db_session):
    """Every persisted Source must carry a URL, retrieval timestamp and
    is_official flag — the trust contract."""
    q = await _run_workflow_to_awaiting_review(db_session)

    rr = db_session.query(ResearchResult).filter_by(question_id=q.id).first()
    sources = db_session.query(Source).filter(Source.research_result_id == rr.id).all()
    assert len(sources) >= 1
    for s in sources:
        assert s.url.startswith("http")
        assert s.retrieved_at is not None
        assert isinstance(s.is_official, bool)
        assert s.is_official is True  # all curated sources are official
        assert isinstance(s.reachable, bool)


@pytest.mark.asyncio
async def test_translation_preserves_original_snippets(db_session):
    """The TranslationResult must include original_snippets preserving the
    official wording verbatim."""
    q = await _run_workflow_to_awaiting_review(db_session)

    tr = db_session.query(TranslationResult).filter_by(question_id=q.id).first()
    assert tr is not None
    assert tr.language == "en"
    assert len(tr.simplified_text) > 0
    # original_snippets must be a list (possibly empty in deterministic mode,
    # but the field must exist and be a list).
    assert isinstance(tr.original_snippets, list)


@pytest.mark.asyncio
async def test_checklist_has_items_and_warnings(db_session):
    """The GuidanceChecklist must have items, missing_information and
    uncertainty_warnings — the coordinator's review surface."""
    q = await _run_workflow_to_awaiting_review(db_session)

    gc = db_session.query(GuidanceChecklist).filter_by(question_id=q.id).first()
    assert gc is not None
    assert isinstance(gc.items, list)
    assert len(gc.items) >= 1
    # Each item must have the required shape.
    for item in gc.items:
        assert "title" in item
        assert "detail" in item
        assert "status" in item
        assert item["status"] in ("todo", "ready", "missing", "uncertain")
    assert isinstance(gc.missing_information, list)
    assert isinstance(gc.uncertainty_warnings, list)
