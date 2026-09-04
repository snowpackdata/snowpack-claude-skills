#!/usr/bin/env node
// v2 — supersedes an earlier draft that checked a `status:` frontmatter
// field. Tier now comes from folder location only, matching
// build-readme.mjs and build-codeowners.mjs, so there's exactly one source
// of truth instead of a field that could drift out of sync with reality.
//
// Layout checked:
//   skills/production/{name}/SKILL.md  -> production tier
//   skills/review/{name}/SKILL.md      -> review tier
//   skills/{name}/SKILL.md             -> not yet promoted (name+description
//                                          only; no README/owner requirement)
//   archive/**                          -> not checked at all
//
// Run: node scripts/validate-skills.mjs

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const SKILLS_DIR = "skills";

function parseFrontmatter(text) {
  const match = text.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const fm = {};
  for (const line of match[1].split("\n")) {
    const m = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (m) fm[m[1]] = m[2].trim();
  }
  return fm;
}

function collectSkillDirs() {
  const found = [];
  if (!existsSync(SKILLS_DIR)) return found;

  for (const entry of readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;

    if (entry.name === "production" || entry.name === "review") {
      const tier = entry.name;
      const subDir = join(SKILLS_DIR, entry.name);
      for (const sub of readdirSync(subDir, { withFileTypes: true })) {
        if (sub.isDirectory()) {
          found.push({ tier, name: sub.name, path: join(subDir, sub.name) });
        }
      }
      continue;
    }

    found.push({ tier: "unpromoted", name: entry.name, path: join(SKILLS_DIR, entry.name) });
  }
  return found;
}

function main() {
  const readme = existsSync("README.md") ? readFileSync("README.md", "utf8") : "";
  const errors = [];
  const skills = collectSkillDirs();

  for (const { tier, name, path } of skills) {
    const skillMdPath = join(path, "SKILL.md");
    if (!existsSync(skillMdPath)) {
      errors.push(`${path}: missing SKILL.md`);
      continue;
    }

    const fm = parseFrontmatter(readFileSync(skillMdPath, "utf8"));
    if (!fm) {
      errors.push(`${path}: SKILL.md has no YAML frontmatter block`);
      continue;
    }
    if (!fm.name) errors.push(`${path}: frontmatter is missing "name"`);
    if (!fm.description) errors.push(`${path}: frontmatter is missing "description"`);

    if (tier === "production" && !fm.owner) {
      errors.push(`${path}: production skills need an "owner" in frontmatter`);
    }
    if ((tier === "production" || tier === "review") && !readme.includes(`skills/${tier}/${name}`)) {
      errors.push(`${path}: not linked from README.md (expected a link to skills/${tier}/${name})`);
    }
  }

  if (errors.length) {
    console.error("Skill validation failed:\n" + errors.map((e) => `  - ${e}`).join("\n"));
    process.exit(1);
  }
  console.log(`All skills valid (${skills.length} checked).`);
}

main();
