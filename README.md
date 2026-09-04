# snowpack-claude-skills

Reusable Claude Code skills for Snowpack. Follows the [Agent Skills](https://agentskills.io/)
format used by [skills.sh](https://www.skills.sh/) — every skill has a `SKILL.md` — so
skills here are installable with:

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill {skill-name}
```

Some skills bundle Claude Code subagents (`.claude/agents/*.md`), which aren't
discoverable by Claude Code while nested inside an installed skill folder — those
skills' `SKILL.md` self-installs its subagents to the global `~/.claude/agents/` as a
first step, so `npx skills add` still works normally. See each skill's own `SKILL.md`
for specifics, and [`AGENTS.md`](./AGENTS.md) for the structural conventions.

## Skill tiers

A skill's tier is decided entirely by which folder it's in — there's no separate
`status:` field to keep in sync. See the
[Publishing & Maintaining Skills](https://app.notion.com/p/3d1d5d2202f98135847ae91710530c20)
doc for the full framework and rationale; `AGENTS.md` and this README reflect what it's
enforced into.

| Folder | Tier | What it means |
|---|---|---|
| `wip/{name}` branch (never merged here) | In Development | Pushed for teammates to test; not shown in this tree at all. |
| `skills/{name}/` | Not yet promoted | Name + description only — no other requirement. |
| `skills/review/{name}/` | Ready for Review | Listed below; `notes:` optional. |
| `skills/production/{name}/` | Production Ready | Listed below; requires a named `owner:`, enforced via [`CODEOWNERS`](./.github/CODEOWNERS). |
| `archive/{name}/` | Archived | Retired, outside `skills/` entirely, invisible to the installer. |

The two tables below are generated from each skill's `SKILL.md` frontmatter — run
`node scripts/build-readme.mjs` after adding, moving, or editing a skill, and commit the
result. CI (`node scripts/build-readme.mjs --check`) fails the PR if it's out of date.

## Production Ready

<!-- SKILLS-TABLE:PRODUCTION:START -->
| Skill | Description | Owner |
|---|---|---|
| [`time-logger`](./skills/production/time-logger) | Assembles a combined daily context file (raw sections from Slack, Google Calendar, Claude Code sessions, GitHub, Granola, plus a draft Potential Time Entries section) for a downstream agent to review and log against the real time-logging system. Use when the user wants to log time, generate a time entry, run setup for time-logger, prefetch a day's activity, or asks "what did I work on [date]". | @jarellano01 |
<!-- SKILLS-TABLE:PRODUCTION:END -->

## Ready for Review

<!-- SKILLS-TABLE:REVIEW:START -->
| Skill | Description | Notes |
|---|---|---|
| [`gather-context`](./skills/review/gather-context) | Run systematic context-gathering against an operational pipeline or process — parse declared artifacts, backward-trace consumer dependencies, surface tribal/motivational/ownership gaps as a confirm-or-correct list, and produce a provenance-annotated diagram by default (an execution-order ERD, or a business-category taxonomy view when that's the real question being asked). Triggers on "gather pipeline context", "map this pipeline", "what's declared vs. tribal here", "run the context taxonomy on this repo", "trace how this business logic/taxonomy is implemented across these models", or when onboarding onto an unfamiliar client pipeline. | Owner @auwng. Ready for a second tester — promote to skills/production/ once someone besides the author has used it successfully. |
<!-- SKILLS-TABLE:REVIEW:END -->
