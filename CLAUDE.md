# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Cursor, etc.) when working
with code in this repository.

## Repository Overview

A collection of reusable Claude Code skills for Snowpack. Skills are packaged
instructions and scripts that extend agent capabilities.

Skills move through tiers as they mature. A skill's tier is decided entirely by which
folder it's in — there's no separate `status:` frontmatter field, because that would be a
second source of truth that could drift out of sync with the folder it's actually in.
Tooling in `scripts/` (`validate-skills.mjs`, `build-readme.mjs`, `build-codeowners.mjs`)
derives everything from folder location and enforces it in CI. See the
[Publishing & Maintaining Skills](https://app.notion.com/p/3d1d5d2202f98135847ae91710530c20)
doc for the full rationale behind the tiers below.

## Directory Structure

```
skills/
  {skill-name}/               # Not yet promoted — SKILL.md with name+description only,
                               # no other requirement
  review/{skill-name}/        # Ready for Review
    SKILL.md                  # Required: skill definition
    scripts/                  # Optional: executable scripts
    references/               # Optional: supporting docs loaded on demand
    lib/                      # Optional: shared code for scripts
  production/{skill-name}/    # Production Ready — same layout as review/, plus an
                               # owner: in frontmatter
archive/{skill-name}/         # Archived — outside skills/ entirely, invisible to the
                               # installer
```

**In Development** work never appears in this tree at all — it stays on a
`wip/{skill-name}` branch until it clears the Ready for Review bar, on purpose.

To move a skill between tiers, `git mv` the whole directory to preserve history, update
its frontmatter (see below), then regenerate the README tables:

```bash
git mv skills/{skill-name} skills/review/{skill-name}
node scripts/build-readme.mjs
```

### Naming Conventions

- **Skill directory**: `kebab-case` (e.g., `time-logger`, `deploy-check`)
- **SKILL.md**: Always uppercase, always this exact filename
- **Scripts**: `kebab-case.sh` or `kebab-case.mjs`

### SKILL.md Frontmatter

Every `SKILL.md`, at any tier, requires:

```yaml
---
name: {skill-name}
description: {One sentence describing when to use this skill. Include trigger phrases.}
---
```

Additionally, for a skill in `skills/production/`:

```yaml
owner: {@github-handle or @org/team}   # required — not a display name
```

`owner:` is what `scripts/build-codeowners.mjs` turns into an enforced reviewer in
`.github/CODEOWNERS`. It must resolve to a real GitHub user or team.

Optionally, for a skill in `skills/review/`:

```yaml
notes: {free text, shown in the Ready for Review table's Notes column — blank is fine}
```

Full `SKILL.md` shape:

```markdown
---
name: {skill-name}
description: {One sentence describing when to use this skill. Include trigger phrases.}
owner: {@handle}      # production tier only
notes: {free text}    # review tier only, optional
---

# {Skill Title}

{Brief description of what the skill does.}

## How It Works / Usage / Output / Troubleshooting

{As needed — see skills/production/time-logger/SKILL.md for a real example.}
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
cp -r skills/review/{skill-name} ~/.claude/skills/{skill-name}
# or skills/production/{skill-name}, skills/{skill-name} — match wherever it currently lives
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
   genuinely `npx skills add`-compatible. See `skills/production/time-logger/SKILL.md`'s
   "Step 0 — Bootstrap" for a working example, including a fixed output location (not
   relative to whatever project happens to be open) so the skill behaves the same
   regardless of install method.
2. **Manual-clone-only (only if self-install genuinely doesn't fit)** — state plainly in
   `SKILL.md` that `npx skills add` isn't supported, and document cloning the repo and
   opening the skill's directory directly in Claude Code instead (its own `CLAUDE.md`
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

## Repo Tooling

- `node scripts/validate-skills.mjs` — fails if a promoted skill (`review/` or
  `production/`) is missing required frontmatter or isn't linked from `README.md`. Run
  from repo root; CI runs this on every PR.
- `node scripts/build-readme.mjs` — regenerates the Production Ready and Ready for
  Review tables in `README.md` from frontmatter. `--check` mode (used in CI) exits
  non-zero if the committed README is stale instead of writing it.
- `node scripts/build-codeowners.mjs` — regenerates `.github/CODEOWNERS` from each
  production skill's `owner:` field. No-ops cleanly if there are no production skills
  yet.

## Workflows

Four common operations. All assume `gh` CLI access and a local clone. See the
[Publishing & Maintaining Skills](https://app.notion.com/p/3d1d5d2202f98135847ae91710530c20)
doc for the full rationale and tester/owner expectations at each tier — this is just the
mechanics.

### 1. Publish a new skill (In Development)

No PR — In Development stays off `main` entirely.

```bash
git checkout main && git pull
git checkout -b wip/{skill-name}
mkdir -p skills/{skill-name}
cat > skills/{skill-name}/SKILL.md <<'EOF'
---
name: {skill-name}
description: One sentence describing when to use this skill. Include trigger phrases.
---

# {Skill Title}

🧪 In Development — rough, expect breakage. What it does, how to use it.
EOF
git add skills/{skill-name}
git commit -m "wip: {skill-name}"
git push -u origin wip/{skill-name}
```

Tell teammates directly (Slack, not a PR) that the branch exists and what to try.

### 2. Promote In Development → Ready for Review

Continue on the same `wip/{skill-name}` branch:

```bash
git checkout wip/{skill-name}
git mv skills/{skill-name} skills/review/{skill-name}
# optionally add notes: to SKILL.md's frontmatter — blank is fine
node scripts/build-readme.mjs
node scripts/validate-skills.mjs   # should exit 0 before you push
git add -A
git commit -m "Promote {skill-name}: In Development -> Ready for Review"
git push -u origin wip/{skill-name}
gh pr create --base main --head wip/{skill-name}
```

`gh pr create` opens pre-filled from `.github/pull_request_template.md`. CI
(`validate-skills.yml`) must pass; get at least one teammate to skim the PR — not a
blocking approval at this tier.

### 3. Archive a skill

```bash
git checkout main && git pull
git checkout -b archive-{skill-name}
git mv skills/review/{skill-name} archive/{skill-name}
# or: git mv skills/production/{skill-name} archive/{skill-name}
node scripts/build-readme.mjs        # drops it from whichever table it was in
node scripts/build-codeowners.mjs    # drops its CODEOWNERS line, if it had one
git add -A
git commit -m "Archive {skill-name}: no longer maintained"
git push -u origin archive-{skill-name}
gh pr create --base main
```

`archive/{name}/` sits outside `skills/` entirely, so the skill disappears from both
README tables and from `npx skills add` the moment this merges. Say why in the PR
description.

### 4. Maintain a published skill

- **Edit content**: change the files, keep `SKILL.md` frontmatter accurate, regenerate
  the README if the description changed (`node scripts/build-readme.mjs`), push to a
  PR. Editing a Production Ready skill requires the named `owner:`'s review once branch
  protection's Code Owners rule is turned on.
- **Reassign an owner**: edit `owner:` in `SKILL.md`, run
  `node scripts/build-codeowners.mjs`, and commit the regenerated
  `.github/CODEOWNERS` — the new owner's review isn't enforced until that merges.
- **Promote Ready for Review → Production Ready**: confirm someone besides the author
  has used it successfully and is willing to be named, then `git mv
  skills/review/{name} skills/production/{name}`, add `owner: @handle` to frontmatter,
  run both generator scripts, open a PR.
- **Rename**: `git mv` the directory, update `name:` in frontmatter, regenerate the
  README.
