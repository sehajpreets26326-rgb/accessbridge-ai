"""Pydantic schemas for the REST API and for inter-service messages.

These are deliberately separate from the SQLAlchemy models so the API contract
is stable even if the database schema evolves.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


Language = Literal["en", "hi", "pa"]
Category = Literal["scholarship", "admission", "scheme", "general"]


# --- Question lifecycle ----------------------------------------------------

class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=8, max_length=2000)
    language: Language = "en"
    category: Category = "scholarship"
    platform: str = "web"
    external_user: Optional[str] = None


class QuestionOut(BaseModel):
    id: str
    question_text: str
    language: Language
    category: Category
    status: str
    platform: str
    channel: str
    external_user: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class QuestionListOut(BaseModel):
    id: str
    question_text: str
    language: Language
    category: Category
    status: str
    created_at: datetime
    external_user: Optional[str] = None


# --- Research --------------------------------------------------------------

class SourceOut(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    retrieved_at: datetime
    reachable: bool
    is_official: bool
    snippet: Optional[str] = None


class ClaimEvidenceOut(BaseModel):
    """A single eligibility claim linked to its supporting source evidence."""
    claim: str
    claim_type: str
    source_url: str
    source_title: Optional[str] = None
    excerpt: str
    retrieved_at: datetime
    confidence: str
    notes: Optional[str] = None
    freshness_days: Optional[float] = None


class ResearchResultOut(BaseModel):
    id: str
    scholarship_name: Optional[str] = None
    provider: Optional[str] = None
    eligibility: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    application_deadline: Optional[str] = None
    application_steps: list[str] = Field(default_factory=list)
    retrieved_at: datetime
    verification_status: str
    confidence_notes: Optional[str] = None
    sources: list[SourceOut] = Field(default_factory=list)
    evidence: list[ClaimEvidenceOut] = Field(default_factory=list)
    conflicting_claims: list[str] = Field(default_factory=list)
    duplicate_sources: list[str] = Field(default_factory=list)


# --- Translation -----------------------------------------------------------

class TranslationOut(BaseModel):
    id: str
    language: Language
    simplified_text: str
    original_snippets: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    created_at: datetime


# --- Guidance --------------------------------------------------------------

class ChecklistItem(BaseModel):
    title: str
    detail: str
    status: Literal["todo", "ready", "missing", "uncertain"] = "todo"
    source_id: Optional[str] = None


class GuidanceOut(BaseModel):
    id: str
    items: list[ChecklistItem]
    missing_information: list[str] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)
    eligibility_assessment: Optional[str] = None
    uncertainty_warnings: list[str] = Field(default_factory=list)
    created_at: datetime


# --- Human review ----------------------------------------------------------

class ReviewCreate(BaseModel):
    action: Literal["approved", "rejected", "corrections_requested"]
    reviewer_name: str = Field(..., min_length=1, max_length=120)
    note: Optional[str] = Field(None, max_length=2000)
    secret: Optional[str] = Field(
        None,
        description="Required when REVIEW_APPROVAL_SECRET is configured in the backend.",
    )


class DeliverCreate(BaseModel):
    """Request body for the deliver endpoint. Requires the review secret."""
    secret: Optional[str] = Field(
        None,
        description="Required when REVIEW_APPROVAL_SECRET is configured in the backend.",
    )


class ReviewOut(BaseModel):
    id: str
    question_id: str
    reviewer_name: str
    action: str
    note: Optional[str] = None
    created_at: datetime


# --- Agent workspace -------------------------------------------------------

class AgentExecutionOut(BaseModel):
    id: str
    agent: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    messages_exchanged: int = 0
    error_message: Optional[str] = None
    details: dict = Field(default_factory=dict)


# --- Switch bridge ---------------------------------------------------------

class SwitchBridgeEvent(BaseModel):
    """Inbound event from the Switch Agent Bridge (or a raw Mattermost webhook).

    Switch Console dispatches a room message to our bridge; the payload shape is
    normalised here so the orchestrator only cares about one schema.
    """

    room: str = Field(..., description="Channel/room name e.g. student-questions")
    platform: Literal["mattermost", "discord", "switch"] = "switch"
    sender: str = Field(..., description="Display name of the human sender")
    sender_id: Optional[str] = None
    text: str = Field(..., min_length=1, max_length=4000)
    language: Language = "en"
    category: Category = "scholarship"
    token: Optional[str] = None
    event_id: Optional[str] = Field(None, description="Platform's native message/event ID for dedup")


class SwitchBridgeAck(BaseModel):
    accepted: bool
    question_id: str
    status: str
    message: str


# --- Dashboard -------------------------------------------------------------

class DashboardOut(BaseModel):
    recent_questions: list[QuestionListOut]
    active_agent_runs: list[AgentExecutionOut]
    pending_reviews: list[QuestionListOut]
    completed_today: int
    verification_summary: dict[str, int]
    switch_status: dict
