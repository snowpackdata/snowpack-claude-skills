# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Cursor, etc.) when working
with code in this repository.

## Repository Overview

A collection of reusable Claude Code skills for Snowpack. Skills are packaged
instructions and scripts that extend agent capabilities.

## Creating a New Skill

### Directory Structure

```
skills/
  {skill-name}/           # kebab-case directory name
    SKILL.md              # Required: skill definition
    scripts/              # Optional: executable scripts
    references/           # Optional: supporting docs loaded on demand
    lib/                  # Optional: shared code for scripts
```

### Naming Conventions

- **Skill directory**: `kebab-case` (e.g., `time-logger`, `deploy-check`)
- **SKILL.md**: Always uppercase, always this exact filename
- **Scripts**: `kebab-case.sh` or `kebab-case.mjs`

### SKILL.md Format

```markdown
---
name: {skill-name}
description: {One sentence describing when to use this skill. Include trigger phrases.}
---

# {Skill Title}

{Brief description of what the skill does.}

## How It Works / Usage / Output / Troubleshooting

{As needed — see skills/time-logger/SKILL.md for a real example.}
```

### End-User Installation

For skills that are genuinely single-file (a `SKILL.md` plus optional `scripts/` — no
subagents, no separate `CLAUDE.md` driving project-level behavior), document the
standard skills.sh install:

```bash
npx skills add <org>/snowpack-claude-skills --skill {skill-name}
```

**Manual fallback (always works, any skill):**

```bash
cp -r skills/{skill-name} ~/.claude/skills/
```

### Skills that bundle subagents

Some skills (e.g. `time-logger`) bundle Claude Code subagents (`.claude/agents/*.md`).
**Subagents nested inside a `~/.claude/skills/{name}/` folder are not discovered by
Claude Code** — copying or `npx skills add`-installing these silently breaks the
subagent wiring unless the skill fixes it itself. Two options:

1. **Self-install (preferred)** — give the skill's `SKILL.md` a first step that checks
   whether its subagents are already reachable (project-local `.claude/agents/` or
   global `~/.claude/agents/`) and, if not, locates its own installed location
   (`~/.claude/skills/{name}` or `.claude/skills/{name}`) and copies
   `.claude/agents/*.md` into the global `~/.claude/agents/`. This makes the skill
   genuinely `npx skills add`-compatible. See `skills/time-logger/SKILL.md`'s "Step 0 —
   Bootstrap" for a working example, including a fixed output location (not relative to
   whatever project happens to be open) so the skill behaves the same regardless of
   install method.
2. **Manual-clone-only (only if self-install genuinely doesn't fit)** — state plainly in
   `SKILL.md` that `npx skills add` isn't supported, and document cloning the repo and
   opening `skills/{skill-name}` directly in Claude Code instead (its own `CLAUDE.md`
   becomes the project instructions, `.claude/agents/` discovered normally since it's no
   longer nested inside another skill's folder). Prefer option 1 — this should be a last
   resort, not the default.

### Best Practices for Context Efficiency

Skills are loaded on-demand — only the skill name and description are loaded at
startup. The full `SKILL.md` loads into context only when the agent decides the skill
is relevant.

- **Keep SKILL.md under 500 lines** — put detailed reference material in separate files
- **Write specific descriptions** — helps the agent know exactly when to activate
- **Use progressive disclosure** — reference supporting files read only when needed
- **Prefer scripts over inline code** — script execution doesn't consume context, only output does
