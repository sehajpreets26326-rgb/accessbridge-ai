# Multi-Platform Setup — AccessBridge AI

AccessBridge supports five chat platforms through Switch. All credentials are
read from environment variables — never hardcoded.

## Honest status model

Every platform reports one of:
- **Connected**: credentials present AND a message round-trip has been verified.
- **Pending**: credentials entered but not yet verified.
- **Disconnected**: no credentials configured.
- **Error**: last delivery attempt failed.

`GET /switch/health` returns the real status of every platform. The dashboard
shows it. We never mark a platform as connected just because credentials exist.

## Platform setup guides

### Mattermost (recommended, fully tested)
- Deploy Mattermost (cloud or self-hosted).
- Create the 5 channels: `student-questions`, `research-updates`, `translation`, `human-review`, `final-guidance`.
- Create a bot account, add it to all channels.
- Set `ACCESSBRIDGE_MATTERMOST_ENABLED=true`, `ACCESSBRIDGE_MATTERMOST_BASE_URL`, `ACCESSBRIDGE_MATTERMOST_BOT_TOKEN`.
- (Alternative) Outgoing webhook → `http://<host>:8000/switch/mattermost/webhook`.

### Discord
- Create an app at https://discord.com/developers/applications.
- Add a bot, get the token. Set `ACCESSBRIDGE_DISCORD_BOT_TOKEN`.
- Get the channel ID. Set `ACCESSBRIDGE_DISCORD_CHANNEL_ID`.
- Inbound: use the Switch Console to route Discord messages to `/switch/bridge`.

### Slack
- Create an app at https://api.slack.com/apps.
- Add the `chat:write` OAuth scope. Set `ACCESSBRIDGE_SLACK_BOT_TOKEN`.
- Set `ACCESSBRIDGE_SLACK_CHANNEL` (e.g. `#student-questions`).
- Inbound: use the Switch Console to route Slack messages to `/switch/bridge`.

### Telegram
- Create a bot via @BotFather. Set `ACCESSBRIDGE_TELEGRAM_BOT_TOKEN`.
- Get your chat ID via @userinfobot or `/getUpdates`. Set `ACCESSBRIDGE_TELEGRAM_CHAT_ID`.
- Inbound: use the Switch Console, or run `getUpdates` polling (not included).

### Microsoft Teams (outbound only)
- Teams inbound requires a hosted Azure Bot Service (beyond the MVP scope).
- Outbound: create a Power Automate incoming webhook. Set `ACCESSBRIDGE_TEAMS_INCOMING_WEBHOOK_URL`.
- The bridge posts progress + final guidance to this webhook.

## Which platforms are genuinely integrated?

| Platform | Outbound (posting back) | Inbound (receiving messages) |
|---|---|---|
| Mattermost | ✅ Bot token REST API | ✅ Outgoing webhook + Switch Console |
| Discord | ✅ Bot token REST API | ✅ via Switch Console |
| Slack | ✅ Bot token Web API | ✅ via Switch Console |
| Telegram | ✅ Bot API | ✅ via Switch Console |
| Teams | ✅ Incoming webhook | ⚠️ Requires Azure Bot Service |

The outbound side is real for all five. The inbound side for Discord/Slack/
Telegram goes through the Switch Console, which normalises their events into
our `SwitchBridgeEvent` schema — that is the genuine Switch integration.
