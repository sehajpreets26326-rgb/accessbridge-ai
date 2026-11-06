"""Application configuration.

All secrets are read from environment variables. Nothing is hardcoded.
A `.env.example` file at the repository root documents every variable.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core runtime ---
    app_name: str = "AccessBridge AI"
    environment: Literal["development", "staging", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Database ---
    # We deliberately do NOT read the bare `DATABASE_URL` env var, because
    # sandboxes often set it to a non-SQLAlchemy value (e.g. `file:...`).
    # Override with `ACCESSBRIDGE_DATABASE_URL` instead.
    database_url: str = Field(
        default=f"sqlite:///{(REPO_ROOT / 'data' / 'accessbridge.db').as_posix()}",
        validation_alias="ACCESSBRIDGE_DATABASE_URL",
    )

    @model_validator(mode="after")
    def _validate_db_url(self):
        if not self.database_url or not self.database_url.startswith(
            ("sqlite://", "postgresql://", "postgresql+psycopg://", "mysql://", "mysql+pymysql://")
        ):
            self.database_url = f"sqlite:///{(REPO_ROOT / 'data' / 'accessbridge.db').as_posix()}"
        return self

    # --- LLM (OpenAI-compatible) ---
    # AccessBridge uses any OpenAI-compatible endpoint. Set llm_provider to one
    # of the presets below, or use "custom" with your own base_url + model.
    #   - "openai"  → https://api.openai.com/v1 (gpt-4o-mini)
    #   - "asi1"    → https://api.asi1.ai/v1 (Fetch.ai ASI-1 Mini — agent-ready)
    #   - "groq"    → https://api.groq.com/openai/v1
    #   - "custom"  → whatever you set in llm_base_url
    llm_provider: Literal["openai", "asi1", "groq", "ollama", "custom"] = "openai"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 45.0
    llm_max_tokens: int = 1200

    # Preset base URLs + default models per provider.
    _LLM_PRESETS: dict = {
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
        "asi1": {"base_url": "https://api.asi1.ai/v1", "model": "asi1-mini"},
        "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
        "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b"},
    }

    @model_validator(mode="after")
    def _apply_llm_preset(self):
        """When llm_provider is a known preset, fill in base_url + model
        unless the user explicitly overrode them."""
        preset = self._LLM_PRESETS.get(self.llm_provider)
        if preset and self.llm_provider != "custom":
            # Only override if the user hasn't set a non-default value.
            if self.llm_base_url == "https://api.openai.com/v1" or self.llm_provider != "openai":
                self.llm_base_url = preset["base_url"]
            if self.llm_model == "gpt-4o-mini" or self.llm_provider != "openai":
                self.llm_model = preset["model"]
        return self

    # --- Switch Trust guardrails ---
    # Switch Trust is the code-level Switch integration: every LLM call from
    # every agent is wrapped with switch_trust.wrap(...). When guardrails are
    # not configured the SDK runs in pass-through mode and warns loudly, so the
    # project still runs locally for development.
    switch_trust_enabled: bool = True
    switch_trust_gateway_url: str = "https://api.switchagents.ai"
    switch_trust_api_key: str = ""
    switch_trust_policy_id: str = ""
    switch_trust_require_guardrails: bool = False  # set True in production
    switch_trust_allow_insecure_gateway: bool = False

    # --- Switch Console / Agent Bridge ---
    # The Switch Console (desktop app) calls our bridge endpoint to dispatch a
    # room message to the AccessBridge orchestrator. This is the token Switch
    # presents when calling our bridge; we verify it on every inbound request.
    switch_bridge_token: str = ""
    switch_bridge_public_url: str = "http://localhost:8000"  # reachable by Switch

    # --- Mattermost (chat platform transport) ---
    mattermost_enabled: bool = False
    mattermost_base_url: str = ""          # e.g. https://mattermost.example.com
    mattermost_bot_token: str = ""          # bot account token (preferred)
    mattermost_incoming_webhook_url: str = ""  # per-channel incoming webhook
    mattermost_channel_student_questions: str = "student-questions"
    mattermost_channel_research_updates: str = "research-updates"
    mattermost_channel_translation: str = "translation"
    mattermost_channel_human_review: str = "human-review"
    mattermost_channel_final_guidance: str = "final-guidance"

    # --- Discord (bot token from https://discord.com/developers/applications) ---
    discord_bot_token: str = ""
    discord_channel_id: str = ""

    # --- Slack (bot token from https://api.slack.com/apps, scope: chat:write) ---
    slack_bot_token: str = ""
    slack_channel: str = ""

    # --- Telegram (bot token from @BotFather, chat_id from /getUpdates) ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Microsoft Teams (incoming webhook URL for outbound) ---
    # Teams inbound requires a hosted Azure Bot Service; we support outbound only.
    teams_incoming_webhook_url: str = ""

    # --- Fetch.ai uAgents ---
    agents_enabled: bool = True
    agents_research_port: int = 8001
    agents_language_port: int = 8002
    agents_guidance_port: int = 8003
    agents_seed: str = "accessbridge-dev-seed-change-me"
    agents_endpoint_base: str = "http://localhost"

    # --- Knowledge retrieval ---
    knowledge_offline_fallback: bool = True
    knowledge_request_timeout_seconds: float = 12.0
    knowledge_user_agent: str = "AccessBridgeAI/0.1 (+https://github.com/accessbridge-ai)"

    # --- Security ---
    review_approval_secret: str = ""  # required to approve/reject final guidance
    rate_limit_per_minute: int = 60
    upload_max_bytes: int = 2 * 1024 * 1024  # 2 MB cap on optional uploads

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or os.environ.get("OPENAI_API_KEY", "")

    def switch_guardrails_configured(self) -> bool:
        return bool(self.switch_trust_api_key and self.switch_trust_gateway_url)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
