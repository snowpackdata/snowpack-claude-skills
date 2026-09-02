---
name: wip-github
description: One-screen readout of every piece of GitHub work you have left open, across all repos you and Claude can reach. Open PRs you own (draft vs ready, with merge/CI/review state), PRs waiting on your review, branches with your commits but no PR, issues you opened, and repos Claude cannot see. Use when the user says "/wip-github", "what do I have open on GitHub", "what's hanging", "where did I leave off", "my open PRs", or wants a next-action pick across repos.
---

# wip-github

Deterministic collection, thin interpretation. `scripts/wip.py` does every GitHub call and
renders the readout. You add exactly two lines on top: one sentence of summary, one
next action. Nothing else.

Read-only. Never writes to GitHub, never prints tokens, never hard-codes repos. Safe to
install on a client machine.

## Step 0 — locate the script

```bash
SKILL_DIR=""
for candidate in ~/.claude/skills/wip-github .claude/skills/wip-github; do
  [ -f "$candidate/scripts/wip.py" ] && SKILL_DIR="$candidate" && break
done
WIP="${SKILL_DIR:+$SKILL_DIR/}scripts/wip.py"
```

## Step 1 — run it

Requires `python3` and either `gh` (authenticated) or `GH_TOKEN`/`GITHUB_TOKEN` in env.

```bash
python3 "$WIP"                 # markdown; auto-discovers repos
python3 "$WIP" --no-branches   # ~5x cheaper; skips the branch scan
python3 "$WIP" --json          # machine-readable
```

**Discovery works two ways, chosen automatically:**

- **Unrestricted token (your laptop, `gh auth login`)**: cross-account search API
  finds everything you authored, were asked to review, or touched, in any repo.
  Branches are scanned per repo over `user/repos` pushed within `--days` (default 90).
- **Bound token (Claude Code on the web, Claude GitHub App)**: search is blocked.
  The script falls back to scanning repo by repo and needs a repo list. Get it from the
  `list_repos` tool of the claude-code-remote MCP server, then pass every `full_name`:

  ```bash
  python3 "$WIP" --repos owner/a,owner/b,owner/c
  ```

  Repos that return 403 land in **Not scanned**. Attaching them needs `add_repo`, which
  prompts the user per repo. Do not loop on denials; report them.

Repo list can also come from `$WIP_GITHUB_REPOS` or `~/.config/wip-github/repos.txt`
(one `owner/name` per line). Keep that file out of client repos.

## Step 2 — output

Print the script's markdown **verbatim** under two lines of yours:

```
<one sentence: what the shape of the backlog is>
**Do first:** <one line; agree with the script's Next or override with a reason>

<script output>
```

Rules for those two lines:
- Sentence names counts and the oldest thing, nothing else.
- Override the script's pick only when you know something it cannot (a PR the user said
  is parked, a reviewer who is out). Say why in five words or fewer.
- Do not re-list, re-group, or paraphrase the script's sections.
- If the run says `per-repo scan`, add a third line naming how many repos were not
  scanned so the user knows the readout is partial.

## What the readout contains

| Section | Source | Notes |
|---|---|---|
| Next | `pick_next()` rule order | changes requested > review requested > conflict > CI failing > approved+clean > unreviewed > oldest ready > oldest draft > stalest branch > oldest issue |
| Needs you | your PRs with changes requested, PRs requesting your review | |
| My PRs ready/draft | author = you | state is `mergeable_state` + last review per reviewer |
| Watching | you reviewed or are assigned, not author | commented-only detection needs search API |
| Branches without a PR | branches with your commits, ahead of default, no open PR | branches with a closed PR are counted, not listed; merged ones counted as deletable |
| Issues | opened by you, assigned to you | capped at `--limit` (default 10) |
| Not scanned | 403 per repo | web sessions only |
| You can see, Claude cannot | `user/repos` minus `~/.config/wip-github/claude-repos.txt` | file is written from a web session's `list_repos`; section skipped when absent |

Flags: `--limit N` lines per section (0 = all), `--max-branches N` per repo (default 80),
`--days N` repo recency for auto-discovery, `--no-coverage` to skip the access diff,
`--no-search` to force the per-repo path, `--workers N`.

`python3 "$WIP" --selftest` runs 20 offline logic checks (ordering, rule precedence,
truncation, rendering, error classification) with no network or auth, and exits non-zero
on failure. Run it after editing the script, and on a client machine to sanity-check the
install before pointing it at their org.

Output is deterministic: two runs on unchanged data are byte-identical apart from the
timestamp and call count. Every list is stalest-first with ties broken by repo then
number, so truncation always keeps the most-stale items. Both collection paths are
cross-checked to return the same PRs and issues for the same repo set.

To fill the coverage diff, run the `list_repos` MCP tool in a Claude Code **web** session
and write each `full_name` to `~/.config/wip-github/claude-repos.txt`, one per line. There
is no API for this: `/user/installations` requires a GitHub App user-to-server token, which
`gh auth login` cannot issue.

## Known limits

Read [`references/api-surface.md`](./references/api-surface.md) if a run looks wrong.
Short version: branch authorship comes from commit author login, so commits with an
unlinked email are invisible; `mergeable_state` can stay `unknown` on very stale PRs;
in bound sessions, "commented on but never reviewed" PRs are not found.

## Install

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill wip-github
```

or `cp -r skills/wip-github ~/.claude/skills/`. No subagents, no extra config.
