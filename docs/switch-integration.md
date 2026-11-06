# Switch Integration — AccessBridge AI

Switch is the **central communication and collaboration layer** for AccessBridge.
If Switch is removed, the core team-collaboration experience stops working.

## How Switch is central

AccessBridge is not a standalone chatbot. A student's question enters through
a chat platform (Mattermost, Discord, Slack, Telegram, Teams), is routed by
Switch to the AccessBridge bridge endpoint, processed by three independent
Fetch.ai uAgents, reviewed by a human coordinator, and the final approved
guidance is posted back through Switch into the original chat room.

```
Human → Chat platform → Switch → AccessBridge bridge → uAgents → Switch → Chat platform → Human
```

## Two real integration surfaces

### 1. Switch Console — Agent Bridge (ingress)

The Switch Console desktop app creates an agent whose **bridge endpoint** is
our `POST /switch/bridge` route. When a human sends a message in a connected
chat room, Switch normalises the event and POSTs it to our bridge.

The bridge:
1. Verifies the inbound token (`ACCESSBRIDGE_SWITCH_BRIDGE_TOKEN`).
2. Checks for duplicate event delivery via the `processed_events` table.
3. Creates a `Question` row.
4. Schedules the orchestrator as a FastAPI background task.
5. Returns `200` immediately so Switch sees a clean ack.

### 2. Switch Trust — LLM guardrails (every LLM call)

`backend/app/services/llm.py` wraps every LLM call from every agent with
Switch Trust. When `ACCESSBRIDGE_SWITCH_TRUST_API_KEY` is set, calls route
through the Switch Trust gateway under the configured policy. When not set,
the SDK runs in pass-through mode and logs a warning.

## Why this workflow needs Switch

Without Switch, there is no shared room where a student, three AI agents, and
a human coordinator can all see the same conversation. Without Switch Trust,
there is no policy-level guardrail around LLM calls. Without the bridge, there
is no single normalised ingress for events from five different chat platforms.

Switch is the substrate that makes human-agent collaboration real.

## Setup

See `docs/demo-script.md` and `README.md` section 16 for the full setup guide.
The short version:

1. Install the Switch Console desktop app.
2. Create an agent whose bridge endpoint is `http://<host>:8000/switch/bridge`.
3. Set `ACCESSBRIDGE_SWITCH_BRIDGE_TOKEN` to the same token.
4. Connect the agent to your Mattermost/Discord room.
5. Verify: `curl http://localhost:8000/switch/health`.

## Verification

```bash
# Bridge health
curl http://localhost:8000/switch/health | jq .platforms

# Send a test event
curl -X POST http://localhost:8000/switch/bridge \
  -H "Content-Type: application/json" \
  -d '{"room":"student-questions","sender":"alice","text":"AICTE Pragati?"}'
```

The response includes a real `question_id`. Check progress at
`GET /api/agents/question/{question_id}`.
