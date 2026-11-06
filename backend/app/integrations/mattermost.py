"""Mattermost REST client helpers (kept thin — most posting goes through
switch_integration.message_sender)."""

from __future__ import annotations

from backend.app.config import settings


def configured() -> bool:
    return bool(
        settings.mattermost_enabled
        and settings.mattermost_base_url
        and (settings.mattermost_bot_token or settings.mattermost_incoming_webhook_url)
    )


def status() -> dict:
    return {
        "enabled": settings.mattermost_enabled,
        "base_url": settings.mattermost_base_url or None,
        "bot_token_configured": bool(settings.mattermost_bot_token),
        "incoming_webhook_configured": bool(settings.mattermost_incoming_webhook_url),
        "channels": {
            "student_questions": settings.mattermost_channel_student_questions,
            "research_updates": settings.mattermost_channel_research_updates,
            "translation": settings.mattermost_channel_translation,
            "human_review": settings.mattermost_channel_human_review,
            "final_guidance": settings.mattermost_channel_final_guidance,
        },
        "configured": configured(),
    }
