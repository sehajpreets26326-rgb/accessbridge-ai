"""Slack integration adapter.

Posts messages to a Slack channel via the Slack Web API (bot token).
Inbound messages arrive through the Switch Console Agent Bridge.

Slack API docs: https://api.slack.com/docs
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

log = logging.getLogger("accessbridge.integrations.slack")


def configured() -> bool:
    return bool(settings.slack_bot_token and settings.slack_channel)


def status() -> dict[str, Any]:
    return {
        "enabled": bool(settings.slack_bot_token),
        "bot_token_configured": bool(settings.slack_bot_token),
        "channel": settings.slack_channel or None,
        "configured": configured(),
    }


def post_to_channel(text: str) -> dict[str, Any]:
    """Post a message to the configured Slack channel."""
    if not configured():
        log.info("[slack:not-configured] %s", text[:120])
        return {"posted": False, "reason": "not_configured"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://slack.com/api/chat.postMessage",
                json={
                    "channel": settings.slack_channel,
                    "text": text[:40000 - 100],  # Slack's text cap is ~40k
                    "username": "AccessBridge AI",
                },
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            )
        body = resp.json()
        if resp.status_code < 400 and body.get("ok"):
            return {"posted": True, "method": "bot_token", "channel": settings.slack_channel}
        reason = body.get("error", f"http_{resp.status_code}")
        log.warning("Slack post failed: %s", reason)
        return {"posted": False, "reason": reason}
    except Exception as exc:
        log.warning("Slack post error: %s", exc)
        return {"posted": False, "reason": "exception", "error": str(exc)}
