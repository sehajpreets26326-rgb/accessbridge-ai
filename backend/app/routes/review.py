"""Human review API: approve / reject / request corrections."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    AuditEvent,
    GuidanceChecklist,
    HumanApproval,
    Question,
    QuestionStatus,
    ReviewAction,
    User,
    UserRole,
)
from backend.app.schemas import ReviewCreate, ReviewOut
from backend.app.security import rate_limiter, verify_review_secret
from backend.app.services.audit import record as audit_record

log = logging.getLogger("accessbridge.routes.review")

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/{question_id}", response_model=ReviewOut, status_code=201)
def review_question(
    question_id: str,
    payload: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ReviewOut:
    if not rate_limiter.allow(request.client.host if request.client else "anon"):
        raise HTTPException(status_code=429, detail="Too many requests.")

    if not verify_review_secret(payload.secret):
        raise HTTPException(status_code=403, detail="Review secret required but not provided or incorrect.")

    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if q.status != QuestionStatus.awaiting_review:
        raise HTTPException(
            status_code=409,
            detail=f"Question is not awaiting review (current status: {q.status.value}).",
        )

    # Resolve or create a coordinator user.
    reviewer = db.query(User).filter_by(display_name=payload.reviewer_name, role=UserRole.coordinator).first()
    if not reviewer:
        reviewer = User(display_name=payload.reviewer_name, role=UserRole.coordinator)
        db.add(reviewer)
        db.flush()

    approval = HumanApproval(
        question_id=question_id,
        reviewer_id=reviewer.id,
        reviewer_name=payload.reviewer_name,
        action=ReviewAction(payload.action),
        note=payload.note,
    )
    db.add(approval)
    db.flush()

    if payload.action == "approved":
        q.status = QuestionStatus.approved
    elif payload.action == "rejected":
        q.status = QuestionStatus.rejected
    else:
        q.status = QuestionStatus.awaiting_review  # corrections requested → back to review queue

    audit_record(
        db,
        question_id=question_id,
        actor=f"coordinator:{payload.reviewer_name}",
        event=f"review_{payload.action}",
        payload={"note": payload.note},
    )

    db.commit()

    # Post a cheering-teammate progress message into the room.
    from backend.app.services.teammate import teammate_message
    from switch_integration.message_sender import post_progress
    from backend.app.config import settings
    tm_event = {"approved": "approved", "rejected": "rejected",
                "corrections_requested": "corrections_requested"}.get(payload.action, "awaiting_review")
    tm = teammate_message(tm_event, reviewer=payload.reviewer_name)
    post_progress(question_id, settings.mattermost_channel_human_review, tm)

    return ReviewOut(
        id=approval.id,
        question_id=question_id,
        reviewer_name=approval.reviewer_name,
        action=approval.action.value,
        note=approval.note,
        created_at=approval.created_at,
    )


@router.get("/{question_id}", response_model=list[ReviewOut])
def list_reviews(question_id: str, db: Session = Depends(get_db)) -> list[ReviewOut]:
    rows = db.query(HumanApproval).filter_by(question_id=question_id).order_by(HumanApproval.created_at).all()
    return [
        ReviewOut(
            id=r.id,
            question_id=r.question_id,
            reviewer_name=r.reviewer_name,
            action=r.action.value,
            note=r.note,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{question_id}/deliver", response_model=dict)
def deliver(question_id: str, db: Session = Depends(get_db)) -> dict:
    """Mark an approved question as delivered and post final guidance to the room."""
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if q.status != QuestionStatus.approved:
        raise HTTPException(status_code=409, detail=f"Question must be approved first (status: {q.status.value}).")

    checklist = db.query(GuidanceChecklist).filter_by(question_id=question_id).first()
    text = _render_final(q, checklist)

    from switch_integration.message_sender import post_final_guidance
    from backend.app.config import settings
    platform = q.platform or "mattermost"
    result = post_final_guidance(question_id, settings.mattermost_channel_final_guidance, text, platform=platform)

    q.status = QuestionStatus.delivered
    audit_record(db, question_id=question_id, actor="api:review", event="delivered",
                 payload={"room": settings.mattermost_channel_final_guidance, "post_result": result})
    db.commit()

    # Post a cheering-teammate message into the final-guidance room alongside
    # the guidance text itself.
    from backend.app.services.teammate import teammate_message
    from switch_integration.message_sender import post_progress
    post_progress(question_id, settings.mattermost_channel_final_guidance,
                  teammate_message("delivered"))

    return {"delivered": True, "post_result": result, "final_text": text}


def _render_final(q: Question, checklist: GuidanceChecklist | None) -> str:
    parts = [f"Final guidance for: {q.question_text}", ""]
    if checklist:
        if checklist.eligibility_assessment:
            parts.append("Eligibility assessment:")
            parts.append(checklist.eligibility_assessment)
            parts.append("")
        if checklist.items:
            parts.append("Application checklist:")
            for i, item in enumerate(checklist.items or [], 1):
                title = item.get("title", "")
                detail = item.get("detail", "")
                parts.append(f"  {i}. [{item.get('status','todo').upper()}] {title} — {detail}")
            parts.append("")
        if checklist.uncertainty_warnings:
            parts.append("Uncertainty warnings:")
            for w in checklist.uncertainty_warnings:
                parts.append(f"  - {w}")
            parts.append("")
        if checklist.missing_information:
            parts.append("Still needed from the student:")
            for m in checklist.missing_information:
                parts.append(f"  - {m}")
    else:
        parts.append("No checklist was generated for this question.")
    parts.append("")
    parts.append("Reviewed and approved by a human coordinator. Verify on the official portal before applying.")
    return "\n".join(parts)
