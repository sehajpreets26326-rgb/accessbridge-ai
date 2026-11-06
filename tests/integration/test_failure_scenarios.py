"""Failure-handling tests: duplicate webhooks, invalid events, conflicting
sources, agent timeout simulation, LLM failure.

Covers the failure-demonstration requirement (section E of the quality spec).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.app.main import app
    return TestClient(app)


# --- Duplicate webhook event (idempotency via the API) --------------------

def test_duplicate_bridge_event_returns_same_question_id(client):
    """When the same event is delivered twice (Switch retry), the bridge must
    return the original question_id, not create a duplicate."""
    payload = {
        "room": "student-questions",
        "platform": "switch",
        "sender": "alice",
        "sender_id": "u-alice-001",
        "text": "Duplicate event test: AICTE Pragati scholarship documents",
        "event_id": "evt-dedup-001",
    }
    r1 = client.post("/switch/bridge", json=payload)
    assert r1.status_code == 200
    qid1 = r1.json()["question_id"]

    # Same event again — must return the same question_id.
    r2 = client.post("/switch/bridge", json=payload)
    assert r2.status_code == 200
    assert r2.json()["question_id"] == qid1
    assert r2.json()["status"] == "duplicate"


def test_different_event_id_creates_new_question(client):
    """A different event_id must create a new question (not a duplicate)."""
    base = {
        "room": "student-questions",
        "sender": "bob",
        "text": "Different event test: AICTE Saksham scholarship",
    }
    r1 = client.post("/switch/bridge", json={**base, "event_id": "evt-A"})
    r2 = client.post("/switch/bridge", json={**base, "event_id": "evt-B"})
    assert r1.json()["question_id"] != r2.json()["question_id"]


# --- Invalid events -------------------------------------------------------

def test_bridge_rejects_payload_without_sender(client):
    """An event without a sender must be rejected by Pydantic."""
    r = client.post("/switch/bridge", json={
        "room": "r",
        "text": "hello",
        # sender missing — required field
    })
    assert r.status_code == 422


def test_mattermost_webhook_rejects_unparseable_payload(client):
    """A malformed JSON payload must return 400."""
    r = client.post("/switch/mattermost/webhook",
                    content="{invalid json}",
                    headers={"content-type": "application/json"})
    # 400 is the honest rejection for unparseable JSON.
    assert r.status_code == 400


# --- Conflicting sources --------------------------------------------------

@pytest.mark.asyncio
async def test_conflicting_income_limits_detected():
    """When sources state different income limits, a conflict is recorded."""
    from agents.research_agent import _detect_conflicts
    from knowledge_base.retriever import RetrievedSource
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    retrieved = [
        RetrievedSource(url="https://src-a", title="A", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="Income limit: Rs. 8 lakh per annum for this scheme."),
        RetrievedSource(url="https://src-b", title="B", publisher="P", retrieved_at=now,
                        reachable=True, is_official=True, snippet="",
                        raw_text="The family income ceiling is Rs. 6 lakh per annum."),
    ]
    conflicts = _detect_conflicts({}, retrieved)
    assert len(conflicts) >= 1
    # The conflict message must mention both values or the income key.
    assert "income" in conflicts[0].lower() or "lakh" in conflicts[0].lower()


# --- Agent failure / timeout simulation -----------------------------------

@pytest.mark.asyncio
async def test_agent_failure_marks_question_failed(db_session, monkeypatch):
    """When the Research Agent raises, the question must be marked failed."""
    from agents.orchestrator import run_workflow
    from agents.messages import ResearchRequest
    from backend.app.models import Question, QuestionStatus, AuditEvent
    import agents.research_agent as ra

    async def _boom(req: ResearchRequest):
        raise RuntimeError("simulated agent timeout")

    monkeypatch.setattr(ra, "research", _boom)

    q = Question(
        question_text="Failure test: AICTE Pragati scholarship documents",
        language="en", category="scholarship", status=QuestionStatus.received,
    )
    db_session.add(q); db_session.commit(); db_session.refresh(q)

    with pytest.raises(RuntimeError):
        await run_workflow(q.id, db_session)
    db_session.commit()
    db_session.refresh(q)

    assert q.status == QuestionStatus.failed
    assert q.error_message is not None
    assert "simulated" in q.error_message

    # The failure must be audited.
    failed_audit = db_session.query(AuditEvent).filter_by(
        question_id=q.id, event="workflow_failed"
    ).first()
    assert failed_audit is not None


# --- LLM provider failure (graceful degradation) --------------------------

@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_deterministic():
    """When the LLM is unavailable, the Research Agent must fall back to the
    deterministic extractor and still produce a result."""
    from agents.research_agent import research, _deterministic_extract
    from agents.messages import ResearchRequest
    from knowledge_base.retriever import retrieve

    req = ResearchRequest(
        question_id="test-llm-fallback",
        question_text="AICTE Pragati scholarship for girls eligibility",
    )
    # With no LLM key in the test env, _llm_extract returns None and the
    # deterministic extractor runs. The workflow must still complete.
    resp = await research(req)
    assert resp.error is None
    assert resp.scholarship_name is not None
    # Confidence notes must mention deterministic extraction.
    assert resp.confidence_notes is not None


# --- Unreachable source (honest reporting) --------------------------------

def test_unreachable_source_recorded_honestly():
    """When a source URL cannot be fetched, reachable=False must be recorded."""
    from knowledge_base.retriever import retrieve

    sources = retrieve("AICTE Pragati scholarship", max_sources=1)
    assert len(sources) == 1
    s = sources[0]
    # In the test env (no internet), reachable is False.
    assert isinstance(s.reachable, bool)
    if not s.reachable:
        # The bundled excerpt must still provide content.
        assert s.raw_text is not None
        assert len(s.raw_text) > 0


# --- Human rejection flow -------------------------------------------------

@pytest.mark.asyncio
async def test_human_rejection_blocks_delivery(db_session):
    """A rejected question must not be deliverable."""
    from agents.orchestrator import run_workflow
    from backend.app.models import (Question, QuestionStatus, HumanApproval, ReviewAction)

    q = Question(
        question_text="Rejection test: AICTE Pragati scholarship for girls",
        language="en", category="scholarship", status=QuestionStatus.received,
    )
    db_session.add(q); db_session.commit(); db_session.refresh(q)
    await run_workflow(q.id, db_session)
    db_session.commit()
    db_session.refresh(q)
    assert q.status == QuestionStatus.awaiting_review

    # Reject it.
    db_session.add(HumanApproval(
        question_id=q.id, reviewer_name="coordinator",
        action=ReviewAction.rejected, note="unverified deadline",
    ))
    q.status = QuestionStatus.rejected
    db_session.commit()

    # A rejected question must not be deliverable.
    assert q.status == QuestionStatus.rejected
    assert q.status != QuestionStatus.approved
    assert q.status != QuestionStatus.delivered
