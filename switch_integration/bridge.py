"""The Switch Agent Bridge.

This is the genuine integration boundary between Switch and AccessBridge:

- The Switch Console (desktop app) creates an agent that points its bridge
  endpoint at this FastAPI route group. When a human sends a message in a
  connected Mattermost/Discord room, Switch dispatches the room message to our
  `/switch/bridge` endpoint as a normalised JSON event.

- The same endpoint also accepts raw Mattermost outgoing-webhook payloads, so
  the project is fully testable with Mattermost alone (Switch Console is an
  additional layer on top, not a hard requirement for local testing).

The bridge:
1. Verifies the inbound token (when configured).
2. Normalises the payload via `event_handler.from_raw`.
3. Creates a Question row.
4. Schedules the orchestrator workflow (async background task).
5. Returns an immediate ack so Switch/Mattermost see a 200 right away.
6. The orchestrator posts progress + final guidance back into the rooms via
   `message_sender`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.app.database import session_scope
from backend.app.models import AuditEvent, Question, QuestionStatus, User, UserRole
from backend.app.schemas import SwitchBridgeAck, SwitchBridgeEvent
from backend.app.services.audit import record as audit_record
from .config import MATTERMOST_WEBHOOK_PATH, BRIDGE_PATH, HEALTH_PATH, verify_inbound_token
from .event_handler import from_raw
from .message_sender import post_progress

log = logging.getLogger("accessbridge.switch_bridge")

router = APIRouter(prefix="", tags=["switch"])


@router.get(HEALTH_PATH)
def health() -> dict[str, Any]:
    """Switch bridge health check — used by the dashboard's connection status."""
    from backend.app.services.llm import switch_trust_status
    from backend.app.config import settings
    from switch_integration.message_sender import all_platform_status
    return {
        "bridge_enabled": True,
        "switch_trust": switch_trust_status(),
        "bridge_token_configured": bool(settings.switch_bridge_token),
        "platforms": all_platform_status(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.post(BRIDGE_PATH, response_model=SwitchBridgeAck)
async def switch_bridge(event: SwitchBridgeEvent, background_tasks: BackgroundTasks) -> SwitchBridgeAck:
    """Switch Console Agent Bridge endpoint."""
    if not verify_inbound_token(event.token):
        raise HTTPException(status_code=401, detail="Invalid bridge token.")
    return await _dispatch(event, background_tasks, source="switch")


@router.post(MATTERMOST_WEBHOOK_PATH, response_model=SwitchBridgeAck)
async def mattermost_webhook(request: Request, background_tasks: BackgroundTasks) -> SwitchBridgeAck:
    """Raw Mattermost outgoing-webhook endpoint.

    Mattermost posts form-encoded or JSON payloads. We accept either.
    """
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
        else:
            form = await request.form()
            payload = dict(form)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse Mattermost payload: {exc}") from exc

    token = payload.get("token")
    if not verify_inbound_token(token):
        raise HTTPException(status_code=401, detail="Invalid Mattermost webhook token.")

    event = from_raw(payload)
    return await _dispatch(event, background_tasks, source="mattermost")


async def _dispatch(event: SwitchBridgeEvent, background_tasks: BackgroundTasks, *, source: str) -> SwitchBridgeAck:
    if not event.text:
        raise HTTPException(status_code=400, detail="Empty message text.")

    # Persist the question synchronously so we can return a real question_id.
    with session_scope() as db:
        # --- Idempotency: check for duplicate event delivery ---
        from backend.app.services.idempotency import check_or_record
        event_id = getattr(event, "event_id", None) or event.sender_id and f"{event.sender_id}:{event.text[:40]}"
        is_dup, existing_qid = check_or_record(
            db,
            platform=event.platform,
            event_id=event_id,
            payload={"room": event.room, "sender": event.sender, "text": event.text},
            question_id="",  # filled below; placeholder — will update
        )
        if is_dup and existing_qid:
            audit_record(db, question_id=existing_qid, actor=f"switch_bridge:{source}",
                         event="duplicate_event_rejected",
                         payload={"event_id": event_id, "platform": event.platform})
            db.commit()
            return SwitchBridgeAck(
                accepted=True,
                question_id=existing_qid,
                status="duplicate",
                message=f"Duplicate event already processed as {existing_qid[:8]}. No new question created.",
            )

        user_id: str | None = None
        if event.sender_id:
            user = db.query(User).filter_by(external_id=event.sender_id).first()
            if not user:
                user = User(
                    external_id=event.sender_id,
                    display_name=event.sender,
                    role=UserRole.student,
                )
                db.add(user)
                db.flush()
            user_id = user.id

        question = Question(
            user_id=user_id,
            external_user=event.sender,
            platform=event.platform,
            channel=event.room,
            question_text=event.text,
            category=event.category,
            language=event.language,
            status=QuestionStatus.received,
        )
        db.add(question)
        db.flush()

        # Update the idempotency record with the real question_id.
        from backend.app.models import ProcessedEvent
        # The check_or_record call above already inserted a row with question_id=""
        # — update it now.
        from backend.app.services.idempotency import _event_key
        key = _event_key(event.platform, event_id, {"room": event.room, "sender": event.sender, "text": event.text})
        row = db.query(ProcessedEvent).filter_by(event_key=key).first()
        if row:
            row.question_id = question.id

        audit_record(
            db,
            question_id=question.id,
            actor=f"switch_bridge:{source}",
            event="message_received",
            payload={"room": event.room, "sender": event.sender, "platform": event.platform,
                     "correlation_id": question.id},
        )
        question_id = question.id
        platform = event.platform

    # Run the workflow in the background so the bridge returns immediately.
    background_tasks.add_task(_run_workflow_background, question_id, event.room, platform)

    return SwitchBridgeAck(
        accepted=True,
        question_id=question_id,
        status="received",
        message=f"AccessBridge received the question in #{event.room}. Research is starting.",
    )


async def _run_workflow_background(question_id: str, room: str, platform: str = "mattermost") -> None:
    """Background task: run the orchestrator and post progress to the room."""
    from agents.orchestrator import run_workflow

    def progress(msg: str) -> None:
        post_progress(question_id, room, msg, platform=platform)

    try:
        with session_scope() as db:
            await run_workflow(question_id, db, progress_sink=progress)
    except Exception as exc:
        log.exception("Background workflow failed for %s", question_id)
        post_progress(question_id, room, f"Workflow failed: {exc}", platform=platform)
