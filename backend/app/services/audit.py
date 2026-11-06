"""Audit logging.

Every meaningful state change is recorded as an AuditEvent row so the
dashboard and the demo can show a real, traceable timeline.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEvent


def record(
    db: Session,
    *,
    question_id: str | None,
    actor: str,
    event: str,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    row = AuditEvent(
        question_id=question_id,
        actor=actor,
        event=event,
        payload=payload or {},
    )
    db.add(row)
    db.flush()
    return row
