#!/bin/bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

if [ -t 1 ]; then
  _spin() {
    local i=0 sp='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while true; do
      printf "\r${sp:i++%${#sp}:1} Processing TLDR emails..."
      sleep 0.1
    done
  }
  _spin & _SPIN_PID=$!
  trap "kill $_SPIN_PID 2>/dev/null; printf '\r\033[K'" EXIT INT TERM
  "$HOME/.local/bin/claude" \
    --dangerously-skip-permissions \
    -p \
    -- "$(cat "$SKILL_FILE")"
else
  exec "$HOME/.local/bin/claude" \
    --dangerously-skip-permissions \
    -p \
    -- "$(cat "$SKILL_FILE")"
fi
