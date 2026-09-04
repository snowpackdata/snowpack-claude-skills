## What does this PR do?

- [ ] Promote a skill: `skills/{name}/` → `skills/review/{name}/` (Ready for Review)
- [ ] Promote a skill: `skills/review/{name}/` → `skills/production/{name}/` (Production Ready)
- [ ] Edit a skill already in `skills/review/` or `skills/production/`
- [ ] Archive a skill: `skills/review/{name}/` or `skills/production/{name}/` → `archive/{name}/`
- [ ] Repo tooling / docs only — no skill tier change

<!--
In Development work stays on a wip/{skill-name} branch and never opens a PR — it's not
tracked here. See AGENTS.md and the Publishing & Maintaining Skills doc for the full
framework: https://app.notion.com/p/3d1d5d2202f98135847ae91710530c20
-->

## Checklist

- [ ] `SKILL.md` frontmatter has `name` and `description`.
- [ ] If this skill is (or is becoming) Production Ready: `owner:` is set to a real
      `@handle` or `@org/team`, and that person/team is willing to be the enforced
      reviewer (`build-codeowners.mjs` turns this into a CODEOWNERS entry).
- [ ] If this skill is in `skills/review/`: `notes:` reflects its current state
      (blank is fine).
- [ ] README tables are regenerated and committed: `node scripts/build-readme.mjs`.
- [ ] No credentials, production write access, or client data in examples.
- [ ] For a new Production Ready skill: confirm someone besides the author has used it
      successfully.
- [ ] Get at least one other person to skim this PR — not a blocking approval below
      Production tier, but a second pair of eyes.

## What changed and why

<!-- Describe the change. Link any relevant context (Notion, Linear, Slack). -->
