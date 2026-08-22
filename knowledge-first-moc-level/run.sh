#!/bin/bash
# Runs the first-moc-level skill interactively via Claude Code.
# Unlike the -p/--dangerously-skip-permissions run.sh skills (which are
# unattended, one-shot), this skill stops to ask the human questions, so it
# stays a normal interactive session — permission prompts included.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

exec "$HOME/.local/bin/claude" -- "You are being launched to execute this skill file directly — it is your active task, not background context. Read it in full, then begin executing its Instructions section starting at Step 1, asking the human for each required parameter as it directs.

---

$(cat "$SKILL_FILE")"
