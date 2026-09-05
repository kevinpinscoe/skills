#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export YOUTRACK_BASE_URL="${YOUTRACK_BASE_URL:-https://youtrack.kevininscoe.com}"

# The FLDW's plaintext OpenBao root token (~/.environment/.vault-token) was
# revoked and removed under PARZIVAL-2/PARZIVAL-9 -- credential access now
# goes through parzival's youtrack-claude-code profile, never a direct
# `bao kv get`. See ~/ai/directives/when-creating-a-youtrack-ticket.md SS14.
#
# Source the AppRole env directly rather than assume the caller's shell did
# (Claude Code's own Bash tool runs a non-interactive shell that never reads
# .zshrc/.bashrc) -- without this, `parzival` silently falls back to its
# ambient bao-CLI compatibility mode, which needs the now-deleted vault token.
[[ -f "$HOME/.environment/openbao/openbao-env.sh" ]] && source "$HOME/.environment/openbao/openbao-env.sh"

exec parzival exec --as ai youtrack-claude-code -- "$SCRIPT_DIR/run_inner.sh" "$@"
