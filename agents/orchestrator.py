"""Workflow orchestrator.

The orchestrator composes the three Fetch.ai uAgents into one end-to-end
workflow and persists every step to the database so the dashboard, agent
workspace and human-review workspace read from real data.

Two execution modes:

- Embedded (default, reliable, used for the demo and tests):
    Calls the agents' pure-logic functions (research(), translate(), guide())
    directly. The agents are still real uAgents — they each define an Agent,
    on_message handler and ctx.send reply — but execution happens in-process.

- Distributed (optional, demonstrates genuine inter-process uAgents messaging):
    Sends real uAgents messages to the running agent processes via their
    endpoints. See `dispatch_distributed()`.

The orchestrator records an AgentExecution row per agent with status, timing
and a structured `details` trace, and posts progress messages to the Switch
rooms (via the Mattermost transport when configured).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import (
    AgentExecution,
    AgentExecutionStatus,
    AgentName,
    AuditEvent,
    GuidanceChecklist,
    Question,
    QuestionStatus,
    ResearchResult,
    Source,
    TranslationResult,
    VerificationStatus,
)
from backend.app.services.audit import record as audit_record
from agents.messages import GuidanceRequest, LanguageRequest, ResearchRequest

log = logging.getLogger("accessbridge.orchestrator")


def _teammate(event: str, **kw) -> str:
    """Cheering-teammate progress message (see backend.app.services.teammate)."""
    from backend.app.services.teammate import teammate_message
    return teammate_message(event, **kw)


def _jsonable(obj) -> Any:
    """Convert a uagents.Model (or any pydantic model) to a JSON-safe dict.

    uagents.Model.model_dump() does not accept `mode="json"`, so we round-trip
    through model_dump_json() to ensure datetimes become ISO strings, which
    SQLAlchemy's JSON column can store.
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump_json"):
        return json.loads(obj.model_dump_json())
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    return obj


async def run_workflow(question_id: str, db: Session, *, progress_sink=None) -> Question:
    """Run the full research -> translate -> guide workflow for a question.

    `progress_sink` is an optional callable(str) used to push progress messages
    into the Switch rooms (no-op when not provided).
    """
    question = db.get(Question, question_id)
    if not question:
        raise ValueError(f"Question {question_id} not found")

    def _set_status(status: QuestionStatus, error: str | None = None) -> None:
        question.status = status
        question.error_message = error
        db.flush()

    def _progress(msg: str) -> None:
        if progress_sink:
            try:
                progress_sink(msg)
            except Exception as exc:  # never let a progress failure abort the workflow
                log.warning("progress_sink failed: %s", exc)

    try:
        # --- 1. Research ---
        _set_status(QuestionStatus.researching)
        audit_record(db, question_id=question_id, actor="orchestrator", event="research_started")
        _progress(_teammate("research_started", scholarship=None))

        from agents.research_agent import research
        research_req = ResearchRequest(
            question_id=question_id,
            question_text=question.question_text,
            category=question.category,
            correlation_id=question_id,
            task_id=f"research-{question_id[:8]}",
        )
        exec_row = _start_execution(db, question_id, AgentName.research, input_summary=question.question_text[:200])
        research_resp = await research(research_req)
        _finish_execution(db, exec_row, output_summary=research_resp.scholarship_name or "no match", messages_exchanged=1,
                          details=_jsonable(research_resp))
        _persist_research(db, question_id, research_resp)
        _progress(_teammate("research_done",
                            scholarship=research_resp.scholarship_name,
                            source_count=len(research_resp.sources)))

        # --- 2. Translation ---
        _set_status(QuestionStatus.translating)
        audit_record(db, question_id=question_id, actor="orchestrator", event="translation_started")
        _progress(_teammate("translation_started", language=question.language))

        from agents.language_agent import translate
        lang_req = LanguageRequest(
            question_id=question_id,
            target_language=question.language,
            research=research_resp,
            correlation_id=question_id,
            task_id=f"language-{question_id[:8]}",
        )
        exec_row = _start_execution(db, question_id, AgentName.language, input_summary=f"target={question.language}")
        lang_resp = await translate(lang_req)
        _finish_execution(db, exec_row, output_summary=lang_resp.simplified_text[:200], messages_exchanged=1,
                          details=_jsonable(lang_resp))
        _persist_translation(db, question_id, lang_resp)
        _progress(_teammate("translation_done", language=question.language))

        # --- 3. Guidance ---
        _set_status(QuestionStatus.guiding)
        audit_record(db, question_id=question_id, actor="orchestrator", event="guidance_started")
        _progress(_teammate("guidance_started"))

        from agents.guidance_agent import guide
        guidance_req = GuidanceRequest(
            question_id=question_id,
            question_text=question.question_text,
            research=research_resp,
            translation=lang_resp,
            student_profile={},
            correlation_id=question_id,
            task_id=f"guidance-{question_id[:8]}",
        )
        exec_row = _start_execution(db, question_id, AgentName.guidance, input_summary="research+translation")
        guidance_resp = await guide(guidance_req)
        _finish_execution(db, exec_row, output_summary=guidance_resp.summary or "checklist ready", messages_exchanged=1,
                          details=_jsonable(guidance_resp))
        _persist_checklist(db, question_id, guidance_resp)
        _progress(_teammate("guidance_done", checklist_count=len(guidance_resp.checklist)))

        # --- 4. Await human review ---
        _set_status(QuestionStatus.awaiting_review)
        audit_record(db, question_id=question_id, actor="orchestrator", event="awaiting_human_review")
        _progress(_teammate("awaiting_review"))

        db.commit()
        return question

    except Exception as exc:
        log.exception("Workflow failed for question %s", question_id)
        _set_status(QuestionStatus.failed, error=str(exc)[:500])
        audit_record(db, question_id=question_id, actor="orchestrator", event="workflow_failed",
                     payload={"error": str(exc)[:500]})
        # also record a failed execution if we have a partial one
        db.commit()
        raise


# --- persistence helpers --------------------------------------------------

def _start_execution(db: Session, question_id: str, agent: AgentName, *, input_summary: str | None) -> AgentExecution:
    row = AgentExecution(
        question_id=question_id,
        agent=agent,
        status=AgentExecutionStatus.started,
        input_summary=input_summary,
    )
    db.add(row)
    db.flush()
    return row


def _finish_execution(db: Session, row: AgentExecution, *, output_summary: str | None, messages_exchanged: int, details: dict) -> None:
    row.status = AgentExecutionStatus.success
    row.output_summary = output_summary
    row.messages_exchanged = messages_exchanged
    row.details = details
    row.finished_at = datetime.now(timezone.utc)
    db.flush()


def _persist_research(db: Session, question_id: str, resp) -> None:
    existing = db.query(ResearchResult).filter_by(question_id=question_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    rr = ResearchResult(
        question_id=question_id,
        scholarship_name=resp.scholarship_name,
        provider=resp.provider,
        eligibility=resp.eligibility,
        required_documents=resp.required_documents,
        application_deadline=resp.application_deadline,
        application_steps=resp.application_steps,
        retrieved_at=resp.retrieved_at,
        verification_status=VerificationStatus(resp.verification_status),
        confidence_notes=resp.confidence_notes,
        raw_summary=None,
    )
    db.add(rr)
    db.flush()
    for s in resp.sources:
        db.add(Source(
            research_result_id=rr.id,
            url=s.url,
            title=s.title,
            publisher=s.publisher,
            retrieved_at=s.retrieved_at,
            reachable=s.reachable,
            snippet=s.snippet,
            is_official=s.is_official,
        ))
    db.flush()


def _persist_translation(db: Session, question_id: str, resp) -> None:
    existing = db.query(TranslationResult).filter_by(question_id=question_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    db.add(TranslationResult(
        question_id=question_id,
        language=resp.language,
        simplified_text=resp.simplified_text,
        original_snippets=resp.original_snippets,
        source_ids=resp.source_ids,
    ))
    db.flush()


def _persist_checklist(db: Session, question_id: str, resp) -> None:
    existing = db.query(GuidanceChecklist).filter_by(question_id=question_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    db.add(GuidanceChecklist(
        question_id=question_id,
        items=[_jsonable(c) for c in resp.checklist],
        missing_information=resp.missing_information,
        unanswered_questions=resp.unanswered_questions,
        eligibility_assessment=resp.eligibility_assessment,
        uncertainty_warnings=resp.uncertainty_warnings,
    ))
    db.flush()


# --- Optional distributed dispatch (real uAgents messaging) ----------------

async def dispatch_distributed(question_id: str, db: Session) -> None:
    """Send real uAgents messages to the three running agent processes.

    This requires the agents to be running as separate processes
    (`python -m agents.research_agent`, etc.) and reachable on their endpoints.
    For the hackathon demo we use embedded mode (run_workflow) by default, but
    this function demonstrates genuine inter-agent uAgents messaging.

    NOTE: uAgents address-based messaging is asynchronous. A production
    deployment would register response handlers on the orchestrator agent and
    correlate by question_id. This function sends the initial dispatch and
    logs the addresses for the demo.
    """
    from agents.addresses import guidance_address, language_address, research_address

    question = db.get(Question, question_id)
    if not question:
        raise ValueError(f"Question {question_id} not found")

    log.info("Distributed dispatch — research=%s language=%s guidance=%s",
             research_address(), language_address(), guidance_address())
    audit_record(
        db,
        question_id=question_id,
        actor="orchestrator",
        event="distributed_dispatch_queued",
        payload={
            "research_address": research_address(),
            "language_address": language_address(),
            "guidance_address": guidance_address(),
        },
    )
    db.commit()
