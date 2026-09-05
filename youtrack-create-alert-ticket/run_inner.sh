#!/usr/bin/env bash
set -euo pipefail

# Invoked by run.sh as the command inside `parzival exec ... --`, so
# $YOUTRACK_CURL_CONFIG is already set to a RAM-backed curl config rendered
# by the youtrack-claude-code profile (header = "Authorization: Bearer ...").
# create_alert_ticket.py speaks urllib, not curl, so pull the token out of
# that one-shot file and export it for this single child process only --
# the "environment-variable injection, scoped to one child process" fallback
# Parzival's own README documents, not a raw `parzival get` of the token.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

YOUTRACK_TOKEN="$(sed -n 's/^header = "Authorization: Bearer \(.*\)"$/\1/p' "$YOUTRACK_CURL_CONFIG")"
export YOUTRACK_TOKEN

exec python3 "$SCRIPT_DIR/create_alert_ticket.py" "$@"
