#!/bin/bash
# Runs the read-my-gmail-for-tldr-articles skill non-interactively via Claude Code.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

exec "$HOME/.local/bin/claude" \
  --dangerously-skip-permissions \
  -p \
  -- "$(cat "$SKILL_FILE")"
