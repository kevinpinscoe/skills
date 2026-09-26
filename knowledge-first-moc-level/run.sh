#!/bin/bash
# Runs the first-moc-level skill interactively via Claude Code.
# Unlike the -p/--dangerously-skip-permissions run.sh skills (which are
# unattended, one-shot), this skill stops to ask the human questions, so it
# stays a normal interactive session — permission prompts included.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

resolve_claude() {
  if command -v claude >/dev/null 2>&1; then
    command -v claude
    return
  fi
  for candidate in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" \
                    "/mac-home/.local/bin/claude" \
                    "/opt/homebrew/bin/claude" "/usr/local/bin/claude"; do
    if [ -x "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done
  return 1
}

CLAUDE_BIN="$(resolve_claude)" || {
  echo "error: could not find the 'claude' CLI (checked PATH, \$HOME/.local/bin, /mac-home/.local/bin, and common install locations)" >&2
  exit 1
}

exec "$CLAUDE_BIN" -- "You are being launched to execute this skill file directly — it is your active task, not background context. Read it in full, then begin executing its Instructions section starting at Step 1, asking the human for each required parameter as it directs.

---

$(cat "$SKILL_FILE")"
