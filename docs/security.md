# Security — AccessBridge AI

## Threat model

AccessBridge is a public-information education tool. The primary risks are:
- Invented scholarship details reaching a student.
- Prompt injection via retrieved official content.
- Webhook replay / duplicate events creating duplicate questions.
- Credential leakage.
- SSRF via the retriever fetching attacker-controlled URLs.

## Controls implemented

| Control | Location | Tested |
|---|---|---|
| Bridge token verification | `switch_integration/config.py:verify_inbound_token` | ✅ |
| Review secret (constant-time) | `backend/app/security/auth.py:verify_review_secret` | ✅ |
| Rate limiting (per-IP token bucket) | `backend/app/security/auth.py:RateLimiter` | ✅ |
| Safe upload paths (traversal prevention) | `backend/app/security/auth.py:safe_upload_path` | ✅ |
| Idempotency / replay protection | `backend/app/services/idempotency.py` + `processed_events` table | ✅ |
| Pydantic input validation | `backend/app/schemas/api.py` | ✅ |
| No secrets in repo | `.gitignore` excludes `.env`, `*.key`, `*.db` | ✅ |
| Audit logging | `backend/app/services/audit.py` | ✅ |
| Switch Trust guardrails on LLM calls | `backend/app/services/llm.py` | ✅ |

## Prompt injection defence

Retrieved official content is treated as **untrusted data**, not as
instructions. The Research Agent's system prompt explicitly states:
"Use ONLY information present in the provided official source text." The
deterministic fallback extractor uses regex, not LLM parsing, so it cannot
be prompt-injected. Retrieved content never overrides system permissions.

## SSRF defence

The retriever only fetches URLs from the curated `knowledge_base/sources.py`
list — it does not fetch arbitrary user-supplied URLs. The user cannot
control which URL is fetched.

## CORS

`ACCESSBRIDGE_CORS_ORIGINS` defaults to the Vite dev server. Set it to your
production frontend URL in deployment.

## What is NOT implemented (known limitations)

- No JWT-based user authentication (the MVP uses a review secret for the
  coordinator endpoint only).
- No per-user rate limiting (per-IP only).
- No webhook signature verification for Discord/Slack (their events arrive
  through Switch Console, which handles verification on its side).
- No data retention policy enforcement (the `expires_at` field on
  `processed_events` is set but not yet pruned by a background job).

These are documented honestly — not hidden.
