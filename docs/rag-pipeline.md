# RAG Pipeline — AccessBridge AI

## Overview

The Research Agent uses Retrieval-Augmented Generation over a curated
knowledge base of official scholarship sources. The pipeline:

1. **Source ingestion** — `knowledge_base/sources.py` defines 10 official
   scholarship sources (AICTE Pragati, Saksham, NSP, UGC ISIR, Post-Matric
   SC/OBC, Swami Vivekananda, Chevening, Commonwealth, Fulbright).
2. **Matching** — the student question is matched against source tags using
   Unicode-aware word-boundary matching (handles English, Devanagari, Gurmukhi).
3. **Retrieval** — `knowledge_base/retriever.py` fetches the official page via
   httpx with a short timeout, extracts text via BeautifulSoup, and records
   `reachable` + `retrieved_at`.
4. **Offline fallback** — when the network is unreachable, a bundled official
   excerpt is used. `reachable=False` is recorded honestly.
5. **Extraction** — the Research Agent (via LLM or deterministic fallback)
   extracts structured fields: scholarship_name, eligibility, documents,
   deadline, steps.
6. **Evidence attribution** — `_build_evidence()` links every extracted claim
   to its source URL + excerpt + timestamp + confidence.
7. **Conflict detection** — `_detect_conflicts()` flags when sources disagree
   on key values (e.g. different income limits).
8. **Duplicate detection** — `_detect_duplicate_sources()` flags URLs that
   appear more than once.
9. **Freshness monitoring** — `freshness_days` is computed from `retrieved_at`
   and exposed via `GET /api/questions/{id}/evidence`.

## Trust contract

Every important eligibility claim is traceable to:
- Official source URL
- Source title
- Supporting passage (excerpt)
- Retrieval timestamp
- Availability status (`reachable` boolean)
- Verification state (`confirmed` / `uncertain` / `unavailable`)

## What we never do

- Never invent a scholarship name, deadline, amount, or eligibility condition.
- Never claim a live fetch when the source came from a bundled excerpt.
- Never fabricate confidence scores — `unavailable` means no source was found.
