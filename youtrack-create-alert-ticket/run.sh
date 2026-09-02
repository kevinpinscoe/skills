#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export YOUTRACK_BASE_URL="${YOUTRACK_BASE_URL:-https://youtrack.kevininscoe.com}"

YOUTRACK_TOKEN="$(
  BAO_ADDR=https://openbao.kevininscoe.com \
  BAO_TOKEN=$(cat "$HOME/.environment/.vault-token") \
  "$HOME/.local/bin/bao" kv get -field=token -mount=app YouTrack-Claude-Code
)"
export YOUTRACK_TOKEN

exec python3 "$SCRIPT_DIR/create_alert_ticket.py" "$@"
