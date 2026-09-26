#!/bin/bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

# The skill's step 1 runs collect-checkpoints.py from the skill directory.
cd "$SKILL_DIR"

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

if [ -t 1 ]; then
  _spin() {
    local i=0 sp='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while true; do
      printf "\r${sp:i++%${#sp}:1} Reviewing CHECKPOINT.md files..."
      sleep 0.1
    done
  }
  _spin & _SPIN_PID=$!
  trap "kill $_SPIN_PID 2>/dev/null; printf '\r\033[K'" EXIT INT TERM
  "$CLAUDE_BIN" \
    --dangerously-skip-permissions \
    -p \
    -- "$(cat "$SKILL_FILE")"
else
  exec "$CLAUDE_BIN" \
    --dangerously-skip-permissions \
    -p \
    -- "$(cat "$SKILL_FILE")"
fi
