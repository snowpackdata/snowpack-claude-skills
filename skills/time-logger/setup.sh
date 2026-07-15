#!/usr/bin/env bash
# setup.sh — bootstrap directories and config files after cloning
# For full integration setup (Slack, Calendar, GitHub, Granola), open this
# repo in Claude Code and say "setup" — Claude will probe and configure everything.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPS="$SCRIPT_DIR/capabilities.yml"

# Determine repo path from capabilities.yml if it exists, otherwise use default
if [[ -f "$CAPS" ]]; then
  REPO_PATH=$(grep "repo_path:" "$CAPS" | sed "s/.*repo_path: *//" | sed "s|~|$HOME|g" | tr -d '"')
else
  REPO_PATH="$HOME/repos/time_logs"
fi

echo "Using repo path: $REPO_PATH"

# Create required data directories (gitignored)
mkdir -p "$REPO_PATH/raw/slack" "$REPO_PATH/raw/calendar" "$REPO_PATH/raw/claude"
mkdir -p "$REPO_PATH/raw/github" "$REPO_PATH/raw/granola"
mkdir -p "$REPO_PATH/time_logs"
echo "Created output directories"

# Bootstrap capabilities.yml from example template if not yet configured
if [[ ! -f "$CAPS" ]]; then
  cp "$SCRIPT_DIR/capabilities.example.yml" "$CAPS"
  echo "Created capabilities.yml from template"
else
  echo "capabilities.yml already exists"
fi

# Bootstrap user-preferences.md from example template if not yet created
PREFS="$REPO_PATH/user-preferences.md"
if [[ ! -f "$PREFS" ]]; then
  cp "$SCRIPT_DIR/user-preferences.example.md" "$PREFS"
  echo "Created user-preferences.md from template"
else
  echo "user-preferences.md already exists"
fi

echo
echo "Next step: open this repo in Claude Code and say 'setup' to configure"
echo "your integrations (Slack, GitHub, Google Calendar, Granola)."
