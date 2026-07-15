# time-logger setup flow

Loaded on demand from `SKILL.md` when the user says "setup", "configure", or "run
setup". Run this flow interactively.

### 1. Check current state

Read `~/repos/time_logs/capabilities.yml`.
- File missing → announce "Running first-time setup."
- File exists → announce "Reconfiguring." and show current integration statuses.

### 2. Directories

Already created in `SKILL.md` Step 0 — confirm they exist:

```bash
ls ~/repos/time_logs/raw ~/repos/time_logs/time_logs
```

### 3. Probe each integration

Run these checks and record what's available:

**Claude sessions** (always enabled if projects dir exists):
```bash
ls ~/.claude/projects/ 2>/dev/null | wc -l
```
Available if count > 0.

**GitHub** (gh CLI):
```bash
gh auth status 2>&1
```
Available if output contains "Logged in". Extract the username from the output.

**Slack MCP** — call `slack_search_users` with `query: "a"`. Available if no error.

**Google Calendar MCP** — call `list_calendars`. Available if no error.

**Granola MCP** — call `list_meetings` with `time_range: last_30_days`. Available if no error.

### 4. Present findings

Show a table like:
```
Integration       Status       Notes
──────────────────────────────────────────
claude_sessions   available    ~/.claude/projects/ found
slack             available    Slack MCP detected
google_calendar   available    Google Calendar MCP detected
github            available    authenticated as octocat
granola           unavailable  Granola MCP not found
```

For anything unavailable, briefly explain what's needed to enable it.

### 5. Confirm and collect config

For each available integration, ask the user: "Enable [name]? (yes/no)" — or if reconfiguring,
show current state and ask if they want to change it.

If Slack is being enabled and `user_id` is empty, ask:
> "What's your Slack member ID? (Slack → click your name → Profile → ⋮ → Copy member ID)"

### 6. Write capabilities.yml

Write `~/repos/time_logs/capabilities.yml` using this format:

```yaml
# time-logger capabilities
# Last configured: YYYY-MM-DD

settings:
  repo_path: ~/repos/time_logs

integrations:
  claude_sessions:
    enabled: true

  slack:
    enabled: true
    user_id: U01ABCDE123

  google_calendar:
    enabled: true

  github:
    enabled: true
    username: octocat

  granola:
    enabled: false
```

### 7. Bootstrap preference file if missing

Already handled in `SKILL.md` Step 0, but double-check: if `~/repos/time_logs/user-preferences.md`
still doesn't exist, copy it from this skill's own `user-preferences.example.md`.

### 8. Confirm completion

Tell the user which integrations are active and that they can say "prefetch today" to test.
