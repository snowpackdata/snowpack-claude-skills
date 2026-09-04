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
| `skills/review/{name}/` | Ready for Review | Listed below; requires `summary:` (≤140 chars); `notes:` optional. |
| `skills/production/{name}/` | Production Ready | Listed below; requires `summary:` (≤140 chars) and a named `owner:`, enforced via [`CODEOWNERS`](./.github/CODEOWNERS). |
| `archive/{name}/` | Archived | Retired, outside `skills/` entirely, invisible to the installer. |

`node scripts/build-readme.mjs` generates the two tables below from each skill's
`SKILL.md` frontmatter. Run it after adding, moving, or editing a skill, and commit
the result. CI (`node scripts/build-readme.mjs --check`) fails the PR if it's out of
date.

## Production Ready

<!-- SKILLS-TABLE:PRODUCTION:START -->
| Skill | Description | Owner |
|---|---|---|
| [`time-logger`](./skills/production/time-logger) | Builds a daily work-activity file from Slack, Calendar, GitHub, Claude sessions, and Granola. Use to log time or recall a day's work. | @jarellano01 |
<!-- SKILLS-TABLE:PRODUCTION:END -->

## Ready for Review

<!-- SKILLS-TABLE:REVIEW:START -->
| Skill | Description | Notes |
|---|---|---|
| [`gather-context`](./skills/review/gather-context) | Systematically maps an unfamiliar pipeline's declared and tribal context. Use when onboarding onto or auditing a client pipeline. | Owner @auwng. Ready for a second tester — promote to skills/production/ once someone besides the author has used it successfully. |
| [`plain-style`](./skills/review/plain-style) | Revises drafted prose to be direct, active, and free of filler. Use to tighten writing before it ships. | Owner @auwng. Ready for a second tester — promote to skills/production/ once someone besides the author has used it successfully. |
<!-- SKILLS-TABLE:REVIEW:END -->
