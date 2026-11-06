"""Post progress and final-guidance messages back into the chat rooms.

Multi-platform: when a question arrives from a specific platform (recorded on
the Question row), progress messages are posted back to that platform. When
the platform is Mattermost and a bot token is configured, we use the REST API.
When Discord/Slack/Telegram/Teams is the source platform, we use that
platform's adapter. When nothing is configured, messages are logged only —
the workflow still completes and the dashboard shows them.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

log = logging.getLogger("accessbridge.message_sender")


def _enabled() -> bool:
    return bool(settings.mattermost_enabled and (settings.mattermost_bot_token or settings.mattermost_incoming_webhook_url))


def post_to_room(channel: str, text: str, *, thread_id: str | None = None,
                 platform: str = "mattermost") -> dict[str, Any]:
    """Post a message to a chat platform channel.

    When `platform` is mattermost, use the Mattermost REST API (preferred) or
    an incoming webhook. For discord/slack/telegram/teams, delegate to the
    platform adapter. When the platform is not configured, log and return a
    disabled status.
    """
    if platform == "discord":
        from backend.app.integrations import discord
        return discord.post_to_channel(text)
    if platform == "slack":
        from backend.app.integrations import slack
        return slack.post_to_channel(text)
    if platform == "telegram":
        from backend.app.integrations import telegram
        return telegram.post_to_channel(text)
    if platform == "teams":
        return _post_to_teams(text)

    # Default: Mattermost.
    return _post_to_mattermost(channel, text, thread_id=thread_id)


def _post_to_mattermost(channel: str, text: str, *, thread_id: str | None = None) -> dict[str, Any]:
    if not settings.mattermost_enabled or not settings.mattermost_base_url:
        log.info("[mattermost:disabled] #%s | %s", channel, text[:120])
        return {"posted": False, "reason": "mattermost_disabled", "channel": channel}

    base = settings.mattermost_base_url.rstrip("/")

    if settings.mattermost_bot_token:
        try:
            payload = {"channel": channel, "message": text}
            if thread_id:
                payload["root_id"] = thread_id
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{base}/api/v4/posts",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.mattermost_bot_token}"},
                )
            if resp.status_code < 400:
                return {"posted": True, "channel": channel, "method": "bot_token"}
            log.warning("Mattermost bot-token post failed: %s %s", resp.status_code, resp.text[:200])
            return {"posted": False, "reason": f"http_{resp.status_code}", "channel": channel}
        except Exception as exc:
            log.warning("Mattermost bot-token post error: %s", exc)
            return {"posted": False, "reason": "exception", "channel": channel, "error": str(exc)}

    if settings.mattermost_incoming_webhook_url:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    settings.mattermost_incoming_webhook_url,
                    json={"text": text, "username": "AccessBridge AI"},
                )
            if resp.status_code < 400:
                return {"posted": True, "channel": channel, "method": "incoming_webhook"}
            return {"posted": False, "reason": f"http_{resp.status_code}", "channel": channel}
        except Exception as exc:
            log.warning("Mattermost webhook post error: %s", exc)
            return {"posted": False, "reason": "exception", "channel": channel, "error": str(exc)}

    log.info("[mattermost:no-creds] #%s | %s", channel, text[:120])
    return {"posted": False, "reason": "no_credentials", "channel": channel}


def _post_to_teams(text: str) -> dict[str, Any]:
    """Post to Microsoft Teams via an incoming webhook (Power Automate)."""
    if not settings.teams_incoming_webhook_url:
        log.info("[teams:not-configured] %s", text[:120])
        return {"posted": False, "reason": "not_configured"}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                settings.teams_incoming_webhook_url,
                json={"text": text, "title": "AccessBridge AI"},
            )
        if resp.status_code < 400:
            return {"posted": True, "method": "incoming_webhook"}
        return {"posted": False, "reason": f"http_{resp.status_code}"}
    except Exception as exc:
        log.warning("Teams webhook post error: %s", exc)
        return {"posted": False, "reason": "exception", "error": str(exc)}


def post_progress(question_id: str, room: str, message: str, *, platform: str = "mattermost") -> dict[str, Any]:
    return post_to_room(room, f"[AccessBridge · {question_id[:8]}] {message}", platform=platform)


def post_final_guidance(question_id: str, room: str, guidance_text: str, *, platform: str = "mattermost") -> dict[str, Any]:
    return post_to_room(room, f"[AccessBridge · final · {question_id[:8]}]\n{guidance_text}", platform=platform)


def all_platform_status() -> dict[str, Any]:
    """Return the connection status of every supported platform."""
    from backend.app.integrations import mattermost, discord, slack, telegram
    return {
        "mattermost": mattermost.status(),
        "discord": discord.status(),
        "slack": slack.status(),
        "telegram": telegram.status(),
        "teams": {
            "enabled": bool(settings.teams_incoming_webhook_url),
            "webhook_configured": bool(settings.teams_incoming_webhook_url),
            "configured": bool(settings.teams_incoming_webhook_url),
            "note": "Outbound only; inbound requires Azure Bot Service.",
        },
    }
