# Demo script — AccessBridge AI

A 2–3 minute walkthrough of one complete workflow. Record in a single take
if possible; if not, cut only between scenes.

## Before you record

- [ ] Backend running: `uvicorn backend.app.main:app --port 8000`
- [ ] Frontend running: `cd frontend && npm run dev` (http://localhost:5173)
- [ ] Mattermost open in another tab, logged into the team, with the five
      channels created: `#student-questions`, `#research-updates`,
      `#translation`, `#human-review`, `#final-guidance`.
- [ ] Switch Console configured with the bridge endpoint pointing at
      `http://localhost:8000/switch/bridge` and the bridge token set.
- [ ] A coordinator account ready in the frontend.
- [ ] Terminal open next to the browser so the agent process logs are
      visible.

## Scene 1 — A student asks (≈20s)

- Show the Mattermost `#student-questions` channel.
- A student (you, playing the role) types:

  > "What documents do I need for the AICTE Pragati scholarship for girls?
  > I am in my second year of B.Tech and my family income is below 8 lakh."

- Say: *"A student asks a real question in the shared Mattermost room.
  Switch routes this to AccessBridge."*

## Scene 2 — Switch receives the task (≈15s)

- Switch to the terminal running the backend.
- Show the log line: `switch_bridge: message_received … question_id=…`
- Say: *"Switch's Console Agent Bridge delivers the message to our
  `/switch/bridge` endpoint. AccessBridge creates a question row and starts
  the orchestrator."*

## Scene 3 — Research Agent finds official sources (≈30s)

- Show `#research-updates` receiving: *"Research started — searching
  official sources."*
- Then: *"Official sources found: 3 source(s). Verification: partial."*
- Switch to the AccessBridge **Agent Workspace** page in the frontend.
  Show the Research Agent card with status `success`, the 3 sources listed
  with their URLs and retrieval timestamps.
- Say: *"The Research Agent — a real Fetch.ai uAgent — matched the question
  against curated official sources, fetched them, and extracted structured
  eligibility, documents and deadlines. Every source carries a URL and a
  retrieval timestamp. Verification is partial because we are honest about
  reachability."*

## Scene 4 — Language Agent simplifies and translates (≈25s)

- Show `#translation` receiving: *"Translation completed."*
- In the Agent Workspace, click the Language Agent card. Show the
  simplified text and the 4 preserved original official snippets.
- Switch the language selector to **Punjabi** (or Hindi) to show the
  translated guidance.
- Say: *"The Language Agent simplifies the official wording and translates
  it — but it preserves the exact original wording for important conditions,
  so nothing is lost in translation."*

## Scene 5 — Guidance Agent builds the checklist (≈25s)

- In the Agent Workspace, click the Guidance Agent card. Show the 18-item
  checklist, the 1 flagged missing piece of information, and the 1
  uncertainty warning.
- Say: *"The Guidance Agent builds a personalised application checklist,
  flags what the student still needs to provide, and raises an uncertainty
  warning — so the coordinator knows what to check."*

## Scene 6 — Human coordinator reviews (≈25s)

- Open the **Human Review workspace** in the frontend.
- Show: the original question, the official sources, the extracted
  eligibility, the translated guidance, the checklist.
- Click **Approve**. Enter your coordinator name.
- Say: *"Nothing reaches the student until a human coordinator reviews the
  sources, the extracted fields and the translated guidance, and explicitly
  approves. The approval is recorded with the reviewer's name and a
  timestamp."*

## Scene 7 — Final guidance appears in the room (≈15s)

- Switch back to Mattermost. Show `#final-guidance` receiving the approved
  answer, with source links and the verification timestamp.
- Say: *"Only after approval is the final guidance posted back into the
  shared room — with source links and a clear verification timestamp."*

## Scene 8 — Dashboard + agent execution history (≈15s)

- Open the AccessBridge **Dashboard**.
- Show the request in the list with status `delivered`, the agent execution
  history (3 rows, all `success`), and the audit log.
- Say: *"Every step — research, translation, guidance, review — is recorded
  in the database. The dashboard reads from real data, not from a mockup."*

## Closing line (≈10s)

> *"AccessBridge AI — three Fetch.ai uAgents, Switch as the communication
> substrate, a human coordinator as the trust gate. Making essential
> information understandable and accessible to everyone."*

---

## Demo recording checklist

- [ ] Resolution: 1920×1080, 30fps minimum.
- [ ] Audio: clean voiceover, no background music.
- [ ] Browser zoom: 100% (so text is readable).
- [ ] No personal information visible in Mattermost or the dashboard.
- [ ] No API keys, tokens, or `.env` contents visible in the terminal.
- [ ] Title card: project name + tagline.
- [ ] End card: GitHub URL + "Built for the Flip the Switch hackathon."
- [ ] Upload as unlisted on YouTube and link it in `README.md` section 26.

## Judge-facing problem & impact (60-second pitch)

> Millions of students miss scholarship deadlines every year not because they
> are not eligible, but because the information is scattered, jargon-heavy,
> English-only, and unverified. Generic chatbots make this worse — they
> hallucinate deadlines and eligibility with confidence.
>
> AccessBridge AI is a multi-agent system built on Fetch.ai uAgents and
> Switch. Three specialist agents — Research, Language, Guidance —
> collaborate through structured messages, with every claim tied to a real
> official source and a retrieval timestamp. A human coordinator reviews
> before anything reaches a student. The whole workflow runs through a real
> Mattermost room via Switch.
>
> It is not a chatbot. It is a team of agents and a human, with reliability
> as the design goal — because for a student, a wrong deadline is not a
> minor bug.
