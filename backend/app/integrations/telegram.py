"""Telegram integration adapter.

Posts messages to a Telegram chat via the Telegram Bot API.
Inbound messages arrive through the Switch Console Agent Bridge, or via
Telegram's getUpdates polling (not included here; requires a persistent
process).

Telegram API docs: https://core.telegram.org/bots/api
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

log = logging.getLogger("accessbridge.integrations.telegram")


def configured() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def status() -> dict[str, Any]:
    return {
        "enabled": bool(settings.telegram_bot_token),
        "bot_token_configured": bool(settings.telegram_bot_token),
        "chat_id": settings.telegram_chat_id or None,
        "configured": configured(),
    }


def post_to_channel(text: str) -> dict[str, Any]:
    """Post a message to the configured Telegram chat."""
    if not configured():
        log.info("[telegram:not-configured] %s", text[:120])
        return {"posted": False, "reason": "not_configured"}

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": text[:4096],  # Telegram's message length cap
                "parse_mode": "Markdown",
            })
        body = resp.json()
        if resp.status_code < 400 and body.get("ok"):
            return {"posted": True, "method": "bot_api", "chat_id": settings.telegram_chat_id}
        reason = body.get("description", f"http_{resp.status_code}")
        log.warning("Telegram post failed: %s", reason)
        return {"posted": False, "reason": reason}
    except Exception as exc:
        log.warning("Telegram post error: %s", exc)
        return {"posted": False, "reason": "exception", "error": str(exc)}
