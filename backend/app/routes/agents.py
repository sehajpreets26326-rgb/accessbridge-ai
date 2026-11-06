"""Agent workspace API: real per-question agent execution traces."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AgentExecution, Question, ResearchResult, Source, TranslationResult, GuidanceChecklist, HumanApproval, AuditEvent
from backend.app.schemas import AgentExecutionOut, ClaimEvidenceOut, GuidanceOut, ResearchResultOut, SourceOut, TranslationOut, ChecklistItem

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/executions", response_model=list[AgentExecutionOut])
def recent_executions(limit: int = 30, db: Session = Depends(get_db)) -> list[AgentExecutionOut]:
    rows = db.query(AgentExecution).order_by(desc(AgentExecution.started_at)).limit(limit).all()
    return [_exec(r) for r in rows]


@router.get("/question/{question_id}", response_model=dict)
def question_workspace(question_id: str, db: Session = Depends(get_db)) -> dict:
    """Full workspace view for one question: research, translation, guidance, executions, audit."""
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    research = db.query(ResearchResult).filter_by(question_id=question_id).first()
    translation = db.query(TranslationResult).filter_by(question_id=question_id).first()
    checklist = db.query(GuidanceChecklist).filter_by(question_id=question_id).first()
    executions = db.query(AgentExecution).filter_by(question_id=question_id).order_by(AgentExecution.started_at).all()
    approvals = db.query(HumanApproval).filter_by(question_id=question_id).order_by(HumanApproval.created_at).all()
    audit = db.query(AuditEvent).filter_by(question_id=question_id).order_by(AuditEvent.created_at).all()

    # Pull evidence/conflicts/duplicates from the latest research execution's
    # details trace (the Research Agent stores the full ResearchResponse there).
    research_exec = next(
        (e for e in executions if e.agent.value == "research" and e.details), None
    )
    evidence_data = []
    conflicts = []
    duplicates = []
    if research_exec and research_exec.details:
        evidence_data = research_exec.details.get("evidence", [])
        conflicts = research_exec.details.get("conflicting_claims", [])
        duplicates = research_exec.details.get("duplicate_sources", [])

    return {
        "question": {
            "id": q.id,
            "text": q.question_text,
            "language": q.language,
            "category": q.category,
            "status": q.status.value,
            "platform": q.platform,
            "channel": q.channel,
            "created_at": q.created_at.isoformat(),
            "external_user": q.external_user,
            "error_message": q.error_message,
        },
        "research": _research(research) if research else None,
        "evidence": evidence_data,
        "conflicting_claims": conflicts,
        "duplicate_sources": duplicates,
        "translation": _translation(translation) if translation else None,
        "guidance": _guidance(checklist) if checklist else None,
        "executions": [_exec(e) for e in executions],
        "approvals": [
            {"reviewer": a.reviewer_name, "action": a.action.value, "note": a.note, "at": a.created_at.isoformat()}
            for a in approvals
        ],
        "audit": [
            {"actor": a.actor, "event": a.event, "at": a.created_at.isoformat(), "payload": a.payload}
            for a in audit
        ],
    }


def _research(r: ResearchResult) -> ResearchResultOut:
    return ResearchResultOut(
        id=r.id,
        scholarship_name=r.scholarship_name,
        provider=r.provider,
        eligibility=r.eligibility or [],
        required_documents=r.required_documents or [],
        application_deadline=r.application_deadline,
        application_steps=r.application_steps or [],
        retrieved_at=r.retrieved_at,
        verification_status=r.verification_status.value,
        confidence_notes=r.confidence_notes,
        sources=[
            SourceOut(
                id=s.id,
                url=s.url,
                title=s.title,
                publisher=s.publisher,
                retrieved_at=s.retrieved_at,
                reachable=s.reachable,
                is_official=s.is_official,
                snippet=s.snippet,
            )
            for s in r.sources
        ],
    )


def _translation(t: TranslationResult) -> TranslationOut:
    return TranslationOut(
        id=t.id,
        language=t.language,  # type: ignore[arg-type]
        simplified_text=t.simplified_text,
        original_snippets=t.original_snippets or [],
        source_ids=t.source_ids or [],
        created_at=t.created_at,
    )


def _guidance(c: GuidanceChecklist) -> GuidanceOut:
    return GuidanceOut(
        id=c.id,
        items=[ChecklistItem(**item) for item in (c.items or [])],
        missing_information=c.missing_information or [],
        unanswered_questions=c.unanswered_questions or [],
        eligibility_assessment=c.eligibility_assessment,
        uncertainty_warnings=c.uncertainty_warnings or [],
        created_at=c.created_at,
    )


def _exec(r: AgentExecution) -> AgentExecutionOut:
    return AgentExecutionOut(
        id=r.id,
        agent=r.agent.value,
        status=r.status.value,
        started_at=r.started_at,
        finished_at=r.finished_at,
        input_summary=r.input_summary,
        output_summary=r.output_summary,
        messages_exchanged=r.messages_exchanged,
        error_message=r.error_message,
        details=r.details or {},
    )
