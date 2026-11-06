"""Discord integration adapter.

Sends messages back to a Discord channel via the Discord REST API (bot token).
Inbound messages arrive through the Switch Console Agent Bridge (which
normalises Discord events into our SwitchBridgeEvent), so this module handles
only the outbound side: posting progress + final guidance back into Discord.

To receive inbound Discord messages, either:
1. Use the Switch Console (recommended) — it dispatches Discord room messages
   to our /switch/bridge endpoint as normalised events.
2. Run a Discord gateway bot (not included here; requires a persistent
   WebSocket process) and forward messages to /switch/bridge.

Discord API docs: https://discord.com/developers/docs/intro
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

log = logging.getLogger("accessbridge.integrations.discord")


def configured() -> bool:
    return bool(settings.discord_bot_token and settings.discord_channel_id)


def status() -> dict[str, Any]:
    return {
        "enabled": bool(settings.discord_bot_token),
        "bot_token_configured": bool(settings.discord_bot_token),
        "channel_id": settings.discord_channel_id or None,
        "configured": configured(),
    }


def post_to_channel(text: str) -> dict[str, Any]:
    """Post a message to the configured Discord channel via the bot token."""
    if not configured():
        log.info("[discord:not-configured] %s", text[:120])
        return {"posted": False, "reason": "not_configured"}

    url = f"https://discord.com/api/v10/channels/{settings.discord_channel_id}/messages"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                json={"content": text[:2000]},  # Discord's message length cap
                headers={"Authorization": f"Bot {settings.discord_bot_token}"},
            )
        if resp.status_code < 400:
            return {"posted": True, "method": "bot_token", "channel_id": settings.discord_channel_id}
        log.warning("Discord post failed: %s %s", resp.status_code, resp.text[:200])
        return {"posted": False, "reason": f"http_{resp.status_code}"}
    except Exception as exc:
        log.warning("Discord post error: %s", exc)
        return {"posted": False, "reason": "exception", "error": str(exc)}
