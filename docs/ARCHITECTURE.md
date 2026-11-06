# Architecture — AccessBridge AI

## Overview

AccessBridge AI is a multi-agent, human-in-the-loop guidance system. Three
independent Fetch.ai uAgents (Research, Language, Guidance) collaborate via
structured Pydantic messages under a coordinator, with Switch as the
communication substrate and a human coordinator as the final approval gate.

## Component map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Communication layer                          │
│   Mattermost / Discord room  ──►  Switch Console / webhook          │
│                                            │                         │
│                            POST /switch/bridge                        │
│                            POST /switch/mattermost                    │
└────────────────────────────────────────────┬────────────────────────┘
                                             │ token-verified event
┌────────────────────────────────────────────▼────────────────────────┐
│                         AccessBridge FastAPI                         │
│   bridge.py ──► event_handler ──► Question row ──► background task  │
│                                                                      │
│   orchestrator.run_workflow(question_id, db, progress_sink)          │
│      │                                                               │
│      ├──► Research Agent   (port 8001)  ── ResearchRequest/Response   │
│      ├──► Language Agent   (port 8002)  ── LanguageRequest/Response   │
│      └──► Guidance Agent   (port 8003)  ── GuidanceRequest/Response   │
│                                                                      │
│   routes: /api/questions /api/dashboard /api/agents /api/review       │
│   persistence: SQLAlchemy ──► SQLite (10 tables)                      │
│   audit: every transition recorded                                    │
└────────────────────────────────────────────┬────────────────────────┘
                                             │ progress + final guidance
┌────────────────────────────────────────────▼────────────────────────┐
│                  message_sender ──► Mattermost REST                  │
│                  posts into #research-updates, #translation,         │
│                  #human-review, #final-guidance                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data model

Ten SQLAlchemy tables, all timestamped:

| Table | Purpose |
|---|---|
| `users` | Students and coordinators (external_id from chat platform) |
| `questions` | The student's question + status + language + category |
| `research_results` | One per question: scholarship_name, eligibility, docs, deadline, steps, verification_status |
| `sources` | Many per research_result: url, title, publisher, retrieved_at, reachable, snippet, is_official |
| `agent_executions` | One per agent per question: status, started_at, finished_at, messages_exchanged, details (trace) |
| `translation_results` | One per question: language, simplified_text, original_snippets, source_ids |
| `guidance_checklists` | One per question: items, missing_information, unanswered_questions, eligibility_assessment, uncertainty_warnings |
| `human_approvals` | Many per question: reviewer, action (approved/rejected/corrections), note, timestamp |
| `audit_events` | Every workflow transition + review action |

Status state machine for a `Question`:

```
received → researching → translating → guiding → awaiting_review
                                              ↘ approved → delivered
                                              ↘ rejected
                                              ↘ failed (anywhere)
```

## Agent protocol

All three agents share `agents/messages.py`. Every model extends
`uagents.Model`, so the same class travels over the Fetch.ai uAgents
protocol and is used by the orchestrator in embedded mode.

```
ResearchRequest  { question_id, question_text, category }
        │
        ▼
ResearchResponse { scholarship_name, provider, eligibility[], required_documents[],
                   application_deadline, application_steps[], sources[], retrieved_at,
                   verification_status, confidence_notes }
        │
        ▼  (passed inside LanguageRequest.research)
LanguageRequest  { question_id, target_language, research }
        │
        ▼
LanguageResponse { language, simplified_text, original_snippets[], source_ids[],
                   preserved_deadline, preserved_eligibility[] }
        │
        ▼  (passed inside GuidanceRequest.translation)
GuidanceRequest  { question_id, question_text, research, translation, student_profile }
        │
        ▼
GuidanceResponse { checklist[ChecklistItem], missing_information[], unanswered_questions[],
                   eligibility_assessment, uncertainty_warnings[], summary }
```

## Switch integration — the two real surfaces

### 1. Switch Console Agent Bridge (ingress)

The Switch Console desktop app creates an agent whose bridge endpoint is our
`POST /switch/bridge`. When a human sends a message in a connected
Mattermost/Discord room, Switch normalises the event and POSTs it to our
bridge. We verify `ACCESSBRIDGE_SWITCH_BRIDGE_TOKEN`, create a `Question`,
and schedule the orchestrator as a FastAPI background task. The bridge
returns `200` immediately so Switch sees a clean ack.

For local testing without the Switch Console, `POST /switch/mattermost`
accepts a raw Mattermost outgoing-webhook payload (form or JSON).

### 2. Switch Trust guardrails (every LLM call)

`backend/app/services/llm.py` wraps every LLM call from every agent with
Switch Trust. When `ACCESSBRIDGE_SWITCH_TRUST_API_KEY` is set, calls route
through the Switch Trust gateway under the configured policy. When not set,
the SDK runs in pass-through mode and logs a warning — local development
still works.

## Trust model

- **Official-source preference.** `knowledge_base/sources.py` is a curated
  list of government, university and scheme portals.
- **Source links + retrieval timestamps.** Every `Source` row carries the
  URL and the moment it was retrieved.
- **Honest unreachable reporting.** When a page cannot be fetched, the
  Source is recorded with `reachable=false` and the UI shows it. A bundled
  official excerpt may be used so the workflow still completes, but the
  verification status is `partial` and the confidence note explains it.
- **Uncertainty indicators.** `verification_status` is `verified`,
  `partial`, or `unverified` — never blurred.
- **Human approval gate.** No final guidance reaches the room until a
  coordinator explicitly approves it.
- **No invented details.** The Research Agent's system prompt forbids
  inventing deadlines, amounts or eligibility. The deterministic fallback
  only extracts strings actually present in the source text.

## Execution modes

- **Embedded (default).** The orchestrator calls `research()`, `translate()`,
  `guide()` directly. Deterministic, reliable, used by the demo and tests.
- **Distributed (optional).** Run each agent as its own process
  (`scripts/run_agents.sh`); the orchestrator's `dispatch_distributed()`
  sends real uAgents messages to their Fetch.ai addresses. Demonstrates
  genuine inter-process agent messaging.

## Security

- No secrets in the repository (`.gitignore` excludes `.env`, keys, the
  SQLite file).
- Token verification on every inbound bridge request.
- Review secret required to approve/reject.
- Rate limiting on question submission (default 60/min).
- Upload cap (2 MB) on optional uploads.
- Audit logging on every transition and review action.
- No automatic application submission — AccessBridge produces guidance only.
