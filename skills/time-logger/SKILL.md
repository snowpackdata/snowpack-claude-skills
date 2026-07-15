---
name: time-logger
description: Assembles a combined daily context file (raw sections from Slack, Google Calendar, Claude Code sessions, GitHub, Granola, plus a draft Potential Time Entries section) for a downstream agent to review and log against the real time-logging system. Use when the user wants to log time, generate a time entry, run setup for time-logger, prefetch a day's activity, or asks "what did I work on [date]".
---

# time-logger

Pulls from wherever you actually did work into one combined daily file — raw context per
source, plus a draft entry list — instead of reconstructing your day from memory at the
end of the week. Doesn't log anything itself; hand the output to a downstream agent with
access to the real time-logging system to review and finalize.

Works from any project — output always goes to `~/repos/time_logs/` regardless of what
you currently have open in Claude Code.

## Step 0 — Bootstrap (once, automatic)

This skill bundles six subagents (`.claude/agents/fetch-*-day.md`,
`.claude/agents/generate-time-entry.md`) that aren't discoverable by Claude Code while
they sit inside an installed skill folder — subagents are only picked up from a
project's own `.claude/agents/` or the global `~/.claude/agents/`. Before doing anything
else, locate this skill's own files and, if the subagents and local config aren't set up
yet, install them:

```bash
SKILL_DIR=""
for candidate in ~/.claude/skills/time-logger .claude/skills/time-logger; do
  if [ -d "$candidate/.claude/agents" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done

mkdir -p ~/repos/time_logs/raw/{slack,calendar,claude,github,granola} ~/repos/time_logs/time_logs

if [ -n "$SKILL_DIR" ] && [ ! -f ~/.claude/agents/generate-time-entry.md ] && [ ! -f .claude/agents/generate-time-entry.md ]; then
  mkdir -p ~/.claude/agents
  cp "$SKILL_DIR"/.claude/agents/*.md ~/.claude/agents/
  echo "Installed time-logger subagents to ~/.claude/agents/"
fi

if [ -n "$SKILL_DIR" ] && [ ! -f ~/repos/time_logs/capabilities.yml ]; then
  cp "$SKILL_DIR/capabilities.example.yml" ~/repos/time_logs/capabilities.yml
fi
if [ -n "$SKILL_DIR" ] && [ ! -f ~/repos/time_logs/user-preferences.md ]; then
  cp "$SKILL_DIR/user-preferences.example.md" ~/repos/time_logs/user-preferences.md
fi
```

If you cloned this repo directly and opened `skills/time-logger` itself as the project
root, `$SKILL_DIR` won't match either candidate (it's not installed as a skill) — its own
`.claude/agents/` already works natively via normal per-project discovery, so the
subagent-copy step is skipped safely; only the directory/config bootstrap still applies.

## Setup

When the user says **"setup"**, **"configure"**, or **"run setup"**: probe which
integrations are available, ask which to enable, and write `~/repos/time_logs/capabilities.yml`.
Full step-by-step flow in [`references/setup.md`](./references/setup.md) — read it now
if this is a setup request.

## Prefetch

When the user says **"prefetch [date]"**: read `~/repos/time_logs/capabilities.yml` and
spawn only the `fetch-*-day` subagents for enabled integrations, in parallel. Always run
`fetch-claude-sessions-day` regardless (local, always available). Then run
`generate-time-entry` for that date.

## Generate

When the user says **"log [date]"** or **"generate time entries for [date]"**: run just
`generate-time-entry` for that date (see `.claude/agents/generate-time-entry.md`, now
installed per Step 0), which assembles the combined file from whatever raw files already
exist under `~/repos/time_logs/raw/`.

## Feedback

When the user corrects something ("always skip standup", "that's for client X") or
teaches a new preference, append it to `~/repos/time_logs/user-preferences.md` — see the
Corrections log format already in that file.

## Install

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill time-logger
```

The Step 0 bootstrap above handles the subagent-discovery issue that would otherwise
break this after an `npx` install. Manual clone also still works if you'd rather work
inside the repo directly:

```bash
git clone https://github.com/snowpackdata/snowpack-claude-skills.git
cd snowpack-claude-skills/skills/time-logger
./setup.sh
```
