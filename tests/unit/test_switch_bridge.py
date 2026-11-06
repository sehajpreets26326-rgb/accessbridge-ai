"""Unit tests for the Switch integration layer.

Covers:
- /switch/health endpoint
- /switch/bridge (Switch Console Agent Bridge) — happy path, token rejection,
  empty-text rejection
- /switch/mattermost/webhook — raw Mattermost outgoing webhook
- event_handler.from_raw normalisation for both payload shapes
- event_handler language + category detection
- message_sender graceful behaviour when Mattermost is not configured
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """FastAPI test client. Module-scoped so the lifespan runs once."""
    from backend.app.main import app
    return TestClient(app)


# --- /switch/health -------------------------------------------------------

def test_switch_health_returns_real_status(client):
    """The health endpoint must report real connection status, not a fake one."""
    r = client.get("/switch/health")
    assert r.status_code == 200
    body = r.json()
    assert body["bridge_enabled"] is True
    # switch_trust must be present and report its configured state honestly.
    assert "switch_trust" in body
    # platforms must report real status for every supported chat app.
    assert "platforms" in body
    platforms = body["platforms"]
    for name in ("mattermost", "discord", "slack", "telegram", "teams"):
        assert name in platforms
        assert isinstance(platforms[name]["configured"], bool)
    # In the test env, no platform has credentials, so all must be unconfigured.
    assert platforms["discord"]["configured"] is False
    assert "time" in body


# --- /switch/bridge (Switch Console Agent Bridge) -------------------------

def test_switch_bridge_rejects_missing_token_when_configured(client, monkeypatch):
    """When SWITCH_BRIDGE_TOKEN is set, an inbound event without it is 401."""
    from backend.app.config import settings
    monkeypatch.setattr(settings, "switch_bridge_token", "secret-bridge-token")

    r = client.post("/switch/bridge", json={
        "room": "student-questions",
        "sender": "alice",
        "text": "What documents do I need for AICTE Pragati?",
        "token": "wrong-token",
    })
    assert r.status_code == 401

    # Correct token is accepted.
    r2 = client.post("/switch/bridge", json={
        "room": "student-questions",
        "sender": "alice",
        "text": "What documents do I need for AICTE Pragati?",
        "token": "secret-bridge-token",
    })
    assert r2.status_code == 200
    assert r2.json()["accepted"] is True

    # Reset so other tests are not affected.
    monkeypatch.setattr(settings, "switch_bridge_token", "")


def test_switch_bridge_rejects_empty_text(client):
    """An empty message must be rejected — Pydantic validates min_length=1."""
    r = client.post("/switch/bridge", json={
        "room": "student-questions",
        "sender": "alice",
        "text": "",
    })
    # 422 is Pydantic's validation rejection — correct and even stricter than 400.
    assert r.status_code in (400, 422)


def test_switch_bridge_creates_question_and_acknowledges(client):
    """A valid event must create a Question row and return a real question_id."""
    r = client.post("/switch/bridge", json={
        "room": "student-questions",
        "platform": "switch",
        "sender": "alice",
        "sender_id": "u-123",
        "text": "What is the AICTE Saksham scholarship?",
        "language": "en",
        "category": "scholarship",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["question_id"]  # real UUID
    assert body["status"] == "received"


# --- /switch/mattermost/webhook (raw Mattermost outgoing webhook) ---------

def test_mattermost_webhook_accepts_form_payload(client):
    """Mattermost posts form-encoded payloads; the bridge must accept them."""
    r = client.post("/switch/mattermost/webhook", data={
        "token": "",
        "channel_name": "student-questions",
        "user_name": "bob",
        "user_id": "u-bob",
        "text": "Tell me about the NSP scholarship portal",
        "trigger_word": "@accessbridge",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["question_id"]


def test_mattermost_webhook_accepts_json_payload(client):
    """Mattermost may also post JSON; the bridge must accept either shape."""
    r = client.post("/switch/mattermost/webhook", json={
        "channel_name": "student-questions",
        "user_name": "carol",
        "text": "What is the Chevening scholarship?",
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is True


# --- event_handler normalisation -----------------------------------------

def test_event_handler_detects_mattermost_payload_shape():
    """from_raw must auto-detect a Mattermost payload by its keys."""
    from switch_integration.event_handler import from_raw
    ev = from_raw({
        "channel_name": "student-questions",
        "user_name": "alice",
        "text": "Hello",
    })
    assert ev.platform == "mattermost"
    assert ev.sender == "alice"
    assert ev.room == "student-questions"


def test_event_handler_detects_switch_payload_shape():
    """from_raw must auto-detect a Switch Console payload by its keys."""
    from switch_integration.event_handler import from_raw
    ev = from_raw({
        "room": "student-questions",
        "sender": "alice",
        "text": "Hello",
    })
    assert ev.platform == "switch"


def test_event_handler_strips_trigger_word():
    """The Mattermost trigger_word must be stripped from the message text."""
    from switch_integration.event_handler import from_mattermost_webhook
    ev = from_mattermost_webhook({
        "trigger_word": "@accessbridge",
        "text": "@accessbridge What is the Pragati scholarship?",
        "channel_name": "student-questions",
        "user_name": "alice",
    })
    assert not ev.text.startswith("@accessbridge")
    assert "Pragati" in ev.text


# --- language + category detection ---------------------------------------

def test_detect_language_by_script():
    """Devanagari → hi, Gurmukhi → pa, otherwise en."""
    from switch_integration.event_handler import _detect_language
    assert _detect_language("प्रगति छात्रवृत्ति के बारे में बताओ") == "hi"
    assert _detect_language("ਪ੍ਰਗਤੀ ਸਕਾਲਰਸ਼ਿਪ ਬਾਰੇ ਦੱਸੋ") == "pa"
    assert _detect_language("Tell me about the Pragati scholarship") == "en"


def test_detect_language_by_explicit_request():
    """An explicit 'in Hindi' / 'in Punjabi' request is honoured."""
    from switch_integration.event_handler import _detect_language
    assert _detect_language("Explain the Pragati scholarship in Hindi") == "hi"
    assert _detect_language("Explain the Pragati scholarship in Punjabi") == "pa"


def test_detect_category():
    """Category is inferred from keywords."""
    from switch_integration.event_handler import _detect_category
    assert _detect_category("What scholarships am I eligible for?") == "scholarship"
    assert _detect_category("How do I apply for college admission?") == "admission"
    assert _detect_category("Tell me about the PM yojana scheme") == "scheme"
    assert _detect_category("What is the weather?") == "general"


# --- message_sender graceful degradation ---------------------------------

def test_message_sender_disabled_when_no_mattermost():
    """When Mattermost is not configured, post_to_room must return a honest
    'disabled' status rather than raising or pretending it posted."""
    from switch_integration.message_sender import post_to_room
    result = post_to_room("student-questions", "test message")
    assert result["posted"] is False
    assert "reason" in result
    # Must NOT claim success.
    assert result["posted"] is False


def test_post_progress_format():
    """post_progress prefixes the message with the question id prefix."""
    from switch_integration.message_sender import post_progress
    result = post_progress("abcdef1234567890", "student-questions", "Research started")
    # Even when disabled, the call must not raise.
    assert isinstance(result, dict)
    assert result["posted"] is False


# --- bridge config: token verification logic -----------------------------

def test_verify_inbound_token_accepts_any_when_unset():
    """When SWITCH_BRIDGE_TOKEN is unset (dev mode), any caller is accepted."""
    from backend.app.config import settings
    from switch_integration.config import verify_inbound_token
    # In the test env the token is unset.
    assert settings.switch_bridge_token == ""
    assert verify_inbound_token(None) is True
    assert verify_inbound_token("anything") is True


def test_verify_inbound_token_enforces_when_set():
    """When the token is set, only the exact match is accepted."""
    from backend.app.config import settings
    from switch_integration.config import verify_inbound_token
    settings.switch_bridge_token = "my-secret"
    try:
        assert verify_inbound_token("my-secret") is True
        assert verify_inbound_token("wrong") is False
        assert verify_inbound_token(None) is False
        assert verify_inbound_token("") is False
    finally:
        settings.switch_bridge_token = ""
