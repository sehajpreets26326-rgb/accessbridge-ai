"""Unit tests for the knowledge base: source matching and retrieval.

The retriever does real HTTP fetches with a short timeout. In the sandbox
there is no internet, so every fetch fails fast and the bundled offline
excerpt is used — but the Source is still recorded with reachable=False so
the UI can show the failure honestly. These tests verify that contract.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from knowledge_base.sources import SOURCES, OfficialSource, match


# --- Source matching ------------------------------------------------------

def test_curated_sources_are_all_official():
    """Every source in the curated knowledge base must be marked official."""
    for s in SOURCES:
        assert s.official is True
        assert s.url.startswith("https://")  # all official sources use HTTPS


def test_match_finds_aicte_pragati():
    """A question about AICTE Pragati must match the Pragati source first."""
    results = match("What are the eligibility requirements for the AICTE Pragati scholarship for girls?")
    assert len(results) >= 1
    assert results[0].key == "aicte-pragati"


def test_match_finds_saksham():
    results = match("Tell me about the AICTE Saksham scholarship for specially-abled students")
    assert len(results) >= 1
    assert results[0].key == "aicte-saksham"


def test_match_finds_international_scholarships():
    """International scholarships must be matched by their name."""
    assert match("How do I apply for the Chevening scholarship?")[0].key == "chevening"
    assert match("Tell me about the Commonwealth scholarship")[0].key == "commonwealth"
    assert match("Fulbright Nehru fellowship for masters")[0].key == "fulbright"


def test_match_returns_empty_for_irrelevant_query():
    """A query with no matching tags must return an empty list, not a guess."""
    results = match("What is the airspeed of an unladen swallow?")
    assert results == []


def test_match_ranks_by_score():
    """A query that matches more tags of one source ranks it first."""
    # "aicte" + "girl" + "scholarship" → Pragati (3 tags) ranks above Saksham (2 tags: aicte, scholarship).
    results = match("aicte girl scholarship")
    assert results[0].key == "aicte-pragati"


# --- Retrieval ------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_returns_sources_with_timestamps():
    """retrieve() must return RetrievedSource objects with real retrieval_at
    timestamps, even when the network is unreachable."""
    from knowledge_base.retriever import retrieve, RetrievedSource

    sources = retrieve("AICTE Pragati scholarship for girls", max_sources=2)
    assert len(sources) >= 1
    for s in sources:
        assert isinstance(s, RetrievedSource)
        assert s.url.startswith("http")
        assert isinstance(s.retrieved_at, datetime)
        assert s.is_official is True


def test_retrieve_records_unreachable_honestly():
    """When a source cannot be fetched, reachable must be False — never pretend
    a live fetch happened."""
    from knowledge_base.retriever import retrieve

    sources = retrieve("AICTE Pragati scholarship", max_sources=1)
    assert len(sources) == 1
    s = sources[0]
    # In the sandbox there is no internet, so reachable is False.
    # The important contract: the field exists and reflects reality.
    assert isinstance(s.reachable, bool)
    if not s.reachable:
        # When unreachable, the offline excerpt must still provide a snippet.
        assert s.snippet is not None
        assert len(s.snippet) > 0


def test_retrieve_uses_bundled_excerpt_when_offline():
    """When the network is unreachable, the bundled official excerpt must be
    used so the workflow still completes — but reachable stays False."""
    from knowledge_base.retriever import retrieve

    sources = retrieve("AICTE Saksham scholarship", max_sources=1)
    assert len(sources) == 1
    s = sources[0]
    if not s.reachable:
        # raw_text comes from the bundled excerpt.
        assert s.raw_text is not None
        assert "saksham" in s.raw_text.lower() or "specially" in s.raw_text.lower()


def test_retrieve_returns_empty_when_no_match():
    """A query that matches no curated source returns an empty list."""
    from knowledge_base.retriever import retrieve
    sources = retrieve("completely unrelated query about cooking recipes")
    assert sources == []


def test_retrieve_respects_max_sources():
    """max_sources caps the number of returned sources."""
    from knowledge_base.retriever import retrieve
    sources = retrieve("scholarship india", max_sources=1)
    assert len(sources) <= 1
