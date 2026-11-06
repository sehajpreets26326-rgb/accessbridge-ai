"""Pytest configuration for AccessBridge AI.

Uses a temporary SQLite file for test isolation. Set before any backend
import so the engine binds to the test database.

CRITICAL FOR SPEED: the retriever is patched to skip all HTTP calls and use
the bundled official excerpts directly. This makes each full workflow run
in <0.1s instead of ~6s (network timeouts), so the entire suite completes
in seconds, not minutes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force a temp SQLite database for the test session, BEFORE any backend import.
_TEST_DB = Path("/tmp/accessbridge-test.db")
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ.setdefault("ACCESSBRIDGE_DATABASE_URL", f"sqlite:///{_TEST_DB}")
# Deterministic mode (no LLM calls) for reproducible tests.
os.environ.setdefault("ACCESSBRIDGE_LLM_API_KEY", "")
os.environ.setdefault("ACCESSBRIDGE_SWITCH_TRUST_API_KEY", "")
os.environ.setdefault("ACCESSBRIDGE_KNOWLEDGE_OFFLINE_FALLBACK", "true")
os.environ.setdefault("ACCESSBRIDGE_KNOWLEDGE_REQUEST_TIMEOUT_SECONDS", "0.1")


@pytest.fixture(autouse=True, scope="session")
def _fast_retriever():
    """Patch the retriever to skip HTTP entirely and use bundled excerpts.

    This is the single most impactful test-performance fix: without it, each
    workflow run tries to fetch 3 URLs with a network timeout, taking ~6s
    per question. With this patch, sources are loaded from the bundled
    knowledge_base/data/*.txt files instantly.
    """
    from knowledge_base import retriever as _ret
    from knowledge_base.sources import match as _match

    _real_fetch = _ret._fetch_one

    def _fast_fetch(src, *, timeout_seconds, user_agent, offline_fallback):
        """Return a RetrievedSource with the bundled excerpt, no HTTP call."""
        now = datetime.now(timezone.utc)
        bundled = _ret._bundled_excerpt(src)
        raw = bundled or ""
        snippet = raw[:300] if raw else None
        return _ret.RetrievedSource(
            url=src.url,
            title=src.name,
            publisher=src.publisher,
            retrieved_at=now,
            reachable=False,  # honest: we did not fetch it live
            is_official=src.official,
            snippet=snippet,
            raw_text=raw,
        )

    _ret._fetch_one = _fast_fetch
    yield
    _ret._fetch_one = _real_fetch


@pytest.fixture(scope="session")
def db_session():
    """Yield a single SQLAlchemy session for the test session."""
    from backend.app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
