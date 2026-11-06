"""Structured Pydantic message models exchanged between the three uAgents.

These are the genuine inter-agent protocol: each agent's `on_message` handler
accepts exactly one of these models and replies with another. The orchestrator
also uses them when running the agents in embedded mode.

These models extend `uagents.Model` (which is itself a Pydantic BaseModel) so
they can be sent over the Fetch.ai uAgents protocol directly. The pure-logic
agent functions accept and return the same classes.

Every request carries a `correlation_id` (ties all messages in one workflow
together) and a `task_id` (the specific step). Responses echo them back so an
orchestrator can correlate async replies. `retry_count` and `timeout_at`
support bounded feedback loops and retries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from uagents import Model


def _new_id() -> str:
    return uuid.uuid4().hex


# --- Research Agent messages ----------------------------------------------

class ResearchRequest(Model):
    """Sent to the Research Agent by the orchestrator."""

    question_id: str
    question_text: str
    category: str = "scholarship"
    correlation_id: str = ""          # ties all messages in one workflow together
    task_id: str = ""                  # specific step within the workflow
    retry_count: int = 0               # 0 for first attempt; >0 for retries
    requested_by: str = "orchestrator"  # who asked for this research


class ResearchSource(Model):
    url: str
    title: str | None = None
    publisher: str | None = None
    retrieved_at: datetime
    reachable: bool
    is_official: bool
    snippet: str | None = None


class ClaimEvidence(Model):
    """A single eligibility claim linked to its supporting source evidence.

    This is the core of AccessBridge's trust contract: every important claim
    (eligibility condition, deadline, income limit, document requirement)
    carries the source URL, the exact excerpt that supports it, the retrieval
    timestamp, and a confidence classification.
    """
    claim: str                              # the factual statement, e.g. "Family income limit: Rs. 8 lakh per annum"
    claim_type: Literal["eligibility", "deadline", "document", "amount", "step", "other"] = "other"
    source_url: str
    source_title: str | None = None
    excerpt: str                            # the exact official wording that supports this claim
    retrieved_at: datetime
    confidence: Literal["confirmed", "uncertain", "unavailable"] = "confirmed"
    notes: str | None = None


class ResearchResponse(Model):
    question_id: str
    scholarship_name: str | None = None
    provider: str | None = None
    eligibility: list[str] = []
    required_documents: list[str] = []
    application_deadline: str | None = None
    application_steps: list[str] = []
    sources: list[ResearchSource] = []
    evidence: list[ClaimEvidence] = []      # per-claim evidence references
    retrieved_at: datetime
    verification_status: Literal["verified", "partial", "unverified"] = "partial"
    confidence_notes: str | None = None
    conflicting_claims: list[str] = []      # claims where sources disagree
    duplicate_sources: list[str] = []       # URLs that appeared more than once
    correlation_id: str = ""               # echoed from the request
    task_id: str = ""
    error: str | None = None


# --- Language Agent messages ----------------------------------------------

class LanguageRequest(Model):
    question_id: str
    target_language: Literal["en", "hi", "pa"]
    research: ResearchResponse
    correlation_id: str = ""
    task_id: str = ""
    retry_count: int = 0


class LanguageResponse(Model):
    question_id: str
    language: Literal["en", "hi", "pa"]
    simplified_text: str
    original_snippets: list[str] = []
    source_ids: list[str] = []
    preserved_deadline: str | None = None
    preserved_eligibility: list[str] = []
    correlation_id: str = ""
    task_id: str = ""
    notes: str | None = None
    error: str | None = None


# --- Guidance Agent messages ----------------------------------------------

class GuidanceRequest(Model):
    question_id: str
    question_text: str
    research: ResearchResponse
    translation: LanguageResponse
    student_profile: dict = {}
    correlation_id: str = ""
    task_id: str = ""
    retry_count: int = 0


class ChecklistItem(Model):
    title: str
    detail: str
    status: Literal["todo", "ready", "missing", "uncertain"] = "todo"
    source_url: str | None = None


class GuidanceResponse(Model):
    question_id: str
    checklist: list[ChecklistItem] = []
    missing_information: list[str] = []
    unanswered_questions: list[str] = []
    eligibility_assessment: str | None = None
    uncertainty_warnings: list[str] = []
    correlation_id: str = ""
    task_id: str = ""
    summary: str | None = None
    error: str | None = None
