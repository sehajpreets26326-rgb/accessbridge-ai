"""AccessBridge AI multi-agent package.

Three real Fetch.ai uAgents with separate responsibilities:
- research_agent  -> retrieves official sources, structures eligibility/docs/steps
- language_agent  -> simplifies + translates (en/hi/pa), preserves official wording
- guidance_agent  -> builds the application checklist for human review

The orchestrator composes them. Each agent can also run as an independent
process:  python -m agents.research_agent
"""

from .messages import (  # noqa: F401
    ChecklistItem,
    GuidanceRequest,
    GuidanceResponse,
    LanguageRequest,
    LanguageResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchSource,
)

__all__ = [
    "ChecklistItem",
    "GuidanceRequest",
    "GuidanceResponse",
    "LanguageRequest",
    "LanguageResponse",
    "ResearchRequest",
    "ResearchResponse",
    "ResearchSource",
]
