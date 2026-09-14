#!/bin/bash
# Runs this skill interactively via Claude Code.
# This skill asks the human for the requested change, confirms a YouTrack
# issue, and stops before merging — it stays a normal interactive session,
# permission prompts included, never unattended.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

exec "$HOME/.local/bin/claude" -- "You are being launched to execute this skill file directly — it is your active task, not background context. Read it in full, then begin executing its Instructions section starting at Step 1, asking the human for each required parameter as it directs.

---

$(cat "$SKILL_FILE")"
