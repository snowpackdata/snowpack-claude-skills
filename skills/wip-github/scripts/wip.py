#!/usr/bin/env python3
"""
wip-github: deterministic readout of your open GitHub work.

Collects, for the authenticated user, across every repo reachable:
  - open PRs you authored (draft vs ready), with merge/CI/review state
  - open PRs where your review is requested, or you reviewed/are assigned
  - open issues you created or are assigned
  - branches with commits you authored that have no open PR
  - repos that could not be scanned (no access in this session)

Read-only. Never writes to GitHub. Never prints tokens. No repos are hard-coded.

Auth/transport: `gh` CLI (preferred, uses your existing `gh auth`). If `gh` is
missing, falls back to curl with $GH_TOKEN / $GITHUB_TOKEN.

Discovery: tries the cross-account search API first. Where that is blocked
(Claude Code on the web binds sessions to attached repos), it scans repo by
repo. Repo list sources, first match wins:
  --repos a/b,c/d   |   $WIP_GITHUB_REPOS   |   ~/.config/wip-github/repos.txt
  |   GET /user/repos (only works with an unrestricted token)

Usage:
  wip.py                      # markdown to stdout
  wip.py --json               # machine-readable
  wip.py --repos owner/a,owner/b --days 120
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.github.com"
UA = "wip-github/1.0"
NOW = datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# transport
# --------------------------------------------------------------------------- #
class ApiError(Exception):
    def __init__(self, status: int, message: str, path: str):
        super().__init__(f"HTTP {status} on {path}: {message}")
        self.status, self.message, self.path = status, message, path


class Transport:
    def __init__(self) -> None:
        self.mode = "gh" if shutil.which("gh") else "curl"
        if self.mode == "curl" and not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
            sys.exit("wip-github: need `gh` on PATH or GH_TOKEN/GITHUB_TOKEN set")
        self.calls = 0
        self.retries = 2
        self.backoff = 1.5

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def get(self, path: str, _attempt: int = 0):
        """GET an API path (relative, may include query). Returns parsed JSON.

        Retries transient failures (5xx, secondary rate limits) with fixed backoff
        so a flaky call cannot silently drop a repo from the readout.
        """
        self.calls += 1
        if self.mode == "gh":
            proc = subprocess.run(
                ["gh", "api", "--include", "-H", "Accept: application/vnd.github+json", path],
                capture_output=True, text=True,
            )
            raw = proc.stdout
        else:
            tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            proc = subprocess.run(
                ["curl", "-sS", "-i", "-H", f"Authorization: Bearer {tok}",
                 "-H", "Accept: application/vnd.github+json", "-H", f"User-Agent: {UA}",
                 f"{API}/{path}"],
                capture_output=True, text=True,
            )
            raw = proc.stdout
        # split headers/body (handle possible 1xx continuation blocks)
        status, body = 0, ""
        chunks = raw.split("\r\n\r\n") if "\r\n\r\n" in raw else raw.split("\n\n")
        for i, chunk in enumerate(chunks):
            m = re.match(r"HTTP/\S+\s+(\d{3})", chunk)
            if m:
                status = int(m.group(1))
                body = "\n\n".join(chunks[i + 1:])
            else:
                body = chunk if i == len(chunks) - 1 else body
        if status == 0 and proc.returncode != 0:
            if _attempt < self.retries:
                time.sleep(self.backoff * (_attempt + 1))
                return self.get(path, _attempt + 1)
            raise ApiError(0, (proc.stderr or raw).strip()[:300], path)
        try:
            data = json.loads(body) if body.strip() else None
        except json.JSONDecodeError:
            data = None
        if status >= 400:
            msg = (data or {}).get("message", body.strip()[:300]) if isinstance(data, dict) else body.strip()[:300]
            transient = status in self.RETRY_STATUS or (status == 403 and "rate limit" in msg.lower())
            if transient and _attempt < self.retries:
                time.sleep(self.backoff * (_attempt + 1))
                return self.get(path, _attempt + 1)
            raise ApiError(status, msg, path)
        return data

    def get_all(self, path: str, cap: int = 300):
        """Paginate a list endpoint (per_page=100) up to `cap` items.

        Sets self.truncated when the cap cut the result short, so callers can
        fall back rather than silently work from a partial list.
        """
        self.truncated = False
        out, page = [], 1
        sep = "&" if "?" in path else "?"
        while len(out) < cap:
            chunk = self.get(f"{path}{sep}per_page=100&page={page}")
            if not isinstance(chunk, list):
                break
            out.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1
        else:
            self.truncated = True
        return out[:cap]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def age_days(iso: str | None) -> int | None:
    if not iso:
        return None
    return (NOW - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days


def repo_of(item: dict) -> str:
    """Owner/name from a search result or PR object."""
    if "repository_url" in item:
        return item["repository_url"].split("/repos/")[-1]
    return item["base"]["repo"]["full_name"]


def is_bound_error(e: ApiError) -> bool:
    return e.status == 403 and ("bound to their configured repositories" in e.message
                                or "not enabled for this session" in e.message)


# --------------------------------------------------------------------------- #
# collection
# --------------------------------------------------------------------------- #
class Collector:
    def __init__(self, t: Transport, me: str, days: int, workers: int):
        self.t, self.me, self.days, self.workers = t, me, days, workers
        self.unreachable: dict[str, str] = {}   # repo -> reason
        self.notes: list[str] = []

    # ---- PR shaping -------------------------------------------------------
    def shape_pr(self, pr: dict) -> dict:
        repo = repo_of(pr)
        return {
            "repo": repo,
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["html_url"],
            "author": pr["user"]["login"],
            "draft": bool(pr.get("draft")),
            "updated_days": age_days(pr.get("updated_at")),
            "created_days": age_days(pr.get("created_at")),
            "head": (pr.get("head") or {}).get("ref"),
            "requested_reviewers": [u["login"] for u in pr.get("requested_reviewers", [])],
            "assignees": [u["login"] for u in pr.get("assignees", [])],
        }

    def enrich_pr(self, p: dict) -> dict:
        """Add mergeable_state + review decision. 2 calls."""
        try:
            full = self.t.get(f"repos/{p['repo']}/pulls/{p['number']}")
            # GitHub computes mergeability lazily: first GET often says "unknown". Re-ask briefly.
            for _ in range(2):
                if full.get("mergeable") is not None or full.get("mergeable_state") != "unknown":
                    break
                time.sleep(1.5)
                full = self.t.get(f"repos/{p['repo']}/pulls/{p['number']}")
            p["mergeable_state"] = full.get("mergeable_state")  # clean|dirty|blocked|unstable|behind|unknown
            p["head"] = full["head"]["ref"]
            p["requested_reviewers"] = [u["login"] for u in full.get("requested_reviewers", [])]
            reviews = self.t.get_all(f"repos/{p['repo']}/pulls/{p['number']}/reviews", cap=200)
            latest: dict[str, str] = {}
            for r in reviews:  # chronological; last state per reviewer wins
                if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED"):
                    latest[r["user"]["login"]] = r["state"]
            latest.pop(p["author"], None)
            states = set(latest.values())
            p["review"] = ("changes_requested" if "CHANGES_REQUESTED" in states
                           else "approved" if "APPROVED" in states
                           else "commented" if latest else "none")
            p["reviewers"] = sorted(latest)
        except ApiError as e:
            p["mergeable_state"], p["review"] = "unknown", "unknown"
            p["enrich_error"] = e.message[:120]
        return p

    # ---- fast path: search API -------------------------------------------
    def via_search(self) -> dict | None:
        q = lambda s: self.t.get(f"search/issues?q={s}&per_page=100")  # noqa: E731
        try:
            mine = q("is:pr+is:open+author:@me")
        except ApiError as e:
            if is_bound_error(e) or e.status in (403, 422):
                return None
            raise
        review_req = q("is:pr+is:open+review-requested:@me")
        involved = q("is:pr+is:open+involves:@me+-author:@me")
        issues_mine = q("is:issue+is:open+author:@me")
        issues_assigned = q("is:issue+is:open+assignee:@me+-author:@me")
        for name, r in (("mine", mine), ("review", review_req), ("involved", involved)):
            if r.get("incomplete_results"):
                self.notes.append(f"search '{name}' returned incomplete results")
        # involves:@me overlaps review-requested; a PR must appear in exactly one bucket
        claimed = {(repo_of(i), i["number"]) for i in mine["items"] + review_req["items"]}
        return {
            "mine": [self.shape_pr(i) for i in mine["items"]],
            "review_requested": [self.shape_pr(i) for i in review_req["items"]],
            "involved": [self.shape_pr(i) for i in involved["items"]
                         if (repo_of(i), i["number"]) not in claimed],
            "issues_mine": [self.shape_issue(i) for i in issues_mine["items"]],
            "issues_assigned": [self.shape_issue(i) for i in issues_assigned["items"]],
        }

    def shape_issue(self, i: dict) -> dict:
        return {
            "repo": repo_of(i), "number": i["number"], "title": i["title"], "url": i["html_url"],
            "updated_days": age_days(i.get("updated_at")), "assignees": [a["login"] for a in i.get("assignees", [])],
            "labels": [l["name"] for l in i.get("labels", [])],
        }

    # ---- fallback path: per-repo REST -------------------------------------
    def scan_repo_prs_issues(self, repo: str) -> dict:
        out = {"mine": [], "review_requested": [], "involved": [], "issues_mine": [], "issues_assigned": [],
               "ok": True}
        try:
            prs = self.t.get_all(f"repos/{repo}/pulls?state=open", cap=200)
        except ApiError as e:
            self.unreachable[repo] = f"HTTP {e.status}: {e.message[:90]}"
            out["ok"] = False
            return out
        for pr in prs:
            pr.setdefault("base", {"repo": {"full_name": repo}})
            p = self.shape_pr(pr)
            if p["author"] == self.me:
                out["mine"].append(p)
            elif self.me in p["requested_reviewers"]:
                out["review_requested"].append(p)
            elif self.me in p["assignees"]:
                out["involved"].append(p)
            else:
                # did I review it? (one call per foreign open PR)
                try:
                    reviews = self.t.get_all(f"repos/{repo}/pulls/{p['number']}/reviews", cap=100)
                    if any(r["user"]["login"] == self.me for r in reviews):
                        out["involved"].append(p)
                except ApiError:
                    pass
        try:
            for i in self.t.get_all(f"repos/{repo}/issues?state=open&creator={self.me}", cap=200):
                if "pull_request" not in i:
                    out["issues_mine"].append(self.shape_issue(i))
            for i in self.t.get_all(f"repos/{repo}/issues?state=open&assignee={self.me}", cap=200):
                if "pull_request" not in i and i["user"]["login"] != self.me:
                    out["issues_assigned"].append(self.shape_issue(i))
        except ApiError as e:
            self.notes.append(f"{repo}: issues not readable ({e.status})")
        return out

    # ---- branches (always per-repo; no search API for refs) --------------
    def branch_pr_index(self, repo: str) -> tuple[dict, bool]:
        """head-ref -> {'open'|'merged'|'closed'} for every PR in the repo.

        One paginated fetch replaces a per-branch PR lookup. Returns (index,
        complete); when incomplete the caller falls back to a per-branch query
        rather than trusting a partial index.
        """
        index: dict[str, set[str]] = {}
        try:
            prs = self.t.get_all(f"repos/{repo}/pulls?state=all", cap=500)
            complete = not self.t.truncated
        except ApiError:
            return {}, False
        for pr in prs:
            ref = (pr.get("head") or {}).get("ref")
            if not ref:
                continue
            state = ("open" if pr["state"] == "open"
                     else "merged" if pr.get("merged_at") else "closed")
            index.setdefault(ref, set()).add(state)
        return index, complete

    def scan_repo_branches(self, repo: str, max_branches: int) -> dict:
        res = {"stray": [], "merged_count": 0, "closed_pr_count": 0, "skipped": 0}
        try:
            meta = self.t.get(f"repos/{repo}")
            default = meta["default_branch"]
            branches = self.t.get_all(f"repos/{repo}/branches", cap=max_branches + 1)
        except ApiError as e:
            if repo not in self.unreachable:
                self.unreachable[repo] = f"HTTP {e.status}: {e.message[:90]}"
            return res
        if len(branches) > max_branches:
            res["skipped"] = len(branches) - max_branches
            branches = branches[:max_branches]

        index, complete = self.branch_pr_index(repo)
        owner = repo.split("/")[0]

        def pr_states(ref: str) -> set[str]:
            if ref in index or complete:
                return index.get(ref, set())
            try:  # index was truncated and this ref was not in it
                prs = self.t.get(f"repos/{repo}/pulls?state=all&head={owner}:{ref}&per_page=10")
            except ApiError:
                return set()
            return {("open" if p["state"] == "open"
                     else "merged" if p.get("merged_at") else "closed") for p in prs}

        cands = [b["name"] for b in branches if b["name"] != default]

        def classify(name: str):
            states = pr_states(name)
            if "open" in states:
                return None  # already surfaced as a PR
            try:
                c = self.t.get(f"repos/{repo}/compare/{default}...{name}?per_page=50")
            except ApiError:
                return None
            commits = c.get("commits", [])
            authors = {(cm.get("author") or {}).get("login") for cm in commits}
            authors.discard(None)
            if c.get("ahead_by", 0) == 0:
                return ("merged", None) if (self.me in authors or not authors) else None
            if self.me not in authors:
                return None
            if states:
                return ("closed_pr", None)
            return ("stray", {
                "repo": repo, "branch": name, "ahead": c.get("ahead_by", 0),
                "behind": c.get("behind_by", 0), "authors": sorted(authors),
                "updated_days": age_days(commits[-1]["commit"]["committer"]["date"] if commits else None),
                "url": f"https://github.com/{repo}/tree/{name}",
            })

        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            for r in ex.map(classify, cands):
                if r is None:
                    continue
                kind, payload = r
                if kind == "merged":
                    res["merged_count"] += 1
                elif kind == "closed_pr":
                    res["closed_pr_count"] += 1
                else:
                    res["stray"].append(payload)
        return res

    # ---- coverage: repos you can see vs repos Claude can see --------------
    def coverage_gap(self, my_repos: list[str]) -> dict:
        """Diff every repo you can reach against the repos Claude has access to.

        There is no user-token API for this: GET /user/installations requires a
        GitHub App user-to-server token, which `gh auth login` never issues (it is
        the wrong token type, not a missing scope). So the Claude-visible list is
        supplied as a file, which a Claude Code web session can write in one step:
            claude-repos.txt  <- one owner/name per line, from the list_repos tool
        """
        gap = {"checked": False, "you_only": [], "claude_only": [], "reason": None,
               "source": None}
        path = Path(os.environ.get("WIP_GITHUB_CLAUDE_REPOS")
                    or Path.home() / ".config" / "wip-github" / "claude-repos.txt")
        if not path.exists():
            gap["reason"] = (f"no Claude repo list at {path} — in a Claude Code web session, "
                             "run the list_repos tool and save each full_name there")
            return gap
        claude = {l.strip() for l in path.read_text().splitlines()
                  if l.strip() and not l.startswith("#")}
        if not claude:
            gap["reason"] = f"{path} is empty"
            return gap
        mine = set(my_repos)
        gap["checked"] = True
        gap["source"] = str(path)
        gap["you_only"] = sorted(mine - claude)
        gap["claude_only"] = sorted(claude - mine)
        return gap

    def all_my_repos(self) -> list[str]:
        """Every non-archived repo the token can reach, ignoring recency."""
        try:
            repos = self.t.get_all(
                "user/repos?affiliation=owner,collaborator,organization_member", cap=800)
        except ApiError:
            return []
        return [r["full_name"] for r in repos if not r.get("archived")]


# --------------------------------------------------------------------------- #
# repo discovery
# --------------------------------------------------------------------------- #
def discover_repos(t: Transport, args, days: int) -> tuple[list[str], str]:
    if args.repos:
        return [r.strip() for r in args.repos.split(",") if r.strip()], "--repos"
    env = os.environ.get("WIP_GITHUB_REPOS")
    if env:
        return [r.strip() for r in env.split(",") if r.strip()], "$WIP_GITHUB_REPOS"
    cfg = Path.home() / ".config" / "wip-github" / "repos.txt"
    if cfg.exists():
        lines = [l.strip() for l in cfg.read_text().splitlines()]
        return [l for l in lines if l and not l.startswith("#")], str(cfg)
    try:
        repos = t.get_all("user/repos?affiliation=owner,collaborator,organization_member&sort=pushed", cap=400)
    except ApiError as e:
        return [], f"none (user/repos: HTTP {e.status})"
    cutoff = NOW - timedelta(days=days)
    keep = [r["full_name"] for r in repos
            if not r.get("archived") and datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) >= cutoff]
    return keep, f"user/repos (pushed within {days}d)"


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #
def pick_next(d: dict) -> dict | None:
    """Deterministic 'do this first'. Returns {reason, item}."""
    mine = d["prs"]["mine"]
    ready = [p for p in mine if not p["draft"]]
    drafts = [p for p in mine if p["draft"]]
    rules = [
        ("changes requested on your PR", [p for p in ready if p.get("review") == "changes_requested"]),
        ("your review is requested", d["prs"]["review_requested"]),
        ("your PR has merge conflicts", [p for p in ready if p.get("mergeable_state") == "dirty"]),
        ("your PR has failing checks", [p for p in ready if p.get("mergeable_state") == "unstable"]),
        ("approved and clean: merge it", [p for p in ready if p.get("review") == "approved" and p.get("mergeable_state") == "clean"]),
        ("ready PR with no review yet: ask for one", [p for p in ready if p.get("review") == "none"]),
        ("oldest ready PR", ready),
        ("oldest draft: finish or close", drafts),
        ("stalest branch without a PR", d["branches"]["stray"]),
        ("oldest issue you opened", d["issues"]["mine"]),
    ]
    for reason, items in rules:
        if items:
            return {"reason": reason, "item": order(items)[0]}
    return None


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
STATE_ICON = {"clean": "clean", "dirty": "CONFLICT", "unstable": "CI failing", "blocked": "blocked",
              "behind": "behind base", "unknown": "?"}
REVIEW_ICON = {"changes_requested": "changes requested", "approved": "approved", "commented": "commented",
               "none": "no review", "unknown": "?"}


def order(items: list[dict]) -> list[dict]:
    """Stalest first, with a total order so runs are byte-identical."""
    return sorted(items, key=lambda x: (-(x.get("updated_days") or 0),
                                        x.get("repo", ""),
                                        x.get("number") or x.get("branch") or ""))


def short(repo: str) -> str:
    return repo.split("/", 1)[1]


def pr_line(p: dict, show_state=True) -> str:
    bits = [f"[{short(p['repo'])}#{p['number']} {p['title']}]({p['url']})"]
    if show_state:
        st = STATE_ICON.get(p.get("mergeable_state") or "unknown", "?")
        rv = REVIEW_ICON.get(p.get("review"), "?")
        bits.append(f"{st} · {rv}")
    else:
        bits.append(f"by {p['author']}")
    if p.get("updated_days") is not None:
        bits.append(f"{p['updated_days']}d")
    return "- " + " · ".join(bits)


def capped(lines: list[str], limit: int) -> list[str]:
    if limit and len(lines) > limit:
        return lines[:limit] + [f"- … +{len(lines) - limit} more (use --limit 0 for all)"]
    return lines


def render_md(d: dict, limit: int = 10) -> str:
    L: list[str] = []
    m = d["meta"]
    scope = (f"{m['repos_with_work']} repos with open work"
             if m["mode"].startswith("search")
             else f"{m['repos_with_work']} of {m['repos_scanned']} scanned repos have open work")
    L.append(f"## WIP · {m['user']} · {m['date']} · {scope} · {m['mode']}")
    nxt = d["next"]
    if nxt:
        it = nxt["item"]
        label = f"[{short(it['repo'])}#{it['number']}]({it['url']})" if "number" in it else f"[{short(it['repo'])}:{it['branch']}]({it['url']})"
        L.append(f"**Next:** {nxt['reason']} → {label}")
    else:
        L.append("**Next:** nothing open. Clean slate.")
    prs, iss, br = d["prs"], d["issues"], d["branches"]

    needs = [p for p in prs["mine"] if not p["draft"] and p.get("review") == "changes_requested"] \
        + prs["review_requested"]
    if needs:
        L.append(f"\n### Needs you ({len(needs)})")
        for p in order(needs):
            tag = "changes requested" if p["author"] == m["user"] else "review requested"
            L.append(pr_line(p, show_state=False).replace("- ", f"- {tag} · ", 1))

    ready = [p for p in prs["mine"] if not p["draft"]]
    drafts = [p for p in prs["mine"] if p["draft"]]
    L.append(f"\n### My PRs · ready ({len(ready)})")
    L += capped([pr_line(p) for p in order(ready)], limit * 2) or ["- none"]
    L.append(f"\n### My PRs · draft ({len(drafts)})")
    L += capped([pr_line(p) for p in order(drafts)], limit) or ["- none"]

    if prs["involved"]:
        L.append(f"\n### Watching · reviewed or assigned, not mine ({len(prs['involved'])})")
        L += capped([pr_line(p, show_state=False) for p in order(prs["involved"])], limit)

    stray = order(br["stray"])
    extras = []
    if br["merged_count"]:
        extras.append(f"{br['merged_count']} merged, deletable")
    if br["closed_pr_count"]:
        extras.append(f"{br['closed_pr_count']} with a closed PR, ignored")
    L.append(f"\n### Branches without a PR ({len(stray)})" + (" · " + " · ".join(extras) if extras else ""))
    L += capped([f"- [{short(b['repo'])}:{b['branch']}]({b['url']}) · +{b['ahead']}/-{b['behind']} · {b['updated_days']}d"
                 for b in stray], limit) or ["- none"]

    if iss["mine"] or iss["assigned"]:
        L.append(f"\n### Issues · opened by me ({len(iss['mine'])}) · assigned to me ({len(iss['assigned'])})")
        L += capped([f"- [{short(i['repo'])}#{i['number']} {i['title']}]({i['url']}) · {i['updated_days']}d"
                     for i in order(iss["mine"] + iss["assigned"])], limit)

    cov = d["coverage"]
    if cov["unreachable"]:
        L.append(f"\n### Not scanned · no access in this session ({len(cov['unreachable'])})")
        L += [f"- {r}" for r in sorted(cov["unreachable"])]
    if cov.get("you_only"):
        L.append(f"\n### You can see these, Claude cannot ({len(cov['you_only'])})")
        L += capped([f"- {r}" for r in cov["you_only"]], limit)
    if cov.get("claude_only"):
        L.append(f"\n### Claude can see these, your token cannot ({len(cov['claude_only'])})")
        L += capped([f"- {r}" for r in cov["claude_only"]], limit)
    if d["notes"]:
        L.append("\n<sub>" + " · ".join(d["notes"]) + "</sub>")
    L.append(f"\n<sub>{m['api_calls']} API calls · repos from {m['repo_source']}</sub>")
    return "\n".join(L)



# --------------------------------------------------------------------------- #
# offline self-test: exercises the pure logic with no network
# --------------------------------------------------------------------------- #
def selftest() -> int:
    fails: list[str] = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}\n    got  {got!r}\n    want {want!r}")

    pr = lambda repo, n, d, **kw: {  # noqa: E731
        "repo": repo, "number": n, "title": f"t{n}", "url": f"u{n}", "author": "me",
        "draft": False, "updated_days": d, "mergeable_state": "clean", "review": "none", **kw}

    # ordering is total and stalest-first; ties break by repo then number
    items = [pr("b/x", 2, 10), pr("a/x", 9, 10), pr("a/x", 1, 10), pr("a/x", 3, 99)]
    check("order", [(i["repo"], i["number"]) for i in order(items)],
          [("a/x", 3), ("a/x", 1), ("a/x", 9), ("b/x", 2)])
    check("order is stable under input shuffle",
          [i["number"] for i in order(list(reversed(items)))],
          [i["number"] for i in order(items)])
    check("order tolerates None age", [i["number"] for i in order([pr("a/x", 1, None), pr("a/x", 2, 5)])], [2, 1])

    # pick_next rule precedence
    base = {"prs": {"mine": [], "review_requested": [], "involved": []},
            "issues": {"mine": [], "assigned": []}, "branches": {"stray": []}}
    d = json.loads(json.dumps(base))
    d["prs"]["mine"] = [pr("a/x", 1, 5, review="changes_requested"), pr("a/x", 2, 900)]
    check("changes-requested wins over age", pick_next(d)["item"]["number"], 1)

    d = json.loads(json.dumps(base))
    d["prs"]["mine"] = [pr("a/x", 1, 5, review="changes_requested")]
    d["prs"]["review_requested"] = [pr("a/x", 2, 1, author="other")]
    check("changes-requested outranks review-requested", pick_next(d)["item"]["number"], 1)

    d = json.loads(json.dumps(base))
    d["prs"]["mine"] = [pr("a/x", 1, 5, mergeable_state="dirty"), pr("a/x", 2, 5, review="approved")]
    check("conflict outranks approved", pick_next(d)["item"]["number"], 1)

    d = json.loads(json.dumps(base))
    d["prs"]["mine"] = [pr("a/x", 1, 3, draft=True)]
    d["branches"]["stray"] = [{"repo": "a/x", "branch": "b", "updated_days": 900, "ahead": 1, "behind": 0, "url": "u"}]
    check("draft outranks stray branch", pick_next(d)["item"].get("number"), 1)

    check("empty state has no next", pick_next(json.loads(json.dumps(base))), None)

    # truncation
    check("capped keeps limit + marker", len(capped([f"- {i}" for i in range(20)], 5)), 6)
    check("capped counts remainder", capped([f"- {i}" for i in range(20)], 5)[-1],
          "- … +15 more (use --limit 0 for all)")
    check("capped no-ops under limit", capped(["- a"], 5), ["- a"])
    check("capped 0 disables", len(capped([f"- {i}" for i in range(20)], 0)), 20)

    # rendering: no crash on unknown/missing state, links well-formed
    d = json.loads(json.dumps(base))
    d["prs"]["mine"] = [pr("a/x", 1, 5, mergeable_state=None, review="unknown"), pr("a/x", 2, 6, draft=True)]
    d["meta"] = {"user": "me", "date": "d", "mode": "search API", "repos_scanned": 1,
                 "repos_with_work": 1, "repo_source": "test", "api_calls": 0, "transport": "gh"}
    d["branches"] = {"stray": [], "merged_count": 0, "closed_pr_count": 0, "skipped": 0}
    d["coverage"] = {"unreachable": [], "unreachable_detail": {}}
    d["notes"] = []
    d["next"] = pick_next(d)
    out = render_md(d, limit=10)
    check("renders unknown state", "?" in out, True)
    check("renders both buckets", ("ready (1)" in out and "draft (1)" in out), True)
    check("no literal None in output", "None" in out, False)

    # helpers
    check("repo_of from search item", repo_of({"repository_url": f"{API}/repos/o/r"}), "o/r")
    check("repo_of from pr object", repo_of({"base": {"repo": {"full_name": "o/r"}}}), "o/r")
    check("age_days None", age_days(None), None)
    check("bound error detected", is_bound_error(ApiError(403, "sessions are bound to their configured repositories", "p")), True)
    check("normal 403 is not a bound error", is_bound_error(ApiError(403, "Forbidden", "p")), False)

    if fails:
        print(f"selftest: {len(fails)} FAILED\n")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest: all checks passed")
    return 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--repos", help="comma-separated owner/name list to scan (overrides discovery)")
    ap.add_argument("--days", type=int, default=90, help="only auto-discover repos pushed within N days")
    ap.add_argument("--max-branches", type=int, default=80, help="branches inspected per repo")
    ap.add_argument("--no-branches", action="store_true", help="skip branch scan (much cheaper)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--selftest", action="store_true",
                    help="run offline logic checks (no network, no auth) and exit")
    ap.add_argument("--no-search", action="store_true",
                    help="skip the search API and scan repo by repo (what a bound session does)")
    ap.add_argument("--no-coverage", action="store_true", help="skip the Claude-access coverage diff")
    ap.add_argument("--limit", type=int, default=10, help="max lines per section in markdown (0 = all)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    t = Transport()
    try:
        me = t.get("user")["login"]
    except ApiError as e:
        sys.exit(f"wip-github: cannot resolve authenticated user ({e})")

    col = Collector(t, me, args.days, args.workers)
    repos, source = discover_repos(t, args, args.days)

    found = None if args.no_search else col.via_search()
    mode = "search API"
    explicit_scope = source in ("--repos", "$WIP_GITHUB_REPOS") or source.startswith("/")
    if found is None:
        mode = "per-repo scan" + ("" if args.no_search else " (search API blocked)")
        if not repos:
            sys.exit("wip-github: search API unavailable and no repo list. Pass --repos, set "
                     "$WIP_GITHUB_REPOS, or write ~/.config/wip-github/repos.txt")
        found = {"mine": [], "review_requested": [], "involved": [], "issues_mine": [], "issues_assigned": []}
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for repo, r in zip(repos, ex.map(col.scan_repo_prs_issues, repos)):
                if not r["ok"]:
                    continue
                for k in found:
                    found[k].extend(r[k])

    # An explicitly supplied repo list scopes the readout; the search API ignores it.
    if found is not None and explicit_scope and repos:
        allow = set(repos)
        for key in ("mine", "review_requested", "involved", "issues_mine", "issues_assigned"):
            found[key] = [i for i in found[key] if i["repo"] in allow]

    # enrich the PRs that matter (mine + review requested)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(col.enrich_pr, found["mine"] + found["review_requested"]))

    # branches
    branches = {"stray": [], "merged_count": 0, "closed_pr_count": 0, "skipped": 0}
    scan_targets = [r for r in repos if r not in col.unreachable]
    if not args.no_branches and scan_targets:
        for repo in scan_targets:
            r = col.scan_repo_branches(repo, args.max_branches)
            branches["stray"] += r["stray"]
            branches["merged_count"] += r["merged_count"]
            branches["closed_pr_count"] += r["closed_pr_count"]
            branches["skipped"] += r["skipped"]
    if branches["skipped"]:
        col.notes.append(f"{branches['skipped']} branches skipped (cap {args.max_branches}/repo)")

    coverage = {"unreachable": sorted(col.unreachable), "unreachable_detail": col.unreachable}
    if not args.no_coverage:
        reachable = col.all_my_repos() if mode == "search API" else repos
        coverage.update(col.coverage_gap(reachable or scan_targets))

    data = {
        "meta": {"user": me, "date": NOW.strftime("%Y-%m-%d %H:%MZ"), "mode": mode,
                 "repos_scanned": len(scan_targets),
                 "repos_with_work": len({i["repo"] for k in ("mine", "review_requested", "involved")
                                         for i in found[k]}
                                        | {i["repo"] for i in found["issues_mine"] + found["issues_assigned"]}
                                        | {b["repo"] for b in branches["stray"]}), "repo_source": source, "api_calls": t.calls,
                 "transport": t.mode},
        "prs": {"mine": found["mine"], "review_requested": found["review_requested"], "involved": found["involved"]},
        "issues": {"mine": found["issues_mine"], "assigned": found["issues_assigned"]},
        "branches": branches,
        "coverage": coverage,
        "notes": col.notes,
    }
    data["next"] = pick_next(data)
    data["meta"]["api_calls"] = t.calls
    print(json.dumps(data, indent=2) if args.json else render_md(data, args.limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
