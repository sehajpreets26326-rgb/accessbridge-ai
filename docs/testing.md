# Testing — AccessBridge AI

## Strategy

Three layers: unit, integration, end-to-end. All tests run in <10s because
`tests/conftest.py` patches the retriever to skip HTTP and use bundled
official excerpts directly.

## Running

```bash
python -m pytest -q                    # all tests
python -m pytest tests/unit -q         # unit only
python -m pytest tests/integration -q  # integration only
python -m pytest -k evidence           # filter by keyword
```

## Test breakdown (132 tests)

### Unit tests
- `test_agents.py` — 5 tests (research, language, guidance pure logic)
- `test_evidence.py` — 7 tests (per-claim evidence, conflicts, duplicates)
- `test_knowledge_base.py` — 9 tests (source matching, retrieval, freshness)
- `test_security_and_schemas.py` — 17 tests (rate limiter, review secret, upload safety, Pydantic validation)
- `test_switch_bridge.py` — 14 tests (bridge endpoints, event handler, language/category detection, token verification)
- `test_api_routes.py` — 14 tests (questions CRUD, dashboard, agents workspace, review, deliver)
- `test_teammate_and_new_routes.py` — 14 tests (teammate persona, evidence endpoint, re-run, evaluation, ASI-1)
- `test_multiplatform_and_idempotency.py` — 14 tests (Discord/Slack/Telegram adapters, duplicate event detection, correlation IDs)

### Integration tests
- `test_workflow.py` — 2 tests (full workflow reaches awaiting_review, failure handling)
- `test_review_flow.py` — 9 tests (approve, reject, corrections, audit trail, failed workflow)
- `test_evaluation.py` — 2 tests (5 reproducible evaluation cases, dataset stability)
- `test_failure_scenarios.py` — 7 tests (duplicate webhook, invalid event, conflicting sources, agent timeout, LLM fallback, unreachable source, human rejection)

## What we test

- Each independent agent's pure logic.
- Agent-to-agent message passing (correlation IDs echoed).
- RAG retrieval + source matching (including bilingual Hindi/Punjabi).
- Evidence attribution (every claim has a source).
- Conflict and duplicate detection.
- Translation preservation (deadlines, eligibility, original snippets).
- Switch bridge token verification + idempotency.
- Mattermost webhook (form + JSON).
- Multi-platform adapter status + routing.
- Human approval / rejection / corrections.
- Failure handling (agent crash, LLM failure, unreachable source, duplicate event, invalid payload).

## What we do NOT do

- Never delete tests to make the suite pass.
- Never weaken assertions.
- Never fabricate benchmark results.
- Never make real network calls in tests (the conftest patches the retriever).
