#!/usr/bin/env bash
# Recreates symlinks from vanco-skills into this repo. Git tracks the
# symlinks themselves, but if a target is missing or a link gets clobbered,
# run this to put them back.
#
# Re-runnable: no-op when each link is already correct.

set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
VANCO_ROOT="/home/kinscoe/Projects/private/vanco-skills"

# Each entry: "<link path relative to $REPO>|<absolute target path>"
LINKS=(
    "skills/Jira|$VANCO_ROOT/skills/Jira"
    "skills/YouTrack|$VANCO_ROOT/skills/YouTrack"
    "skills/daily/run-through-my-os-todo|$VANCO_ROOT/skills/daily/run-through-my-os-todo"
)

link_one() {
    local link="$1"
    local target="$2"

    if [ ! -d "$target" ]; then
        echo "ERROR: target does not exist: $target" >&2
        echo "Clone/update vanco-skills into $VANCO_ROOT first." >&2
        return 1
    fi

    if [ -L "$link" ]; then
        local current
        current="$(readlink "$link")"
        if [ "$current" = "$target" ]; then
            echo "ok: $link -> $target (already correct)"
            return 0
        fi
        echo "replacing existing symlink: $link -> $current"
        rm "$link"
    elif [ -e "$link" ]; then
        echo "ERROR: $link exists and is not a symlink. Refusing to overwrite." >&2
        return 1
    fi

    ln -s "$target" "$link"
    echo "created: $link -> $target"
}

status=0
for entry in "${LINKS[@]}"; do
    link_rel="${entry%%|*}"
    target="${entry#*|}"
    link_one "$REPO/$link_rel" "$target" || status=1
done

exit "$status"
