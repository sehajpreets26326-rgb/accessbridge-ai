"""Tests for multi-platform adapters, idempotency, and correlation IDs.

Covers:
- Discord / Slack / Telegram adapter status + graceful-not-configured behavior
- Idempotency: duplicate event detection + rejection
- Correlation IDs in agent messages
- Platform routing in the message sender
"""
from __future__ import annotations

import pytest


# --- Platform adapter status ----------------------------------------------

def test_discord_adapter_status_when_not_configured():
    """Discord adapter must report configured=False when no token is set."""
    from backend.app.integrations import discord
    s = discord.status()
    assert s["configured"] is False
    assert s["bot_token_configured"] is False


def test_slack_adapter_status_when_not_configured():
    from backend.app.integrations import slack
    s = slack.status()
    assert s["configured"] is False


def test_telegram_adapter_status_when_not_configured():
    from backend.app.integrations import telegram
    s = telegram.status()
    assert s["configured"] is False


def test_discord_post_returns_disabled_when_not_configured():
    """Posting to Discord without a token must return a disabled status, not raise."""
    from backend.app.integrations import discord
    result = discord.post_to_channel("test message")
    assert result["posted"] is False
    assert "reason" in result


def test_slack_post_returns_disabled_when_not_configured():
    from backend.app.integrations import slack
    result = slack.post_to_channel("test message")
    assert result["posted"] is False


def test_telegram_post_returns_disabled_when_not_configured():
    from backend.app.integrations import telegram
    result = telegram.post_to_channel("test message")
    assert result["posted"] is False


def test_all_platform_status_returns_every_platform():
    """all_platform_status must report status for all 5 supported platforms."""
    from switch_integration.message_sender import all_platform_status
    status = all_platform_status()
    for name in ("mattermost", "discord", "slack", "telegram", "teams"):
        assert name in status
        assert "configured" in status[name]


# --- Multi-platform message routing ---------------------------------------

def test_post_to_room_routes_to_discord(monkeypatch):
    """When platform=discord, post_to_room must call the Discord adapter."""
    from switch_integration import message_sender
    called = {}
    def fake_discord_post(text):
        called["text"] = text
        return {"posted": False, "reason": "test"}
    from backend.app.integrations import discord
    monkeypatch.setattr(discord, "post_to_channel", fake_discord_post)
    # post_to_room(channel, text, *, platform) — text is the 2nd positional arg.
    result = message_sender.post_to_room("chan", "hello discord", platform="discord")
    assert called["text"] == "hello discord"
    assert result["reason"] == "test"


def test_post_to_room_routes_to_slack(monkeypatch):
    from switch_integration import message_sender
    from backend.app.integrations import slack
    called = {}
    monkeypatch.setattr(slack, "post_to_channel", lambda t: called.setdefault("t", t) or {"posted": False})
    message_sender.post_to_room("chan", "hello slack", platform="slack")
    assert called["t"] == "hello slack"


def test_post_to_room_routes_to_telegram(monkeypatch):
    from switch_integration import message_sender
    from backend.app.integrations import telegram
    called = {}
    monkeypatch.setattr(telegram, "post_to_channel", lambda t: called.setdefault("t", t) or {"posted": False})
    message_sender.post_to_room("chan", "hello telegram", platform="telegram")
    assert called["t"] == "hello telegram"


def test_post_to_room_defaults_to_mattermost():
    """Without a platform arg, post_to_room must use Mattermost."""
    from switch_integration import message_sender
    result = message_sender.post_to_room("student-questions", "test message")
    # Mattermost not configured in test env → disabled.
    assert result["posted"] is False
    assert result.get("channel") == "student-questions"


# --- Idempotency ----------------------------------------------------------

def test_idempotency_detects_duplicate_event(db_session):
    """A duplicate event (same platform + event_id) must be detected."""
    from backend.app.services.idempotency import check_or_record
    from backend.app.models import Question, QuestionStatus

    q = Question(question_text="Idempotency test question", language="en",
                 category="scholarship", status=QuestionStatus.received)
    db_session.add(q); db_session.commit(); db_session.refresh(q)

    # First call: not a duplicate.
    is_dup, existing_qid = check_or_record(
        db_session, platform="discord", event_id="msg-001",
        payload={"text": "test"}, question_id=q.id,
    )
    assert is_dup is False
    db_session.commit()

    # Second call with same event_id: is a duplicate.
    is_dup2, existing_qid2 = check_or_record(
        db_session, platform="discord", event_id="msg-001",
        payload={"text": "test"}, question_id="different-id",
    )
    assert is_dup2 is True
    assert existing_qid2 == q.id


def test_idempotency_different_events_not_duplicates(db_session):
    """Different event IDs must not be treated as duplicates."""
    from backend.app.services.idempotency import check_or_record
    from backend.app.models import Question, QuestionStatus

    q1 = Question(question_text="Q1", language="en", category="scholarship", status=QuestionStatus.received)
    q2 = Question(question_text="Q2", language="en", category="scholarship", status=QuestionStatus.received)
    db_session.add_all([q1, q2]); db_session.commit(); db_session.refresh(q1); db_session.refresh(q2)

    is_dup1, _ = check_or_record(db_session, platform="slack", event_id="s-1",
                                  payload={"text": "a"}, question_id=q1.id)
    is_dup2, _ = check_or_record(db_session, platform="slack", event_id="s-2",
                                  payload={"text": "b"}, question_id=q2.id)
    assert is_dup1 is False
    assert is_dup2 is False


def test_idempotency_payload_hash_fallback(db_session):
    """When no event_id is provided, the payload hash is used for dedup."""
    from backend.app.services.idempotency import check_or_record, _event_key
    from backend.app.models import Question, QuestionStatus

    q = Question(question_text="Hash test", language="en", category="scholarship",
                 status=QuestionStatus.received)
    db_session.add(q); db_session.commit(); db_session.refresh(q)

    payload = {"text": "hash-based dedup test", "sender": "alice"}
    is_dup1, _ = check_or_record(db_session, platform="telegram", event_id=None,
                                  payload=payload, question_id=q.id)
    assert is_dup1 is False
    db_session.commit()

    # Same payload again → duplicate.
    is_dup2, existing = check_or_record(db_session, platform="telegram", event_id=None,
                                         payload=payload, question_id="other")
    assert is_dup2 is True
    assert existing == q.id


# --- Correlation IDs in agent messages ------------------------------------

def test_research_request_has_correlation_id():
    """ResearchRequest must carry correlation_id + task_id."""
    from agents.messages import ResearchRequest
    req = ResearchRequest(
        question_id="q-1", question_text="test question",
        correlation_id="corr-123", task_id="research-q-1",
    )
    assert req.correlation_id == "corr-123"
    assert req.task_id == "research-q-1"
    assert req.retry_count == 0


def test_language_request_has_correlation_id():
    from agents.messages import LanguageRequest, ResearchResponse
    from datetime import datetime, timezone
    rr = ResearchResponse(question_id="q-1", retrieved_at=datetime.now(timezone.utc))
    req = LanguageRequest(
        question_id="q-1", target_language="hi", research=rr,
        correlation_id="corr-123", task_id="lang-q-1",
    )
    assert req.correlation_id == "corr-123"


def test_guidance_request_has_correlation_id():
    from agents.messages import GuidanceRequest, ResearchResponse, LanguageResponse
    from datetime import datetime, timezone
    rr = ResearchResponse(question_id="q-1", retrieved_at=datetime.now(timezone.utc))
    lr = LanguageResponse(question_id="q-1", language="en", simplified_text="test")
    req = GuidanceRequest(
        question_id="q-1", question_text="test", research=rr, translation=lr,
        correlation_id="corr-123", task_id="guide-q-1",
    )
    assert req.correlation_id == "corr-123"


@pytest.mark.asyncio
async def test_orchestrator_passes_correlation_id(db_session):
    """The orchestrator must set correlation_id on every agent request."""
    from agents.orchestrator import run_workflow
    from backend.app.models import Question, QuestionStatus, AgentExecution, AgentName

    q = Question(
        question_text="Correlation ID test: AICTE Pragati scholarship for girls eligibility",
        language="en", category="scholarship", status=QuestionStatus.received,
    )
    db_session.add(q); db_session.commit(); db_session.refresh(q)
    await run_workflow(q.id, db_session)
    db_session.commit()

    # Every agent execution's details must carry the correlation_id.
    execs = db_session.query(AgentExecution).filter_by(question_id=q.id).all()
    assert len(execs) == 3
    for e in execs:
        details = e.details or {}
        assert details.get("correlation_id") == q.id
