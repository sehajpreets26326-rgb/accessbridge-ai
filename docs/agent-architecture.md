# Agent Architecture — AccessBridge AI

Three independent Fetch.ai uAgents, each with a single responsibility,
communicating through structured Pydantic messages.

## The three agents

| Agent | Port | Responsibility | Input | Output |
|---|---|---|---|---|
| **Research** | 8001 | Retrieve official sources, extract eligibility/docs/deadlines, build evidence refs | `ResearchRequest` | `ResearchResponse` |
| **Language** | 8002 | Simplify official wording, translate to en/hi/pa, preserve original snippets | `LanguageRequest` | `LanguageResponse` |
| **Guidance** | 8003 | Build personalised checklist, flag missing info, route to human review | `GuidanceRequest` | `GuidanceResponse` |

## What makes them genuinely independent

Each agent module defines its own `uagents.Agent` instance with its own
`name`, `seed`, `port`, and `endpoint`. Each has its own `@agent.on_message`
handler that calls a pure-logic function and replies via `ctx.send`. They can
each run as a separate process:

```bash
python -m agents.research_agent     # port 8001
python -m agents.language_agent     # port 8002
python -m agents.guidance_agent     # port 8003
```

This is not three labels inside one LLM call. It is three real uAgents.

## Message protocol

Every request carries:
- `question_id` — the workflow's root identifier
- `correlation_id` — ties all messages in one workflow together (echoed in responses)
- `task_id` — the specific step within the workflow
- `retry_count` — 0 for first attempt; >0 for retries

Every response echoes the `correlation_id` and `task_id` back so the
orchestrator can correlate async replies.

See `agents/messages.py` for the full protocol definition.

## Execution modes

- **Embedded** (default): the orchestrator calls `research()`, `translate()`,
  `guide()` directly. Deterministic, reliable, used by the demo and tests.
- **Distributed** (optional): each agent runs as its own process; the
  orchestrator's `dispatch_distributed()` sends real uAgents messages to
  their Fetch.ai addresses.

## Bounded feedback loops

The Guidance Agent can flag missing information. A coordinator can then call
`POST /api/questions/{id}/rerun-research` to request another research pass.
The `retry_count` field on the request tracks how many times an agent has
been asked to retry. The orchestrator caps retries (default: 3) to prevent
infinite loops.

## Evidence traceability

The Research Agent produces a `ClaimEvidence` ref for every eligibility
condition, document, deadline and step. Each ref carries:
- `claim` — the factual statement
- `claim_type` — eligibility / deadline / document / amount / step / other
- `source_url` — the official URL
- `excerpt` — the exact official wording
- `retrieved_at` — timestamp
- `confidence` — confirmed / uncertain / unavailable

See `docs/rag-pipeline.md` for the retrieval pipeline.
