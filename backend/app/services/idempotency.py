"""Idempotency service: prevents duplicate event processing.

When Switch or a chat platform retries a webhook delivery (network blip,
timeout, etc.), the same event arrives twice. This module records every
processed event's key in the `processed_events` table. On a duplicate, the
bridge returns the original question_id instead of creating a new question.

The `event_key` is a composite: `{platform}:{event_id_or_payload_hash}`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import ProcessedEvent


def _event_key(platform: str, event_id: str | None, payload: dict[str, Any]) -> str:
    """Build a stable dedup key for an inbound event."""
    if event_id:
        return f"{platform}:{event_id}"
    # No native event ID → hash the payload (sorted for stability).
    raw = json.dumps(payload, sort_keys=True, default=str)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{platform}:hash:{h}"


def check_or_record(
    db: Session,
    *,
    platform: str,
    event_id: str | None,
    payload: dict[str, Any],
    question_id: str,
    ttl_days: int = 7,
) -> tuple[bool, str | None]:
    """Check if an event was already processed. If not, record it.

    Returns (is_duplicate, existing_question_id). When is_duplicate is True,
    existing_question_id is the question_id from the first processing. When
    False, the event was just recorded and the caller's question_id was stored.
    """
    key = _event_key(platform, event_id, payload)
    existing = db.query(ProcessedEvent).filter_by(event_key=key).first()
    if existing:
        return True, existing.question_id

    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    now = datetime.now(timezone.utc)
    db.add(ProcessedEvent(
        event_key=key,
        platform=platform,
        event_id=event_id,
        question_id=question_id,
        processed_at=now,
        expires_at=now + timedelta(days=ttl_days),
        payload_hash=payload_hash,
    ))
    db.flush()
    return False, None
