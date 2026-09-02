# API surface, tested behaviour, and known gaps

Everything below was verified on 2026-09-02 against a live account from a Claude Code
web session (bound token) and reasoned from GitHub docs for the laptop path.

## Two environments, two capabilities

| Capability | Laptop `gh auth login` | Claude Code web (Claude GitHub App token) |
|---|---|---|
| `GET /user` | yes | yes (returns the human user) |
| `GET /search/issues?q=author:@me` | yes, 30 req/min | **403** "sessions are bound to their configured repositories" |
| GraphQL `viewer { pullRequests }` | yes | **403** only pinned PR-review operations served |
| `GET /user/repos`, `/user/orgs`, `/user/installations` | yes | **403** |
| `GET /notifications`, `/users/{u}/events` | yes | **403** |
| `GET /repos/{o}/{r}/...` | yes | yes, only for repos attached to the session |
| Attach more repos | n/a | `add_repo` MCP tool, per-repo permission prompt |
| List repos Claude can see | not possible (see below) | `list_repos` MCP tool |

Consequence: on the web, **discovery is an MCP step, collection is the script**. On a
laptop the script does both.

## Endpoints the script uses

Fast path (search available), 5 calls plus enrichment:
- `search/issues?q=is:pr is:open author:@me`
- `search/issues?q=is:pr is:open review-requested:@me`
- `search/issues?q=is:pr is:open involves:@me -author:@me`
- `search/issues?q=is:issue is:open author:@me`
- `search/issues?q=is:issue is:open assignee:@me -author:@me`

Fallback per repo:
- `repos/{r}/pulls?state=open` (author, draft, requested reviewers, assignees, head ref)
- `repos/{r}/pulls/{n}/reviews` for each open PR not yours (did you review it)
- `repos/{r}/issues?state=open&creator=me`, `...&assignee=me`

Enrichment, per PR that is yours or requests your review (2 to 4 calls):
- `repos/{r}/pulls/{n}` for `mergeable_state`; re-fetched up to twice after 1.5s when
  GitHub reports `unknown` (mergeability is computed lazily on first request)
- `repos/{r}/pulls/{n}/reviews`, last state per reviewer wins, author's own excluded

Branches, per repo (always per repo, there is no search for refs):
- `repos/{r}` for default branch
- `repos/{r}/branches` up to `--max-branches`
- `repos/{r}/compare/{default}...{branch}` for each non-default branch without an open PR:
  gives `ahead_by`, `behind_by`, and commit author logins
- `repos/{r}/pulls?state=all&head=owner:branch` for each candidate of yours: a closed PR
  means the branch was abandoned deliberately, so it is counted and not listed

Measured: 8 repos, ~250 branches, 36 PRs of yours, 54 issues → ~310 calls, 50s with
6 workers. `--no-branches` drops that to ~60 calls, ~10s.

## Rate limits

Core REST 15,000/h on this token (5,000/h on a plain PAT). Search 30/min. A full run
uses ~2% of core. Not a concern unless run in a tight loop.

## False positives

- **Ready PR, no review, months old**: real state, but the user may have parked it. The
  script cannot know. The interpretation layer can override the Next pick.
- **Branch with your commits but no PR**: includes branches created by agents on your
  behalf (`claude/*`, `codex/*`) if the commits carry your author login. Real, but often
  disposable. Deletion is never done by this skill.
- **Approved but `mergeable_state: unknown`**: on very old PRs GitHub may not recompute
  within the retry window. Shown as `?`.

## False negatives

- **Branch authorship**: `compare` reports the GitHub login only when the commit email
  is linked to an account. Commits from an unlinked email (a CI bot, a misconfigured
  laptop) are attributed to nobody and the branch is skipped.
- **Commented-only involvement** (you left an issue comment on a PR but never a review):
  found by `involves:@me` on the laptop path, not found on the bound path.
- **Repos not attached to the web session** appear under Not scanned. Anything in them
  is invisible until `add_repo` is approved.
- **Repos pushed more than `--days` ago** are excluded from laptop auto-discovery.
  Stray branches in a dormant repo are missed unless the repo is passed explicitly.
- **Branch cap**: repos with more than `--max-branches` branches are truncated and a note
  is printed.

## "You can see these, Claude cannot"

**Verified 2026-09-02, and the obvious approach does not work.** `GET /user/installations`
(and every other `/user/installations/*` route) answers:

> You must authenticate with an access token authorized to a GitHub App in order to
> list installations — HTTP 403

That needs a GitHub App *user-to-server* token. `gh auth login` issues an OAuth token
(`gho_…`), which is the wrong token **type**, not a token missing a scope. Adding
`read:user` does not help; there is no scope that makes an OAuth token satisfy it.

So the Claude-visible repo list is supplied as a file:

```
~/.config/wip-github/claude-repos.txt      # or $WIP_GITHUB_CLAUDE_REPOS
```

One `owner/name` per line, `#` comments allowed. In a Claude Code web session, run the
`list_repos` tool of the claude-code-remote MCP server and save every `full_name` there.
The script then reports both directions:

- **You can see these, Claude cannot** — repos to attach with `add_repo`, or to check by
  hand. Measured on this account: 37 repos, including one holding a 552-day-old review
  request that the web session could not see at all.
- **Claude can see these, your token cannot** — usually means the file is stale.

Refresh the file whenever repo access changes; nothing expires it automatically. Without
the file the section is skipped and the readout says where to create it. `--no-coverage`
skips the check (it costs a few `user/repos` pages).

## Safety on client machines

- Read-only: no POST/PATCH/DELETE anywhere in the script.
- Auth is inherited from `gh`; the script never reads, stores, or prints a token. With
  the curl fallback the token is passed as a process argument, which is visible to
  other local processes for the duration of the call. Prefer `gh`.
- No repo names are hard-coded. Repo lists come from flags, env, a user config file, or
  the API.
- Output contains client repo names and PR titles. Treat the rendered readout like any
  other client-confidential note.
