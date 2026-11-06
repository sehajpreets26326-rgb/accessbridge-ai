"""Unit tests for security helpers and Pydantic schema validation.

Covers:
- RateLimiter token bucket behaviour
- verify_review_secret (unset → allow; set → constant-time compare)
- safe_upload_path strips dangerous components
- Pydantic schema validation for QuestionCreate, SwitchBridgeEvent, ReviewCreate
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from pydantic import ValidationError


# --- RateLimiter ----------------------------------------------------------

def test_rate_limiter_allows_under_capacity():
    from backend.app.security.auth import RateLimiter
    rl = RateLimiter(per_minute=5)
    for _ in range(5):
        assert rl.allow("1.2.3.4") is True


def test_rate_limiter_blocks_over_capacity():
    from backend.app.security.auth import RateLimiter
    rl = RateLimiter(per_minute=3)
    assert rl.allow("k") is True
    assert rl.allow("k") is True
    assert rl.allow("k") is True
    # 4th request in the same window is blocked.
    assert rl.allow("k") is False


def test_rate_limiter_is_per_key():
    """Different keys have independent buckets."""
    from backend.app.security.auth import RateLimiter
    rl = RateLimiter(per_minute=1)
    assert rl.allow("alice") is True
    assert rl.allow("alice") is False  # alice exhausted
    assert rl.allow("bob") is True      # bob still has capacity


def test_rate_limiter_window_expires(monkeypatch):
    """Tokens older than 60 seconds must not count against the limit."""
    from backend.app.security.auth import RateLimiter
    rl = RateLimiter(per_minute=2)

    # Stub time.time() so we can advance the clock.
    t = [1000.0]
    monkeypatch.setattr(time, "time", lambda: t[0])

    assert rl.allow("k") is True
    assert rl.allow("k") is True
    assert rl.allow("k") is False  # exhausted

    # Advance past the 60s window.
    t[0] = 1061.0
    assert rl.allow("k") is True   # window expired, capacity restored


# --- verify_review_secret -------------------------------------------------

def test_review_secret_allows_all_when_unset():
    """When REVIEW_APPROVAL_SECRET is empty, any caller is accepted."""
    from backend.app.config import settings
    from backend.app.security.auth import verify_review_secret
    settings.review_approval_secret = ""
    assert verify_review_secret(None) is True
    assert verify_review_secret("anything") is True


def test_review_secret_enforces_when_set():
    from backend.app.config import settings
    from backend.app.security.auth import verify_review_secret
    settings.review_approval_secret = "my-review-secret"
    try:
        assert verify_review_secret("my-review-secret") is True
        assert verify_review_secret("wrong") is False
        assert verify_review_secret(None) is False
        assert verify_review_secret("") is False
    finally:
        settings.review_approval_secret = ""


def test_review_secret_constant_time_compare():
    """The compare must not short-circuit on length mismatch in a way that
    leaks timing — the helper uses XOR accumulation."""
    from backend.app.security.auth import _constant_time_eq
    assert _constant_time_eq("abc", "abc") is True
    assert _constant_time_eq("abc", "abd") is False
    assert _constant_time_eq("abc", "ab") is False
    assert _constant_time_eq("", "") is True
    assert _constant_time_eq("abc", "ABC") is False  # case-sensitive


# --- safe_upload_path -----------------------------------------------------

def test_safe_upload_path_strips_directory_traversal(tmp_path):
    """A filename with ../ must not escape the upload directory."""
    from backend.app.security.auth import safe_upload_path
    p = safe_upload_path("../../etc/passwd", tmp_path)
    # The result must be inside tmp_path.
    assert str(p).startswith(str(tmp_path))
    # No path separators in the resulting filename.
    assert p.parent == tmp_path


def test_safe_upload_path_replaces_dangerous_chars(tmp_path):
    """Non-alphanumeric chars (except . - _) must be replaced."""
    from backend.app.security.auth import safe_upload_path
    p = safe_upload_path("file with spaces & weird;chars.pdf", tmp_path)
    name = p.name
    for ch in name:
        assert ch.isalnum() or ch in (".", "-", "_")


def test_safe_upload_path_handles_empty_filename(tmp_path):
    """An empty filename falls back to a default."""
    from backend.app.security.auth import safe_upload_path
    p = safe_upload_path("", tmp_path)
    assert p.parent == tmp_path
    assert len(p.name) > 0


def test_safe_upload_path_creates_directory(tmp_path):
    """The upload directory is created if it does not exist."""
    from backend.app.security.auth import safe_upload_path
    new_dir = tmp_path / "new_subdir"
    assert not new_dir.exists()
    p = safe_upload_path("file.pdf", new_dir)
    assert new_dir.exists()
    assert p.parent == new_dir


# --- Schema validation ----------------------------------------------------

def test_question_create_min_length():
    from backend.app.schemas import QuestionCreate
    with pytest.raises(ValidationError):
        QuestionCreate(question_text="short")  # < 8 chars


def test_question_create_max_length():
    from backend.app.schemas import QuestionCreate
    with pytest.raises(ValidationError):
        QuestionCreate(question_text="x" * 2001)  # > 2000


def test_question_create_defaults():
    """Defaults: language=en, category=scholarship, platform=web."""
    from backend.app.schemas import QuestionCreate
    q = QuestionCreate(question_text="A valid question about scholarships")
    assert q.language == "en"
    assert q.category == "scholarship"
    assert q.platform == "web"


def test_question_create_rejects_invalid_language():
    from backend.app.schemas import QuestionCreate
    with pytest.raises(ValidationError):
        QuestionCreate(question_text="A valid question", language="fr")


def test_question_create_rejects_invalid_category():
    from backend.app.schemas import QuestionCreate
    with pytest.raises(ValidationError):
        QuestionCreate(question_text="A valid question", category="taxes")


def test_switch_bridge_event_requires_text():
    from backend.app.schemas import SwitchBridgeEvent
    with pytest.raises(ValidationError):
        SwitchBridgeEvent(room="r", sender="s", text="")


def test_switch_bridge_event_validates_platform():
    from backend.app.schemas import SwitchBridgeEvent
    with pytest.raises(ValidationError):
        SwitchBridgeEvent(room="r", sender="s", text="hi", platform="slack")  # not supported


def test_review_create_validates_action():
    from backend.app.schemas import ReviewCreate
    with pytest.raises(ValidationError):
        ReviewCreate(action="maybe", reviewer_name="x")


def test_review_create_requires_reviewer_name():
    from backend.app.schemas import ReviewCreate
    with pytest.raises(ValidationError):
        ReviewCreate(action="approved", reviewer_name="")


def test_review_create_accepts_all_three_actions():
    from backend.app.schemas import ReviewCreate
    for action in ("approved", "rejected", "corrections_requested"):
        rv = ReviewCreate(action=action, reviewer_name="alice")
        assert rv.action == action
