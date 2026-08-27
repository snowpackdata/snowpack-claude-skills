# gather-context

Systematic context-gathering for an unfamiliar operational pipeline, built from [A
Taxonomy for Systematic Pipeline Context-Gathering](./references/taxonomy.md) (condensed
copy; the source is an internal Snowpack doc).

Consultants ramping up on an unfamiliar client pipeline can't get business and process
context fast enough — gathering it today is ad hoc detective work. This splits the
problem the way the taxonomy does: some context is mechanically recoverable (declared,
parseable), some requires querying a third-party tool instead of reading code, and some
can't be automated at all and needs a specific, narrow question to a person.

## Scope of this build

Targets compute/infra-heavy pipelines (e.g. Python scripts, JSON configs, dated-release
directory conventions) and the two orchestration shapes covered so far — dbt and Airflow
(see [`references/frameworks/`](./references/frameworks) for exactly what's covered per
framework, and how to add another).

Implements:
- **Execution-order extraction** — dbt manifest `depends_on` graphs and Airflow DAG task
  wiring (`>>`, `<<`, `set_downstream`/`set_upstream`, including list-branch fan-out),
  detected by content shape rather than filename, topologically sorted into an actual run
  order. A real cycle is flagged explicitly rather than silently mis-ordered. This is
  mechanically derived from dependency edges, not a docstring-based guess.
- **Declared-parse** — JSON configs, Python module docstrings/CLI args, and
  release/versioning conventions detected structurally rather than by one pipeline's
  naming: any directory whose children mostly match a known versioning scheme (ISO
  timestamps, dates, semver, git shas, or keyword/pointer-corroborated build numbers),
  plus any pointer symlink inside it under any name (`current`, `latest`, `stable`,
  `prod`, ...).
- **Disagreement detection** — same config key, different value, across non-versioned
  declared sources.
- **Freshness checks** — does the pointer symlink target the most recent sibling by that
  convention's own ordering (numeric-aware for semver/build numbers, not a naive string
  sort — `v9.0.0` correctly sorts before `v10.0.0`). Git-sha-named versions are flagged
  as unorderable by name alone rather than guessed at.
- **Backward-trace** — given consumer artifacts (dashboard queries, reverse-ETL configs,
  anything downstream), flag references to things nothing upstream declares. This is the
  direct fix for a real failure mode seen on a past client engagement: a forward-only
  scan of a clean pipeline gave false confidence while a downstream reverse-ETL sync
  silently depended on a field the pipeline's own tooling never touched.
- **Gap surfacing** — tribal/motivational/ownership candidates, handed to the skill to
  turn into a short confirm-or-correct list, not an open-ended interview.
- **Non-blocking fallback + local learnings capture** — when a pipeline's stack isn't
  covered by `scan.py` or `references/frameworks/`, the skill falls through to reading
  code directly instead of reporting a false-clean scan, and captures what it learns
  locally (gitignored, in the target repo) rather than blocking on a round-trip back
  here. See SKILL.md's "Capturing learnings" step.
- **Provenance-split reporting** — every finding in the output report, and any ERD/data-
  flow diagram built alongside it, is marked mechanical vs. inferred vs. unresolved gap.
  See [`references/erd-provenance.md`](./references/erd-provenance.md) for the diagram
  convention specifically.

Explicitly NOT implemented (see [`references/taxonomy.md`](./references/taxonomy.md)):
execution-based checks for emergent/silent-latent-defect complexity, and
parallel-authority diffing across two simultaneously-live systems. The skill states
plainly when it hasn't checked them rather than letting a clean scan imply it did.

## Use it

```
python3 scripts/scan.py declared <path>
python3 scripts/scan.py backward-trace <path> --consumers <file> [<file> ...]
```

Or just ask Claude to "gather context on this pipeline" — the `gather-context` skill
runs both, reads the output, filters false positives, and writes a structured report.

## Install

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill gather-context
```

Manual fallback (always works): `cp -r skills/gather-context ~/.claude/skills/`.

## Author

Audris (audris@snowpack-data.com)
