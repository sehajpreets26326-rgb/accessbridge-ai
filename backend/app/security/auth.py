"""Lightweight security helpers.

- Rate limiting (in-process token bucket per remote address).
- Optional shared-secret check for the human-review approval endpoint.
- Safe filename handling for optional uploads.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from pathlib import Path

from ..config import settings


class RateLimiter:
    """In-process per-key token bucket. Sufficient for the MVP."""

    def __init__(self, per_minute: int) -> None:
        self.capacity = per_minute
        self.tokens: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        window = 60.0
        bucket = [t for t in self.tokens[key] if now - t < window]
        if len(bucket) >= self.capacity:
            self.tokens[key] = bucket
            return False
        bucket.append(now)
        self.tokens[key] = bucket
        return True


rate_limiter = RateLimiter(settings.rate_limit_per_minute)


def verify_review_secret(provided: str | None) -> bool:
    """If REVIEW_APPROVAL_SECRET is set, the caller must supply it."""
    expected = settings.review_approval_secret
    if not expected:
        return True
    return bool(provided) and _constant_time_eq(provided, expected)


def _constant_time_eq(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def safe_upload_path(filename: str, upload_dir: Path) -> Path:
    """Strip dangerous path components and return a safe absolute path."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    base = os.path.basename(filename) or "upload.bin"
    safe = "".join(c if c.isalnum() or c in (".", "-", "_") else "_" for c in base)
    return upload_dir / safe
