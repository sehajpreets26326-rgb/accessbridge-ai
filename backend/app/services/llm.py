"""LLM client factory.

Every chat completion in AccessBridge goes through this module so that the
Switch Trust guardrails wrapper is applied consistently. When Switch Trust is
not configured (local development), the wrapper runs in pass-through mode and
emits a warning — the project still works, but production deployments should
set SWITCH_TRUST_API_KEY.
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from ..config import settings

log = logging.getLogger("accessbridge.llm")


def build_llm_client() -> OpenAI:
    """Return an OpenAI-compatible client, optionally wrapped by Switch Trust.

    This is the genuine, code-level Switch integration: `switch_trust.wrap`
    routes every chat.completions.create call through the Switch Trust
    guardrails gateway when configured.
    """
    base = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.effective_llm_api_key() or "missing-key",
        timeout=settings.llm_timeout_seconds,
    )

    if not settings.switch_trust_enabled:
        log.warning("Switch Trust guardrails DISABLED by config (switch_trust_enabled=false).")
        return base

    try:
        import switch_trust
    except ImportError:  # pragma: no cover - dependency is pinned in requirements
        log.error("switch_trust SDK not installed; LLM calls will be unguarded.")
        return base

    if not settings.switch_guardrails_configured():
        log.warning(
            "Switch Trust guardrails not configured (SWITCH_TRUST_API_KEY missing). "
            "Running in pass-through mode. Set the key for production."
        )
        # Pass None for both so the SDK runs in pass-through (warn) mode.
        wrapped = switch_trust.wrap(
            base,
            gateway_url=None,
            api_key=None,
            policy_id=None,
            require_guardrails=settings.switch_trust_require_guardrails,
            dangerously_disable_guardrails=False,
            allow_insecure_gateway=settings.switch_trust_allow_insecure_gateway,
        )
        log.info("LLM client wrapped with Switch Trust (pass-through mode).")
        return wrapped

    wrapped = switch_trust.wrap(
        base,
        gateway_url=settings.switch_trust_gateway_url,
        api_key=settings.switch_trust_api_key,
        policy_id=settings.switch_trust_policy_id or None,
        require_guardrails=settings.switch_trust_require_guardrails,
        dangerously_disable_guardrails=False,
        allow_insecure_gateway=settings.switch_trust_allow_insecure_gateway,
    )
    log.info("LLM client wrapped with Switch Trust guardrails (configured).")
    return wrapped


def chat_json(client: OpenAI, system: str, user: str, *, max_tokens: int | None = None) -> str:
    """Single-turn chat completion. Returns the assistant text.

    Used by the three agents. JSON-shaped prompts are enforced by the caller;
    we do not silently retry on parse errors — the orchestrator records them.
    """
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens or settings.llm_max_tokens,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def switch_trust_status() -> dict[str, Any]:
    """Report Switch Trust guardrails status for the dashboard."""
    if not settings.switch_trust_enabled:
        return {"enabled": False, "configured": False, "reason": "disabled_by_config"}

    try:
        import switch_trust
        from importlib.metadata import version as _pkg_version
        try:
            sdk_version = _pkg_version("switch-trust-sdk-py")
        except Exception:
            sdk_version = "unknown"
        status = switch_trust.status()
        return {
            "enabled": True,
            "configured": settings.switch_guardrails_configured(),
            "gateway_url": settings.switch_trust_gateway_url,
            "policy_id": settings.switch_trust_policy_id or None,
            "status": str(status) if status is not None else "uninitialised",
            "sdk_version": sdk_version,
        }
    except ImportError:
        return {"enabled": True, "configured": False, "reason": "sdk_not_installed"}
