# snowpack-claude-skills

This repository contains reusable Claude Code skills for Snowpack. It follows the [Agent Skills](https://agentskills.io/)
format used by [skills.sh](https://www.skills.sh/): every skill has a `SKILL.md`, so
skills here are installable with:

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill {skill-name}
```

Some skills bundle Claude Code subagents (`.claude/agents/*.md`), which Claude Code
can't discover while they sit nested inside an installed skill folder. Those
skills' `SKILL.md` self-installs its subagents to the global `~/.claude/agents/` as a
first step, so `npx skills add` still works normally. See each skill's own `SKILL.md`
for specifics, and [`AGENTS.md`](./AGENTS.md) for the structural conventions.

## Skill tiers

The folder a skill lives in decides its tier entirely. There's no separate
`status:` field to keep in sync. See the
[Publishing & Maintaining Skills](https://app.notion.com/p/3d1d5d2202f98135847ae91710530c20)
doc for the full framework and rationale. `AGENTS.md` and this README reflect what it's
enforced into.

| Folder | Tier | What it means |
|---|---|---|
| `wip/{name}` branch (never merged here) | In Development | Pushed for teammates to test; not shown in this tree at all. |
| `skills/{name}/` | Not yet promoted | Name + description only — no other requirement. |
| `skills/review/{name}/` | Ready for Review | Listed below; `notes:` optional. |
| `skills/production/{name}/` | Production Ready | Listed below; requires a named `owner:`, enforced via [`CODEOWNERS`](./.github/CODEOWNERS). |
| `archive/{name}/` | Archived | Retired, outside `skills/` entirely, invisible to the installer. |

`node scripts/build-readme.mjs` generates the two tables below from each skill's
`SKILL.md` frontmatter. Run it after adding, moving, or editing a skill, and commit
the result. CI (`node scripts/build-readme.mjs --check`) fails the PR if it's out of
date.

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
| [`plain-style`](./skills/review/plain-style) | Revise drafted text to eliminate passive voice, filler words, redundant phrases, throat-clearing openers, vague language, comma-strung fragments, fragmented outlines standing in for real paragraphs, and em dashes -- replacing each with direct, specific, flowing prose. Returns only the revised text, never a changelog of what was edited. Bundles a reusable `apply-style-guide` subagent other skills can dispatch to as a final drafting step, before their own output is considered finished. Triggers on "clean up the style of this", "make this more direct", "cut the filler from this", "apply the style guide", or when another skill's own instructions call for a style-enforcement pass before finalizing output. | Owner @auwng. Ready for a second tester — promote to skills/production/ once someone besides the author has used it successfully. |
<!-- SKILLS-TABLE:REVIEW:END -->
