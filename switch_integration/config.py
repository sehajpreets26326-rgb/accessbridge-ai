"""Switch integration configuration.

This module documents the integration boundary between AccessBridge and the
Switch platform:

1. Switch Trust guardrails (code-level, always active when configured):
   every LLM call from every agent is wrapped with `switch_trust.wrap(...)`.
   See backend/app/services/llm.py.

2. Switch Console + Agent Bridge (process-level):
   The user installs the Switch Console desktop app, connects their chat
   platform (Mattermost recommended), and creates an agent that points at our
   bridge endpoint. Switch dispatches room messages to our bridge as HTTP
   POSTs; we run the workflow and post progress + final guidance back into
   the rooms.

3. Mattermost transport (message-level):
   When Mattermost is the connected chat platform, our bridge accepts
   Mattermost outgoing webhooks directly (so the project is testable even
   before Switch Console is installed) and posts back via incoming webhooks /
   the Mattermost REST API.

All credentials are read from environment variables via backend.app.config.
"""
from __future__ import annotations

from backend.app.config import settings


BRIDGE_PATH = "/switch/bridge"
MATTERMOST_WEBHOOK_PATH = "/switch/mattermost/webhook"
HEALTH_PATH = "/switch/health"


def bridge_enabled() -> bool:
    """The bridge HTTP endpoint is always enabled; it just records events."""
    return True


def verify_inbound_token(provided: str | None) -> bool:
    """Verify the token Switch (or Mattermost) presents when calling our bridge.

    When `SWITCH_BRIDGE_TOKEN` is unset, we accept any caller — this is fine
    for local development but should be locked down for any public deployment.
    """
    expected = settings.switch_bridge_token
    if not expected:
        return True
    return bool(provided) and provided == expected
