"""SQLAlchemy ORM models for AccessBridge AI.

The schema records every step of the human + multi-agent workflow so that the
dashboard, agent workspace and human-review workspace all read from real data.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class UserRole(str, enum.Enum):
    student = "student"
    coordinator = "coordinator"
    admin = "admin"


class QuestionStatus(str, enum.Enum):
    received = "received"
    researching = "researching"
    translating = "translating"
    guiding = "guiding"
    awaiting_review = "awaiting_review"
    approved = "approved"
    rejected = "rejected"
    delivered = "delivered"
    failed = "failed"


class AgentName(str, enum.Enum):
    research = "research"
    language = "language"
    guidance = "guidance"


class AgentExecutionStatus(str, enum.Enum):
    started = "started"
    success = "success"
    error = "error"
    skipped = "skipped"


class VerificationStatus(str, enum.Enum):
    verified = "verified"
    partial = "partial"
    unverified = "unverified"
    unreachable = "unverified"  # alias used when source could not be fetched


class ReviewAction(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    corrections_requested = "corrections_requested"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    external_id = Column(String, index=True)          # mattermost/discord user id
    display_name = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.student, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    questions = relationship("Question", back_populates="user", cascade="all, delete-orphan")
    approvals = relationship("HumanApproval", back_populates="reviewer")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    external_user = Column(String)                     # display name if no user row
    platform = Column(String, default="web")           # web | mattermost | discord
    channel = Column(String, default="student-questions")
    thread_id = Column(String, nullable=True)          # for chat platform reply threading

    question_text = Column(Text, nullable=False)
    category = Column(String, default="scholarship")
    language = Column(String, default="en")             # en | hi | pa
    status = Column(SAEnum(QuestionStatus), default=QuestionStatus.received, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="questions")
    research_result = relationship("ResearchResult", uselist=False, back_populates="question")
    translation = relationship("TranslationResult", uselist=False, back_populates="question")
    checklist = relationship("GuidanceChecklist", uselist=False, back_populates="question")
    approvals = relationship("HumanApproval", back_populates="question")
    agent_executions = relationship("AgentExecution", back_populates="question", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="question", cascade="all, delete-orphan")


class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)

    scholarship_name = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    eligibility = Column(JSON, default=list)            # list of strings
    required_documents = Column(JSON, default=list)
    application_deadline = Column(String, nullable=True)
    application_steps = Column(JSON, default=list)
    retrieved_at = Column(DateTime, default=_utcnow, nullable=False)
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.partial, nullable=False)
    confidence_notes = Column(Text, nullable=True)
    raw_summary = Column(Text, nullable=True)

    question = relationship("Question", back_populates="research_result")
    sources = relationship("Source", back_populates="research_result", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=_uuid)
    research_result_id = Column(String, ForeignKey("research_results.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    publisher = Column(String, nullable=True)          # official site name
    retrieved_at = Column(DateTime, default=_utcnow, nullable=False)
    reachable = Column(Boolean, default=True, nullable=False)
    snippet = Column(Text, nullable=True)              # short extracted quote
    is_official = Column(Boolean, default=True, nullable=False)

    research_result = relationship("ResearchResult", back_populates="sources")


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    agent = Column(SAEnum(AgentName), nullable=False)
    status = Column(SAEnum(AgentExecutionStatus), default=AgentExecutionStatus.started, nullable=False)
    started_at = Column(DateTime, default=_utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    messages_exchanged = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, default=dict)               # structured trace for the workspace UI

    question = relationship("Question", back_populates="agent_executions")


class TranslationResult(Base):
    __tablename__ = "translation_results"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    language = Column(String, nullable=False)
    simplified_text = Column(Text, nullable=False)
    original_snippets = Column(JSON, default=list)     # preserved official wording
    source_ids = Column(JSON, default=list)            # references to Source rows
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    question = relationship("Question", back_populates="translation")


class GuidanceChecklist(Base):
    __tablename__ = "guidance_checklists"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    items = Column(JSON, default=list)                 # [{title, detail, status, source_id?}]
    missing_information = Column(JSON, default=list)   # what the student still needs to provide
    unanswered_questions = Column(JSON, default=list)
    eligibility_assessment = Column(Text, nullable=True)
    uncertainty_warnings = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    question = relationship("Question", back_populates="checklist")


class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewer_name = Column(String, nullable=False)
    action = Column(SAEnum(ReviewAction), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    question = relationship("Question", back_populates="approvals")
    reviewer = relationship("User", back_populates="approvals")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=True, index=True)
    actor = Column(String, nullable=False)             # "research_agent" | "coordinator:alice" | "switch_bridge"
    event = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    question = relationship("Question", back_populates="audit_events")


class ProcessedEvent(Base):
    """Idempotency table: records every inbound event ID we have already
    processed, so duplicate webhook deliveries (Switch retries, Mattermost
    retries) are detected and rejected rather than creating duplicate
    questions.

    The `event_key` is a composite of platform + platform's message/event ID
    (or a hash of the payload when no ID is available). The `expires_at` field
    allows old entries to be pruned (default 7 days).
    """
    __tablename__ = "processed_events"

    id = Column(String, primary_key=True, default=_uuid)
    event_key = Column(String, unique=True, index=True, nullable=False)
    platform = Column(String, nullable=False)           # switch | mattermost | discord | slack | telegram | teams
    event_id = Column(String, nullable=True)            # platform's native message/event ID if available
    question_id = Column(String, ForeignKey("questions.id"), nullable=True)
    processed_at = Column(DateTime, default=_utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    payload_hash = Column(String, nullable=True)        # SHA-256 of the payload for dedup
