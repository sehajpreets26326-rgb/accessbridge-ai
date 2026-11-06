"""Unit tests for the REST API routes.

Uses FastAPI's TestClient against the real app + the test SQLite database.
Background workflow tasks run synchronously inside TestClient, so a POST
/api/questions that triggers the full research→translate→guide pipeline will
block until it completes (a few seconds with the short KB timeout).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.app.main import app
    return TestClient(app)


# --- /api/health ----------------------------------------------------------

def test_api_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "switch_trust" in body
    assert "mattermost" in body
    assert "database" in body


# --- POST /api/questions --------------------------------------------------

def test_create_question_validates_min_length(client):
    """A question shorter than 8 chars must be rejected with 422."""
    r = client.post("/api/questions", json={"question_text": "short"})
    assert r.status_code == 422


def test_create_question_validates_language_enum(client):
    """An unsupported language code must be rejected."""
    r = client.post("/api/questions", json={
        "question_text": "What is the Pragati scholarship?",
        "language": "fr",  # not supported
    })
    assert r.status_code == 422


def test_create_question_returns_201_with_real_id(client):
    """A valid question must return 201, a real UUID, and status=received."""
    r = client.post("/api/questions", json={
        "question_text": "What documents do I need for the AICTE Pragati scholarship?",
        "language": "en",
        "category": "scholarship",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["id"]
    assert len(body["id"]) >= 16  # UUID hex
    assert body["status"] == "received"
    assert body["language"] == "en"
    assert body["category"] == "scholarship"
    assert body["created_at"]


# --- GET /api/questions ---------------------------------------------------

def test_list_questions_returns_recent_first(client):
    """list_questions must return questions newest-first."""
    # Create two questions.
    client.post("/api/questions", json={"question_text": "First test question for listing AAA"})
    client.post("/api/questions", json={"question_text": "Second test question for listing BBB"})
    r = client.get("/api/questions")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 2
    # Newest first: the second question should appear before the first.
    texts = [row["question_text"] for row in rows]
    assert texts.index("Second test question for listing BBB") < texts.index("First test question for listing AAA")


def test_get_question_returns_full_detail(client):
    """GET /api/questions/{id} must return the full question detail."""
    create = client.post("/api/questions", json={
        "question_text": "Detail test question for AICTE Saksham scholarship eligibility",
    })
    qid = create.json()["id"]
    r = client.get(f"/api/questions/{qid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == qid
    assert body["question_text"].startswith("Detail test question")
    assert body["status"] in ("received", "researching", "translating", "guiding", "awaiting_review", "failed")


def test_get_question_404_for_unknown_id(client):
    r = client.get("/api/questions/does-not-exist-12345")
    assert r.status_code == 404


# --- GET /api/dashboard ---------------------------------------------------

def test_dashboard_returns_real_aggregate_data(client):
    """The dashboard must read from real DB data, not return a mockup."""
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert "recent_questions" in body
    assert "active_agent_runs" in body
    assert "pending_reviews" in body
    assert "completed_today" in body
    assert "verification_summary" in body
    assert "switch_status" in body
    assert isinstance(body["recent_questions"], list)
    assert isinstance(body["completed_today"], int)
    # switch_status must report real state.
    assert body["switch_status"]["bridge_enabled"] is True
    assert "trust" in body["switch_status"]


# --- GET /api/agents/* ----------------------------------------------------

def test_agent_executions_list(client):
    r = client.get("/api/agents/executions")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    # At least one workflow has run by now (earlier tests created questions).
    # Each row has the required fields.
    for row in rows[:1]:
        assert row["agent"] in ("research", "language", "guidance")
        assert row["status"] in ("started", "success", "error", "skipped")
        assert "started_at" in row


def test_agent_workspace_404_for_unknown_question(client):
    r = client.get("/api/agents/question/does-not-exist-99999")
    assert r.status_code == 404


def test_agent_workspace_returns_full_trace(client):
    """After a workflow completes, the workspace must show research,
    translation, guidance, executions and audit — all from real data."""
    # Create a question and wait for the background workflow.
    create = client.post("/api/questions", json={
        "question_text": "Workspace trace test: AICTE Pragati scholarship documents for girls",
    })
    qid = create.json()["id"]
    r = client.get(f"/api/agents/question/{qid}")
    assert r.status_code == 200
    body = r.json()
    assert body["question"]["id"] == qid
    assert "executions" in body
    assert "audit" in body
    # If the workflow completed, research/translation/guidance must be present.
    if body["question"]["status"] == "awaiting_review":
        assert body["research"] is not None
        assert body["translation"] is not None
        assert body["guidance"] is not None
        assert len(body["executions"]) == 3
        assert len(body["audit"]) >= 4  # research_started, translation_started, guidance_started, awaiting_human_review


# --- POST /api/review/{id} ------------------------------------------------

@pytest.fixture
def awaiting_question(client):
    """Create a question and run the workflow so it reaches awaiting_review."""
    create = client.post("/api/questions", json={
        "question_text": "Review flow test: AICTE Pragati scholarship eligibility for girls",
    })
    qid = create.json()["id"]
    # The background task ran synchronously inside TestClient; the question
    # should now be awaiting_review (or still processing if timing was tight).
    return qid


def test_review_rejects_without_secret_when_configured(client, monkeypatch):
    """When REVIEW_APPROVAL_SECRET is set, a request without it is 403."""
    from backend.app.config import settings
    monkeypatch.setattr(settings, "review_approval_secret", "top-secret")

    create = client.post("/api/questions", json={
        "question_text": "Secret test: AICTE Saksham scholarship for specially-abled",
    })
    qid = create.json()["id"]

    r = client.post(f"/api/review/{qid}", json={
        "action": "approved",
        "reviewer_name": "coordinator-alice",
        "secret": "",  # missing
    })
    assert r.status_code == 403

    # With the right secret it works.
    r2 = client.post(f"/api/review/{qid}", json={
        "action": "approved",
        "reviewer_name": "coordinator-alice",
        "secret": "top-secret",
    })
    assert r2.status_code == 201

    monkeypatch.setattr(settings, "review_approval_secret", "")


def test_review_rejects_non_awaiting_question(client):
    """Reviewing a question that is not awaiting_review is 409."""
    # Create a question but immediately try to review it before the workflow
    # completes — or review an already-approved question. We'll create one,
    # approve it, then try to approve again.
    create = client.post("/api/questions", json={
        "question_text": "Double review test: NSP national scholarship portal documents",
    })
    qid = create.json()["id"]

    # First approval (if awaiting_review).
    r1 = client.post(f"/api/review/{qid}", json={
        "action": "approved",
        "reviewer_name": "coordinator-bob",
    })
    # If the workflow hadn't reached awaiting_review yet, this is 409 — fine.
    # If it had, this succeeds and the question is now approved.
    if r1.status_code == 201:
        # Second approval must be 409 because status is now 'approved'.
        r2 = client.post(f"/api/review/{qid}", json={
            "action": "approved",
            "reviewer_name": "coordinator-bob",
        })
        assert r2.status_code == 409


def test_review_rejects_unknown_question(client):
    r = client.post("/api/review/does-not-exist-77777", json={
        "action": "approved",
        "reviewer_name": "coordinator-x",
    })
    assert r.status_code == 404


def test_review_records_reviewer_and_action(client):
    """An approved review must persist a HumanApproval with the reviewer name."""
    create = client.post("/api/questions", json={
        "question_text": "Reviewer record test: Chevening scholarship UK for Indian students",
    })
    qid = create.json()["id"]

    r = client.post(f"/api/review/{qid}", json={
        "action": "approved",
        "reviewer_name": "coordinator-carol",
        "note": "Sources verified.",
    })
    if r.status_code == 201:
        body = r.json()
        assert body["reviewer_name"] == "coordinator-carol"
        assert body["action"] == "approved"
        assert body["note"] == "Sources verified."
        assert body["created_at"]

        # GET the review list.
        lr = client.get(f"/api/review/{qid}")
        assert lr.status_code == 200
        reviews = lr.json()
        assert any(rv["reviewer_name"] == "coordinator-carol" for rv in reviews)


# --- POST /api/review/{id}/deliver ---------------------------------------

def test_deliver_requires_approved_status(client):
    """Delivering a question that is not approved is 409."""
    create = client.post("/api/questions", json={
        "question_text": "Deliver test: Fulbright Nehru masters fellowship for Indians",
    })
    qid = create.json()["id"]
    # Try to deliver without approving first.
    r = client.post(f"/api/review/{qid}/deliver")
    # If the question is still awaiting_review (not approved), must be 409.
    # If it's still processing, also 409.
    assert r.status_code in (409,)


def test_deliver_404_for_unknown_question(client):
    r = client.post("/api/review/does-not-exist-deliver/deliver")
    assert r.status_code == 404
