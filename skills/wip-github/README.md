# wip-github

One-screen readout of every piece of GitHub work you have left open, across every repo
you and Claude can reach. No repos hard-coded. Read-only.

```bash
npx skills add snowpackdata/snowpack-claude-skills --skill wip-github
```

Then `/wip-github` in Claude Code. The script does all the GitHub calls; Claude adds one
sentence and one next action.

- [`SKILL.md`](./SKILL.md) is the skill definition.
- [`scripts/wip.py`](./scripts/wip.py) is the collector. Runs standalone too:
  `python3 scripts/wip.py --help`.
- [`references/api-surface.md`](./references/api-surface.md) documents what works on a
  laptop versus in a Claude Code web session, and the known false positives and negatives.
