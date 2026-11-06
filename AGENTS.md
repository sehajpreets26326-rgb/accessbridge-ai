# AGENTS.md — AccessBridge AI coding rules

> Inspired by [Ponytail](https://github.com/DietrichGebert/ponytail): write only
> what the task needs, and never cut validation, error handling, security, or
> accessibility. The code ends up small because it is necessary, not golfed.

## How AccessBridge agents work

Three independent Fetch.ai uAgents — Research, Language, Guidance — exchange
structured Pydantic messages under an orchestrator. A human coordinator
reviews before anything reaches a student. Switch is the communication
substrate (Console Agent Bridge + Switch Trust guardrails).

## Rules for any change to this repo

1. **Read the code your change touches.** Trace the real flow before writing.
   Don't guess what a function does — open it.
2. **Reuse what exists.** The repo has `uagents.Model` schemas, a RAG retriever,
   a Switch bridge, SQLAlchemy models, and a teammate persona module. Use them.
   Don't install a new library when 10 lines of existing code will do.
3. **Never cut validation.** Pydantic schemas enforce min/max length, enums,
   and required fields. Keep them. Don't loosen a constraint to make a test pass.
4. **Never cut security.** Token verification, review secret, rate limiting,
   safe upload paths, audit logging — these are the trust contract. If a test
   fails because of a security check, the test is wrong, not the check.
5. **Never cut accessibility.** The UI is keyboard-navigable, semantic, and
   has ARIA labels. Don't break that.
6. **Every claim has a source.** The Research Agent's `evidence` list links each
   eligibility claim to a source URL + excerpt + timestamp. Don't produce a
   claim without one. If you can't find a source, mark it `unavailable`.
7. **Be honest about failure.** When a source can't be fetched, record
   `reachable=false`. When information is uncertain, say so. Never pretend a
   live fetch happened.
8. **Tests run in <10s.** The conftest patches the retriever to skip HTTP.
   Don't add a test that makes a real network call. Don't add a test that
   takes >5s.
9. **One small change at a time.** Run `pytest -q` after each change. Fix
   errors before moving on.
10. **End every reply with what was skipped or not checked.**

## What NOT to do

- Don't add a new dependency when the existing stack does the job.
- Don't add fake statistics, fake testimonials, or fake agent activity.
- Don't add purple-pink gradients, glowing cards, or AI-robot illustrations.
- Don't claim Switch is integrated if you haven't tested the bridge endpoint.
- Don't commit `.env`, API keys, tokens, or the SQLite database.
- Don't loosen a test to make it pass. Fix the code.

## The teammate tone

Agent progress messages sound like a supportive senior teammate — warm,
encouraging, and honest. See `backend/app/services/teammate.py`. No excessive
emojis (the editorial design forbids it). Celebrate completions. Be plain
about failures.
