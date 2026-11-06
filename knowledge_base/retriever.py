"""Retrieval-Augmented Generation layer for the Research Agent.

The retriever:
1. Matches the student question against the curated official sources.
2. Fetches the official page (HTTP) with a short timeout and a real User-Agent.
3. Extracts clean text via BeautifulSoup.
4. Returns one Source per fetched URL with: url, title, publisher,
   retrieved_at (UTC), reachable, snippet, is_official.

If the network is unreachable or a page is offline, the source is still
recorded with `reachable=False` so the UI can show the failure transparently
and the Guidance Agent can raise an uncertainty warning. We never invent a
source URL.

A small offline fallback uses bundled text excerpts (knowledge_base/data) so
the workflow is demonstrable end-to-end in a sandbox without internet, while
still citing the real official URL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .sources import OfficialSource, match as match_sources


log = logging.getLogger("accessbridge.retriever")


@dataclass
class RetrievedSource:
    url: str
    title: str | None
    publisher: str | None
    retrieved_at: datetime
    reachable: bool
    is_official: bool
    snippet: str | None
    raw_text: str | None = None  # full extracted text, used by the Research Agent


DATA_DIR = Path(__file__).resolve().parent / "data"

DEFAULT_TIMEOUT = 12.0
DEFAULT_USER_AGENT = "AccessBridgeAI/0.1 (+https://github.com/accessbridge-ai)"
DEFAULT_OFFLINE_FALLBACK = True


def retrieve(
    query: str,
    *,
    max_sources: int = 3,
    timeout_seconds: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    offline_fallback: bool = DEFAULT_OFFLINE_FALLBACK,
) -> list[RetrievedSource]:
    """Match + fetch official sources for a student question."""
    matches = match_sources(query)[:max_sources]
    if not matches:
        return []
    return [
        _fetch_one(
            src,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            offline_fallback=offline_fallback,
        )
        for src in matches
    ]


def _fetch_one(
    src: OfficialSource,
    *,
    timeout_seconds: float,
    user_agent: str,
    offline_fallback: bool,
) -> RetrievedSource:
    now = datetime.now(timezone.utc)
    snippet: str | None = None
    raw: str | None = None
    reachable = False
    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = client.get(src.url)
            if resp.status_code < 400:
                reachable = True
                raw, snippet = _extract(resp.text, src)
    except Exception as exc:  # network errors, timeouts, SSL, etc.
        log.warning("Fetch failed for %s: %s", src.url, exc)

    if not reachable and offline_fallback:
        bundled = _bundled_excerpt(src)
        if bundled:
            raw, snippet = bundled, bundled[:300]
            # Reachable stays False — we are honest that this came from a
            # cached bundled excerpt, not a live fetch. The UI shows this.
            log.info("Using bundled offline excerpt for %s", src.key)

    return RetrievedSource(
        url=src.url,
        title=src.name,
        publisher=src.publisher,
        retrieved_at=now,
        reachable=reachable,
        is_official=src.official,
        snippet=snippet,
        raw_text=raw,
    )


def _extract(html: str, src: OfficialSource) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = " ".join(text.split())
    snippet = text[:400]
    return text, snippet


def _bundled_excerpt(src: OfficialSource) -> str | None:
    """Load a curated offline excerpt so the demo works without internet."""
    path = DATA_DIR / f"{src.key}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
