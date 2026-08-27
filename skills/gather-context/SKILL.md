---
name: gather-context
description: Run systematic context-gathering against an operational pipeline — parse declared artifacts, backward-trace consumer dependencies, and surface tribal/motivational/ownership gaps as a confirm-or-correct list. Triggers on "gather pipeline context", "map this pipeline", "what's declared vs. tribal here", "run the context taxonomy on this repo", or when onboarding onto an unfamiliar client pipeline.
---

# Gather Context

Read [`references/taxonomy.md`](./references/taxonomy.md) before starting — it defines
the scope boundary, what the script does and doesn't judge, and the writing style for gap
questions. This skill is the judgment layer on top of `scripts/scan.py`, which does the
mechanical parsing. For framework-specific extraction detail (what dbt/Airflow shapes are
covered today, and what isn't), see [`references/frameworks/`](./references/frameworks/).

## Step 0 — locate this skill's own script

`scan.py` has to run regardless of the current working directory or how this skill was
installed. Resolve its path once, before step 2:

```bash
SKILL_DIR=""
for candidate in ~/.claude/skills/gather-context .claude/skills/gather-context; do
  if [ -f "$candidate/scripts/scan.py" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
SCAN="${SKILL_DIR:+$SKILL_DIR/}scripts/scan.py"
[ -z "$SKILL_DIR" ] && SCAN="scripts/scan.py"  # direct clone, running from skills/gather-context/ itself
```

Use `"$SCAN"` in place of `scripts/scan.py` in every invocation below.

## Scope check first

Confirm the target is something operational today, not something being designed. If
there's no operational reality to observe, say so and stop — that's a different exercise.

## Workflow

1. **Get the target path.** Ask for the repo/directory to scan if not given.

2. **Run the declared-artifact scan:**
   ```
   python3 "$SCAN" declared <path>
   ```

3. **Ask if there are known consumer artifacts** — dashboard exports, reverse-ETL
   configs, BI queries, anything downstream that reads from this pipeline but isn't part
   of its own codebase. If yes, run:
   ```
   python3 "$SCAN" backward-trace <path> --consumers <file> [<file> ...]
   ```
   If no consumer artifacts are available, say so explicitly in the final report — don't
   silently skip this section as if it came back clean. A pipeline with no backward-trace
   run has unknown externalized-dependency risk, not zero risk.

4. **Interpret the raw output — this is the part the script can't do:**
   - **Read `detected_stack` and `known_framework_detected` first, before anything
     else** — this is the mechanical fingerprint from `scan.py`'s stack-identification
     pass, and it decides which `references/frameworks/*.md` applies and whether an
     empty `declared_sequences` later means "nothing to report" or "uncovered." Report
     every `detected_stack` entry with its confidence (`high`/`medium`/`low`) plainly. A
     `low`- or `medium`-confidence `bespoke-scheduler` entry is a candidate worth reading,
     not a verdict — same treatment as `disagreements`/`undeclared_dependencies` below,
     never reported with the same certainty as a `high`-confidence `dbt`/`airflow`
     marker. `known_framework_detected` reflects only real, named markers
     (`dbt_project.yml`, `airflow.cfg`/`dags/`, a Dagster/Prefect import+decorator pair)
     — a bespoke-scheduler guess never sets it true, by design.
   - For each `declared_sequences` entry, report the `execution_order` as fact — it's
     derived from real dependency edges (dbt's `depends_on`, Airflow's `>>`/`<<`/
     `set_downstream`), not inferred from prose. If `cycle_detected` is true, say so
     plainly and show the edges rather than picking an order. If a module's docstring
     claims a schedule/trigger (e.g. "runs nightly via the DAG") cross-check it against
     any matching `declared_sequences` entry — that's a disagreement worth surfacing if
     the DAG file doesn't actually wire what the docstring claims.
   - For each `disagreements` entry, state both values plainly; don't guess which one is
     right.
   - For each `cross_reference_candidates` group, actually read both docstrings/modules
     and judge whether they describe the same process. Only report it as a real conflict
     if they do — the script grouped them by name similarity alone, it didn't check
     meaning.
   - For each `undeclared_dependencies` hit, sanity-check it isn't a false positive (a
     common word or generic filename that happens to match). Drop the noise; keep what
     looks like a genuine external reference nothing upstream declares.
   - For each `gap_candidates` entry (tribal/motivational/ownership), write one short,
     specific question per gap — not "tell me about this pipeline." Use the pattern:
     here's what we found, here's what's missing, here's what we need from you to close
     it.
   - For `release_convention` freshness flags, state plainly what the pointer (whatever
     it's named — `current`, `latest`, `stable`, `prod`) points to vs. the latest version
     by the detected convention, and ask whether that's intentional. If the entry has a
     `note` instead of a `latest_by_convention` (e.g. git-sha-named versions), say
     explicitly that freshness can't be determined from names alone — don't guess.

5. **Read `known_framework_detected` — it's the mechanical trigger for whether an empty
   `declared_sequences` means "uncovered," "known but no graph available," or "genuinely
   nothing here." Never let a thin result read as "nothing to report" without checking
   which of these three it actually is:**
   - **`known_framework_detected: false`** — no dbt/Airflow/Dagster/Prefect marker was
     found anywhere in the tree (at most a low/medium-confidence `bespoke-scheduler` guess
     in `detected_stack`). An empty `declared_sequences` here means the stack is
     **uncovered**, not that the pipeline has no execution order — this is the case a
     bespoke Go scheduler, Temporal, or any other genuinely unsupported stack falls into.
     Fall through to reading the relevant code/config directly by hand.
   - **`known_framework_detected: true`, but `declared_sequences` is still empty** — a
     real framework marker was found, but this pass has no mechanical graph for it: either
     a `dbt_project.yml` with no committed `manifest.json` (the project exists, nothing
     compiled it), or a Dagster/Prefect import was detected but this pass only checks
     presence — it doesn't extract an asset/flow graph (see `references/frameworks/`).
     Say plainly which of these two it is; this is narrower than "uncovered," since the
     framework itself is known, there's just no graph available from what's in the repo
     today.
   - **Neither of the above** — `declared_sequences` has real entries (report as usual),
     or `known_framework_detected` is `false` and a careful look confirms this pipeline
     genuinely has no scheduler/DAG of any kind (rare; say so plainly).

   In either of the first two cases, mark anything recovered by hand-reading as
   **inferred**, not mechanical, in the report (see the provenance summary in the output
   template) — a completed, lower-confidence finding, never a blocker.

6. **Capture what you learn from that fallback reading, locally.** The moment you
   hand-recover something reusable against an undocumented stack — a scheduler
   convention, a write-path shape, a naming pattern — write it down immediately, at zero
   cost to whoever's running this:
   - Append it to `.pipeline-context-learnings/<slug>.md` in the *target* repo. Never
     commit this alongside the client's own code — before the first write in a given
     target repo, check its `.gitignore` for `.pipeline-context-learnings/`; if it's
     missing, add the entry and say out loud that you did. A learnings file must never
     land silently in a client's diff.
   - On a fresh run against a repo that already has `.pipeline-context-learnings/`
     content, surface "N uncontributed learnings from past runs here" as a passive
     nudge in the report — never a gate on finishing the current one.
   - Promoting a learning into a maintained `references/frameworks/*.md` entry is a
     separate, later, optional step: open a PR against wherever this skill itself is
     maintained, once someone has time to review it. Never require that round-trip for
     the learning to exist or to be picked up on the next run against the same repo — and
     never promote it without a pass to strip anything client-identifying (real names,
     table/field names, business logic specifics) first, since a promoted reference is
     shared across every future engagement this skill runs against.

7. **Scale the report to what was actually found.** Zero disagreements and zero
   undeclared dependencies means a short report. Several of either means don't compress
   them into one line each — this is where the real risk is.

8. **Write the output doc** (structured, not conversational) using the template below.
   Name every category the tool didn't check (execution-order, silent-defect,
   parallel-authority) explicitly rather than letting their absence read as "checked and
   clean."

## Output template

Write `pipeline-context-report.md` in the target repo (or wherever the user asks):

```markdown
# Pipeline Context Report — <target>

## Provenance summary
<one line, e.g. "3 findings mechanically derived (scan.py) · 5 findings inferred (direct
code/doc reading) · 2 gaps unresolved". Every section below should trace back to one of
these buckets -- never let an inferred finding read with the same certainty as a
mechanical one. See references/erd-provenance.md if a diagram is also produced --
same principle, applied to edges instead of bullets.>

## Detected stack
<one entry per detected_stack item: signal, category, confidence, evidence path -- report
low/medium-confidence bespoke-scheduler entries as candidates to verify, not verdicts>
<state known_framework_detected plainly (true/false) -- it decides how to read an empty
Execution order section below>

## Execution order (mechanically derived from dbt manifest / Airflow DAG wiring)
<one entry per declared_sequences item: source, kind, and the execution_order>
<if cycle_detected: true, say so explicitly and show the edges -- do not guess an order>
<if declared_sequences is empty and known_framework_detected is false: say so explicitly
-- this means "uncovered," not "no order exists" -- and report what fallback reading
(step 5) found instead, marked inferred>
<if declared_sequences is empty and known_framework_detected is true: say which framework
was found and why no graph is available (no committed manifest, or a framework this pass
only detects the presence of and doesn't extract -- see references/frameworks/) --
narrower than "uncovered," but still no mechanical order to report>
<if declared_sequences is empty, known_framework_detected is false, and a careful look
confirms there's genuinely no scheduler/DAG at all (rare): "No dbt manifest or DAG wiring
found -- process order is not declared anywhere parseable; treat it as tribal knowledge
(see gaps below) rather than assuming there's none.">

## Declared, and disagreeing
<one entry per real disagreement, both values shown, no guess at which is right>

## Externalized dependencies found (backward-trace)
<one entry per confirmed undeclared_dependency, after filtering false positives>
<or: "No consumer artifacts were available to trace — externalized-dependency risk is unknown, not clean.">

## Freshness
<current-vs-latest-dated-release flags, or "no dated-release convention found">

## ERD / data-flow diagram
<if one was built this run: link it and confirm it follows the provenance convention in
references/erd-provenance.md (solid vs. dashed edges, black-box nodes, a provenance-count
banner). If none was built: "No ERD produced this run -- see references/erd-provenance.md
if one becomes worth building.">

## Gaps needing a person to close (confirm or correct)
- [ ] <specific question 1>
- [ ] <specific question 2>

## Uncontributed learnings
<"N entries in .pipeline-context-learnings/ from this or past runs, not yet promoted to
references/frameworks/" or "none">

## Not checked by this pass
- Execution-order / silent-latent-defect complexity (would need a dark-launch run against shadowed destinations)
- Parallel-authority complexity (needs simultaneous access to more than one live system)
```

## Notes

- The script's `disagreements` and `undeclared_dependencies` are candidates, not
  verdicts — always read them before writing them into the report.
- If the target has no detectable versioning convention at all, `release_convention`
  will be empty — that's a fine and expected result for a non-versioned pipeline, not a
  gap.
- An empty `.pipeline-context-learnings/` is the common, expected case — not a sign
  anything's wrong.
- `detected_stack` fingerprints language/orchestration markers structurally (manifests,
  imports, a corroborated scheduler-filename heuristic) — it does not cover managed cloud
  schedulers declared only in IaC (a Terraform `google_cloud_scheduler_job`, a
  `serverless.yml` schedule trigger) or SaaS/reverse-ETL integrations referenced only by
  name in config/env vars. Say so if either seems relevant to the target; don't let their
  absence from `detected_stack` read as "checked and not present."

## Install

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill gather-context
```

Manual fallback (always works): `cp -r skills/gather-context ~/.claude/skills/`.
