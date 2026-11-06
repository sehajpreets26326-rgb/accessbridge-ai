"""Switch integration package.

The real Switch integration is two-layered:

1. Switch Trust guardrails wrap every LLM call (see backend.app.services.llm).
2. This bridge exposes the HTTP endpoint the Switch Console Agent Bridge (or a
   raw Mattermost outgoing webhook) calls to dispatch a room message into the
   AccessBridge orchestrator.
"""

from .bridge import router as bridge_router
from .config import (
    BRIDGE_PATH,
    HEALTH_PATH,
    MATTERMOST_WEBHOOK_PATH,
    bridge_enabled,
    verify_inbound_token,
)
from .event_handler import from_mattermost_webhook, from_raw, from_switch_event
from .message_sender import post_final_guidance, post_progress, post_to_room

__all__ = [
    "BRIDGE_PATH",
    "HEALTH_PATH",
    "MATTERMOST_WEBHOOK_PATH",
    "bridge_enabled",
    "bridge_router",
    "from_mattermost_webhook",
    "from_raw",
    "from_switch_event",
    "post_final_guidance",
    "post_progress",
    "post_to_room",
    "verify_inbound_token",
]
