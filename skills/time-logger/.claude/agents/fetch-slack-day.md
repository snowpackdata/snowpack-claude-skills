---
name: fetch-slack-day
description: Fetches all Slack messages sent by the caller on a specific date and saves them to ~/repos/time_logs/raw/slack/YYYY-MM-DD.md. Invoked by the prefetch-day skill with a target date.
model: haiku
color: yellow
---

You fetch Slack messages for a single date and write a clean summary file.

The target date will be provided in your task prompt in YYYY-MM-DD format.

## Step 0 — Check capabilities

Read `~/repos/time_logs/capabilities.yml`. If the file exists:
- If `slack.enabled` is `false`, write `~/repos/time_logs/raw/slack/YYYY-MM-DD.md` containing
  `Slack disabled in capabilities.yml — skipping.` and stop.
- Read `slack.user_id` — use this as the Slack user ID in Step 1.

If the file doesn't exist, proceed and use the user ID embedded in the task prompt (if any),
or ask the user to run setup.

## What to do

1. Search Slack for all messages sent by the user on the target date using the `slack_search_public_and_private` MCP tool:
   - `query`: `from:<@SLACK_USER_ID> on:YYYY-MM-DD` (use the user_id from capabilities.yml)
   - `sort`: `timestamp`
   - `sort_dir`: `asc`
   - `limit`: 20
   - `include_context`: false

2. If the result contains a pagination cursor, fetch the next page using the `cursor` parameter. Keep paginating until no cursor is returned or you have 60 messages total.

3. Write the output file to `~/repos/time_logs/raw/slack/YYYY-MM-DD.md` using this format:

```
# Slack Activity — [Weekday], [Month Day], [Year]

---

**HH:MM AM/PM** | [Channel name or "DM → Person Name"]
[Message text]

**HH:MM AM/PM** | ...
```

**Formatting rules:**
- Use 12-hour time with AM/PM
- For DMs, use "DM → Person Name" as the channel label
- Collapse purely reactive messages ("yeah", "ok", "one sec", "no worries") into `(brief acknowledgment)` if they add no signal — but preserve any message containing a PR link, ticket ID, decision, status update, or substantive question
- If you hit the 60-message cap with a cursor still available, add a note at the bottom: `> Note: more messages may exist — rerun prefetch to get next page`

4. Report the number of messages written.
