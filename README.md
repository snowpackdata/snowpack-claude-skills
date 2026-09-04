# snowpack-claude-skills

Reusable Claude Code skills for Snowpack. Follows the [Agent Skills](https://agentskills.io/)
format used by [skills.sh](https://www.skills.sh/) — every skill lives under `skills/{name}/`
with a `SKILL.md` — so standard skills here are installable with:

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill {skill-name}
```

Some skills bundle Claude Code subagents (`.claude/agents/*.md`), which aren't
discoverable by Claude Code while nested inside an installed skill folder — those
skills' `SKILL.md` self-installs its subagents to the global `~/.claude/agents/` as a
first step, so `npx skills add` still works normally. See each skill's own `SKILL.md`
for specifics, and [`AGENTS.md`](./AGENTS.md) for the structural conventions.

## Skills

| Skill | Description | Install |
|---|---|---|
| [`time-logger`](./skills/time-logger) | Assembles a combined daily context file (Slack, Calendar, Claude sessions, GitHub, Granola sections + a draft Potential Time Entries section) for a downstream agent to log against the real time-logging system. | `npx skills add snowpackdata/snowpack-claude-skills --skill time-logger` — see its [`SKILL.md`](./skills/time-logger/SKILL.md) |
| [`gather-context`](./skills/gather-context) | Systematic context-gathering for an unfamiliar operational pipeline: parses declared artifacts (dbt/Airflow), backward-traces consumer dependencies to catch externalized/invisible ones, and surfaces tribal/motivational/ownership gaps as a confirm-or-correct list instead of an open-ended interview. | `npx skills add snowpackdata/snowpack-claude-skills --skill gather-context` — see its [`SKILL.md`](./skills/gather-context/SKILL.md) |
| [`plain-style`](./skills/plain-style) | Revises drafted text to cut passive voice, filler words, redundant phrases, throat-clearing openers, vague language, comma-strung fragments, and em dashes — usable directly or dispatched to by another skill's own final drafting step. | `npx skills add snowpackdata/snowpack-claude-skills --skill plain-style` — see its [`SKILL.md`](./skills/plain-style/SKILL.md) |
