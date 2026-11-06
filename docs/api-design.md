# API Design — AccessBridge AI

## Principles

- **Consistent prefixes**: `/api/questions`, `/api/review`, `/api/agents`, `/api/dashboard`, `/switch/*`.
- **Pydantic validation** on every input — min/max length, enums, required fields.
- **Honest status codes**: 200 success, 201 created, 404 not found, 409 conflict, 422 validation error, 401/403 auth.
- **Audit everything**: every state change recorded in `audit_events`.
- **No secrets in responses**: tokens, keys, and personal info never appear in API output.

## Routes (17 total)

### Questions lifecycle
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/questions` | Submit a new question (triggers workflow) |
| `GET` | `/api/questions` | List recent questions (newest first) |
| `GET` | `/api/questions/{id}` | Get question detail |
| `GET` | `/api/questions/{id}/evidence` | Evidence inspector — per-claim source refs + freshness |
| `GET` | `/api/questions/{id}/unsupported-claims` | Claims with no supporting source |
| `POST` | `/api/questions/{id}/rerun-research` | Coordinator requests another research pass |

### Human review
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/review/{id}` | List all review actions on a question |
| `POST` | `/api/review/{id}` | Approve / reject / request corrections (requires secret) |
| `POST` | `/api/review/{id}/deliver` | Post approved guidance to the chat room |

### Agent workspace + dashboard
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/agents/executions` | Recent agent executions (all questions) |
| `GET` | `/api/agents/question/{id}` | Full workspace: research, translation, guidance, evidence, executions, audit |
| `GET` | `/api/dashboard` | Aggregate stats: recent, active runs, pending reviews, verification summary |
| `GET` | `/api/dashboard/evaluation` | Reproducible evaluation dataset + methodology |

### Switch bridge
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/switch/bridge` | Switch Console Agent Bridge endpoint (token-verified, idempotent) |
| `POST` | `/switch/mattermost/webhook` | Raw Mattermost outgoing webhook (form or JSON) |
| `GET` | `/switch/health` | Bridge health + all 5 platform statuses |

### Meta
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | App health: switch_trust, mattermost, database |
| `GET` | `/` | Root: app name, version, docs link |

## Request/response examples

### Submit a question
```bash
curl -X POST http://localhost:8000/api/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text":"AICTE Pragati scholarship for girls?","language":"en"}'
```
```json
{"id":"a1b2c3...","status":"received","question_text":"...","language":"en","created_at":"..."}
```

### Approve guidance (coordinator)
```bash
curl -X POST http://localhost:8000/api/review/a1b2c3 \
  -H "Content-Type: application/json" \
  -d '{"action":"approved","reviewer_name":"alice","secret":"your-review-secret"}'
```

### Evidence inspector
```bash
curl http://localhost:8000/api/questions/a1b2c3/evidence
```
```json
[{"claim":"Family income limit: Rs. 8 lakh","claim_type":"eligibility",
  "source_url":"https://www.aicte-india.org/...","excerpt":"...","confidence":"uncertain",
  "freshness_days":0.5}]
```

## Error responses

Every error is a JSON object with a `detail` field:
```json
{"detail":"Question not found"}
```
Status codes: 400 (bad request), 401 (bad token), 403 (bad review secret), 404 (not found), 409 (wrong state), 422 (validation), 429 (rate limited).
