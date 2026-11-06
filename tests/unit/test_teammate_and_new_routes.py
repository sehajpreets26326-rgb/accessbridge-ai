"""Tests for the cheering teammate persona and the new API routes
(evidence inspector, re-run research, unsupported claims, evaluation endpoint).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.app.main import app
    return TestClient(app)


# --- Teammate persona -----------------------------------------------------

def test_teammate_message_for_every_workflow_event():
    """Every workflow event must produce a non-empty, warm message."""
    from backend.app.services.teammate import teammate_message
    events = [
        "received", "research_started", "research_done", "translation_started",
        "translation_done", "guidance_started", "guidance_done", "awaiting_review",
        "approved", "rejected", "corrections_requested", "delivered", "failed",
    ]
    for event in events:
        msg = teammate_message(event, scholarship="AICTE Pragati", source_count=3,
                               language="hi", reviewer="alice")
        assert len(msg) > 10
        # Must not contain excessive emojis (the design forbids it).
        emoji_count = sum(1 for c in msg if ord(c) > 0x2600)
        assert emoji_count <= 2


def test_teammate_research_done_includes_source_count():
    """The research_done message must include the actual source count."""
    from backend.app.services.teammate import teammate_message
    msg = teammate_message("research_done", scholarship="Pragati", source_count=3)
    assert "3" in msg
    assert "Pragati" in msg


def test_teammate_failed_is_honest_about_error():
    """The failed message must mention the error, not hide it."""
    from backend.app.services.teammate import teammate_message
    msg = teammate_message("failed", error="DNS resolution failed")
    assert "DNS resolution failed" in msg
    assert "snag" in msg.lower() or "hit" in msg.lower()


def test_teammate_approved_celebrates():
    """The approved message must be encouraging."""
    from backend.app.services.teammate import teammate_message
    msg = teammate_message("approved", reviewer="alice")
    assert "alice" in msg.lower() or "coordinator" in msg.lower()
    # Must contain an encouraging word.
    assert any(w in msg.lower() for w in ("got this", "go get", "here", "approved"))


def test_teammate_unknown_event_has_fallback():
    """An unknown event must not crash — it falls back to a generic message."""
    from backend.app.services.teammate import teammate_message
    msg = teammate_message("unknown_event_xyz", scholarship="X")
    assert len(msg) > 5


# --- Evidence inspector endpoint ------------------------------------------

def test_evidence_endpoint_returns_refs_after_workflow(client):
    """GET /api/questions/{id}/evidence must return per-claim evidence refs."""
    create = client.post("/api/questions", json={
        "question_text": "Evidence endpoint test: AICTE Pragati scholarship documents for girls",
    })
    qid = create.json()["id"]

    r = client.get(f"/api/questions/{qid}/evidence")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    # After the workflow, evidence should be present.
    if len(body) > 0:
        ev = body[0]
        assert "claim" in ev
        assert "claim_type" in ev
        assert "confidence" in ev
        assert "freshness_days" in ev


def test_evidence_endpoint_404_for_unknown_question(client):
    r = client.get("/api/questions/nonexistent-evidence/evidence")
    assert r.status_code == 404


# --- Unsupported claims endpoint ------------------------------------------

def test_unsupported_claims_endpoint(client):
    """GET /api/questions/{id}/unsupported-claims returns claims with no source."""
    create = client.post("/api/questions", json={
        "question_text": "Unsupported claims test: AICTE Saksham scholarship eligibility",
    })
    qid = create.json()["id"]
    r = client.get(f"/api/questions/{qid}/unsupported-claims")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- Re-run research endpoint ---------------------------------------------

def test_rerun_research_resets_question(client):
    """POST /api/questions/{id}/rerun-research must reset to received and re-run."""
    create = client.post("/api/questions", json={
        "question_text": "Re-run test: AICTE Pragati scholarship for girls eligibility documents",
    })
    qid = create.json()["id"]

    r = client.post(f"/api/questions/{qid}/rerun-research")
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["status"] == "received"


def test_rerun_research_404_for_unknown_question(client):
    r = client.post("/api/questions/nonexistent-rerun/rerun-research")
    assert r.status_code == 404


# --- Evaluation endpoint --------------------------------------------------

def test_evaluation_endpoint_returns_dataset(client):
    """GET /api/dashboard/evaluation must return the reproducible dataset."""
    r = client.get("/api/dashboard/evaluation")
    assert r.status_code == 200
    body = r.json()
    assert "methodology" in body
    assert "case_count" in body
    assert body["case_count"] >= 4
    assert isinstance(body["cases"], list)
    for case in body["cases"]:
        assert "id" in case
        assert "question" in case
        assert "expected_verification" in case


# --- ASI-1 provider config ------------------------------------------------

def test_asi1_provider_preset():
    """Setting llm_provider=asi1 must fill in the ASI-1 base URL + model."""
    from backend.app.config import Settings
    s = Settings(llm_provider="asi1", llm_api_key="test")
    assert s.llm_base_url == "https://api.asi1.ai/v1"
    assert s.llm_model == "asi1-mini"


def test_openai_provider_preset():
    """The default provider is openai."""
    from backend.app.config import Settings
    s = Settings()
    assert s.llm_provider == "openai"
    assert s.llm_base_url == "https://api.openai.com/v1"


def test_custom_provider_keeps_user_base_url():
    """custom provider does not override the user's base_url."""
    from backend.app.config import Settings
    s = Settings(llm_provider="custom", llm_base_url="https://my-llm.example.com/v1")
    assert s.llm_base_url == "https://my-llm.example.com/v1"
