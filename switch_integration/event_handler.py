"""Normalise raw inbound payloads into the SwitchBridgeEvent schema.

Switch Console dispatches a normalised room-message event to our bridge. When
Mattermost is connected directly (without Switch Console in front), Mattermost
sends an outgoing-webhook payload with a different shape. This module converts
both into the single `SwitchBridgeEvent` the orchestrator consumes.
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.schemas import Language, SwitchBridgeEvent


_CATEGORY_KEYWORDS = {
    "scholarship": ("scholarship", "scholarships", "fellowship", "stipend", "fee waiver", "aid"),
    "admission": ("admission", "admissions", "entrance", "application form", "apply for college"),
    "scheme": ("scheme", "yojana", "scheme", "government scheme", "subsidy"),
}


def from_mattermost_webhook(payload: dict[str, Any]) -> SwitchBridgeEvent:
    """Convert a Mattermost outgoing-webhook payload into a SwitchBridgeEvent."""
    text = (payload.get("text") or "").strip()
    # Mattermost may prefix the bot trigger word; strip it.
    trigger = payload.get("trigger_word")
    if trigger and text.lower().startswith(trigger.lower()):
        text = text[len(trigger):].strip()
    return SwitchBridgeEvent(
        room=payload.get("channel_name") or "student-questions",
        platform="mattermost",
        sender=payload.get("user_name") or "anonymous",
        sender_id=payload.get("user_id"),
        text=text,
        language=_detect_language(text),
        category=_detect_category(text),
        token=payload.get("token"),
    )


def from_switch_event(payload: dict[str, Any]) -> SwitchBridgeEvent:
    """Convert a Switch Console Agent Bridge event into a SwitchBridgeEvent.

    Switch dispatches a room message with the room name, sender display name,
    and the message text. The bridge normalises it here.
    """
    return SwitchBridgeEvent(
        room=payload.get("room") or "student-questions",
        platform=payload.get("platform") or "switch",
        sender=payload.get("sender") or "anonymous",
        sender_id=payload.get("sender_id"),
        text=(payload.get("text") or "").strip(),
        language=payload.get("language") or _detect_language(payload.get("text") or ""),
        category=payload.get("category") or _detect_category(payload.get("text") or ""),
        token=payload.get("token"),
    )


def from_raw(payload: dict[str, Any]) -> SwitchBridgeEvent:
    """Auto-detect payload shape and normalise."""
    if "channel_name" in payload or "user_name" in payload or "trigger_word" in payload:
        return from_mattermost_webhook(payload)
    if "room" in payload or "sender" in payload:
        return from_switch_event(payload)
    # Fall back: treat as a plain text event.
    text = payload.get("text") or json.dumps(payload)
    return SwitchBridgeEvent(
        room=payload.get("room", "student-questions"),
        platform="switch",
        sender=payload.get("sender", "anonymous"),
        text=text,
        language=_detect_language(text),
        category=_detect_category(text),
    )


_LANG_HINTS = {
    "hi": ("hindi", "हिंदी", "हिन्दी", "बताओ", "क्या", "कैसे"),
    "pa": ("punjabi", "ਪੰਜਾਬੀ", "ਦੱਸੋ", "ਕੀ", "ਕਿਵੇਂ"),
}


def _detect_language(text: str) -> Language:
    low = (text or "").lower()
    # Explicit request.
    for lang, hints in _LANG_HINTS.items():
        if any(h in low for h in hints if h.isascii()):
            return lang  # type: ignore[return-value]
    # Script-based detection (Devanagari / Gurmukhi).
    for ch in text or "":
        if "\u0900" <= ch <= "\u097F":  # Devanagari
            return "hi"
        if "\u0A00" <= ch <= "\u0A7F":  # Gurmukhi
            return "pa"
    return "en"


def _detect_category(text: str) -> str:
    low = (text or "").lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(k in low for k in keywords):
            return cat
    return "general"
