"""Questions API: submit, list, get detail, run workflow."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Question, QuestionStatus, User, UserRole, AuditEvent, AgentExecution, AgentName, ResearchResult
from backend.app.schemas import QuestionCreate, QuestionListOut, QuestionOut, ClaimEvidenceOut
from backend.app.security import rate_limiter, verify_review_secret
from backend.app.services.audit import record as audit_record

log = logging.getLogger("accessbridge.routes.questions")

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(
    payload: QuestionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> QuestionOut:
    if not rate_limiter.allow(request.client.host if request.client else "anon"):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    # Resolve or create a guest user when external_user is provided.
    user_id: str | None = None
    if payload.external_user:
        user = User(external_id=payload.external_user, display_name=payload.external_user, role=UserRole.student)
        db.add(user)
        db.flush()
        user_id = user.id

    q = Question(
        user_id=user_id,
        external_user=payload.external_user,
        platform=payload.platform,
        channel="student-questions",
        question_text=payload.question_text,
        category=payload.category,
        language=payload.language,
        status=QuestionStatus.received,
    )
    db.add(q)
    db.flush()
    audit_record(db, question_id=q.id, actor="api:questions", event="question_created",
                 payload={"platform": payload.platform, "language": payload.language})
    db.commit()

    background_tasks.add_task(_run_workflow, q.id)
    return _to_out(q)


@router.get("", response_model=list[QuestionListOut])
def list_questions(limit: int = 50, db: Session = Depends(get_db)) -> list[QuestionListOut]:
    rows = db.query(Question).order_by(desc(Question.created_at)).limit(limit).all()
    return [_to_list_out(r) for r in rows]


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(question_id: str, db: Session = Depends(get_db)) -> QuestionOut:
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return _to_out(q)


async def _run_workflow(question_id: str) -> None:
    """Background workflow runner used by the questions API."""
    from backend.app.database import session_scope
    from agents.orchestrator import run_workflow
    from switch_integration.message_sender import post_progress
    from backend.app.models import Question

    # Read the question's platform so progress goes to the right chat app.
    with session_scope() as db:
        q = db.get(Question, question_id)
        platform = q.platform if q else "mattermost"
        room = settings.mattermost_channel_student_questions

    def progress(msg: str) -> None:
        post_progress(question_id, room, msg, platform=platform)

    try:
        with session_scope() as db:
            await run_workflow(question_id, db, progress_sink=progress)
    except Exception as exc:
        log.exception("Workflow failed for %s", question_id)


def _to_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        question_text=q.question_text,
        language=q.language,  # type: ignore[arg-type]
        category=q.category,  # type: ignore[arg-type]
        status=q.status.value,
        platform=q.platform,
        channel=q.channel,
        external_user=q.external_user,
        created_at=q.created_at,
        updated_at=q.updated_at,
        error_message=q.error_message,
    )


def _to_list_out(q: Question) -> QuestionListOut:
    return QuestionListOut(
        id=q.id,
        question_text=q.question_text,
        language=q.language,  # type: ignore[arg-type]
        category=q.category,  # type: ignore[arg-type]
        status=q.status.value,
        created_at=q.created_at,
        external_user=q.external_user,
    )


# --- Evidence inspector ---------------------------------------------------

@router.get("/{question_id}/evidence", response_model=list[ClaimEvidenceOut])
def get_evidence(question_id: str, db: Session = Depends(get_db)) -> list[ClaimEvidenceOut]:
    """Evidence inspector: every claim linked to its source excerpt.

    Reads the evidence refs from the Research Agent's execution trace
    (stored in AgentExecution.details) and adds a freshness_days field
    computed from the retrieval timestamp.
    """
    from datetime import datetime, timezone

    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    # The research execution's details JSON contains the full ResearchResponse,
    # including the evidence list.
    research_exec = (
        db.query(AgentExecution)
        .filter_by(question_id=question_id, agent=AgentName.research)
        .order_by(AgentExecution.started_at.desc())
        .first()
    )
    if not research_exec or not research_exec.details:
        return []

    details = research_exec.details
    raw_evidence = details.get("evidence", [])
    now = datetime.now(timezone.utc)
    out: list[ClaimEvidenceOut] = []
    for ev in raw_evidence:
        retrieved = ev.get("retrieved_at")
        freshness = None
        if retrieved:
            try:
                dt = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
                freshness = (now - dt).total_seconds() / 86400.0
            except Exception:
                pass
        out.append(ClaimEvidenceOut(
            claim=ev.get("claim", ""),
            claim_type=ev.get("claim_type", "other"),
            source_url=ev.get("source_url", ""),
            source_title=ev.get("source_title"),
            excerpt=ev.get("excerpt", ""),
            retrieved_at=datetime.fromisoformat(ev["retrieved_at"].replace("Z", "+00:00")) if ev.get("retrieved_at") else now,
            confidence=ev.get("confidence", "uncertain"),
            notes=ev.get("notes"),
            freshness_days=freshness,
        ))
    return out


# --- Re-run research ------------------------------------------------------

@router.post("/{question_id}/rerun-research", response_model=dict)
async def rerun_research(
    question_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Let a coordinator request another research pass.

    Resets the question to `received` and re-runs the full workflow. The
    previous research/translation/guidance rows are replaced. The audit log
    records the re-run request.
    """
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    audit_record(db, question_id=question_id, actor="api:rerun-research",
                 event="rerun_requested", payload={"previous_status": q.status.value})
    q.status = QuestionStatus.received
    q.error_message = None
    db.commit()

    background_tasks.add_task(_run_workflow, question_id)
    return {
        "accepted": True,
        "question_id": question_id,
        "status": "received",
        "message": "Re-running research. The previous results will be replaced.",
    }


# --- Unsupported claims ---------------------------------------------------

@router.get("/{question_id}/unsupported-claims", response_model=list[dict])
def unsupported_claims(question_id: str, db: Session = Depends(get_db)) -> list[dict]:
    """Return claims that have no supporting source evidence (confidence=unavailable).

    Used by the review workspace to highlight what the coordinator should
    check manually before approving.
    """
    research_exec = (
        db.query(AgentExecution)
        .filter_by(question_id=question_id, agent=AgentName.research)
        .order_by(AgentExecution.started_at.desc())
        .first()
    )
    if not research_exec or not research_exec.details:
        return []
    evidence = research_exec.details.get("evidence", [])
    return [
        {"claim": ev.get("claim", ""), "claim_type": ev.get("claim_type", "other"),
         "notes": ev.get("notes", "No supporting source.")}
        for ev in evidence
        if ev.get("confidence") == "unavailable"
    ]
