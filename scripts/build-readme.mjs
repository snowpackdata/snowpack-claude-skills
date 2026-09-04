#!/usr/bin/env node
// Regenerates the two skill tables in README.md — Production Ready and Ready
// for Review — from each skill's SKILL.md frontmatter. Tier comes from
// folder location only, matching validate-skills.mjs and
// build-codeowners.mjs, so there's exactly one source of truth instead of a
// table someone has to remember to hand-edit.
//
// The Description column pulls from `summary`, not `description` -- `description`
// stays long and trigger-phrase-rich for Claude Code's own skill-activation matching,
// while `summary` is a separate field validate-skills.mjs caps at 140 characters
// specifically so this table stays scannable.
//
// Only the content between each pair of markers is touched:
//   <!-- SKILLS-TABLE:PRODUCTION:START --> ... <!-- SKILLS-TABLE:PRODUCTION:END -->
//   <!-- SKILLS-TABLE:REVIEW:START -->     ... <!-- SKILLS-TABLE:REVIEW:END -->
// README.md must already contain both marker pairs.
//
// Run:          node scripts/build-readme.mjs
// CI check only: node scripts/build-readme.mjs --check   (exits 1 if the
//                committed README doesn't match what this script generates)

import { readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const README_PATH = "README.md";

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

function collectSkills(dir) {
  if (!existsSync(dir)) return [];
  const skills = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const skillMdPath = join(dir, entry.name, "SKILL.md");
    if (!existsSync(skillMdPath)) continue;
    const fm = parseFrontmatter(readFileSync(skillMdPath, "utf8")) || {};
    skills.push({ name: entry.name, path: join(dir, entry.name), fm });
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

function escapeCell(value) {
  return (value || "").replace(/\|/g, "\\|");
}

function buildProductionTable(skills) {
  if (!skills.length) return "_No skills are Production Ready yet._";
  const rows = skills.map(({ name, path, fm }) => {
    const link = `[\`${name}\`](./${path})`;
    // `summary`, not `description` -- description stays long and trigger-phrase-rich
    // for Claude Code's own skill-activation matching; summary is what's enforced
    // short (validate-skills.mjs) specifically so this table stays scannable.
    const summary = escapeCell(fm.summary) || "_missing summary_";
    const owner = escapeCell(fm.owner) || "_missing owner_";
    return `| ${link} | ${summary} | ${owner} |`;
  });
  return ["| Skill | Description | Owner |", "|---|---|---|", ...rows].join("\n");
}

function buildReviewTable(skills) {
  if (!skills.length) return "_No skills are Ready for Review yet._";
  const rows = skills.map(({ name, path, fm }) => {
    const link = `[\`${name}\`](./${path})`;
    const summary = escapeCell(fm.summary) || "_missing summary_";
    const notes = escapeCell(fm.notes);
    return `| ${link} | ${summary} | ${notes} |`;
  });
  return ["| Skill | Description | Notes |", "|---|---|---|", ...rows].join("\n");
}

function replaceBlock(readme, marker, content) {
  const start = `<!-- SKILLS-TABLE:${marker}:START -->`;
  const end = `<!-- SKILLS-TABLE:${marker}:END -->`;
  const startIdx = readme.indexOf(start);
  const endIdx = readme.indexOf(end);
  if (startIdx === -1 || endIdx === -1 || endIdx < startIdx) {
    throw new Error(`README.md is missing the ${marker} marker block (${start} / ${end})`);
  }
  return readme.slice(0, startIdx + start.length) + "\n" + content + "\n" + readme.slice(endIdx);
}

function main() {
  const check = process.argv.includes("--check");
  if (!existsSync(README_PATH)) {
    console.error(`${README_PATH} not found.`);
    process.exit(1);
  }

  const original = readFileSync(README_PATH, "utf8");
  let readme = original;

  const production = collectSkills("skills/production");
  const review = collectSkills("skills/review");

  readme = replaceBlock(readme, "PRODUCTION", buildProductionTable(production));
  readme = replaceBlock(readme, "REVIEW", buildReviewTable(review));

  if (check) {
    if (readme !== original) {
      console.error(
        "README.md skill tables are out of date — run `node scripts/build-readme.mjs` and commit the result."
      );
      process.exit(1);
    }
    console.log("README.md skill tables are up to date.");
    return;
  }

  if (readme !== original) {
    writeFileSync(README_PATH, readme);
    console.log("Wrote README.md.");
  } else {
    console.log("README.md already up to date.");
  }
}

main();
