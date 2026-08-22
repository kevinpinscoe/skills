#!/usr/bin/env bash
# Recreates symlinks from vanco-skills into this repo. Git tracks the
# symlinks themselves, but if a target is missing or a link gets clobbered,
# run this to put them back.
#
# Re-runnable: no-op when each link is already correct.
#
# One symlink per individual vanco-skills skill, category-prefixed to match
# this repo's flat ~/.claude/skills layout (FSM-3) — a whole-category symlink
# doesn't work once there's no category directory level to symlink onto.

set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
VANCO_ROOT="/home/kinscoe/Projects/private/vanco-skills"

# Each entry: "<link path relative to $REPO>|<absolute target path>"
LINKS=(
    "jira-create-a-jira-ticket|$VANCO_ROOT/skills/Jira/create-a-jira-ticket"
    "jira-create-jira-tickets-bookmark|$VANCO_ROOT/skills/Jira/create-jira-tickets-bookmark"
    "jira-update-menu-app-yaml-from-jira-html|$VANCO_ROOT/skills/Jira/update-menu-app-yaml-from-jira-html"
    "youtrack-check-for-duplicate-tickets-and-tag|$VANCO_ROOT/skills/YouTrack/check-for-duplicate-tickets-and-tag"
    "youtrack-create-a-youtrack-project|$VANCO_ROOT/skills/YouTrack/create-a-youtrack-project"
    "youtrack-create-ticket-in-youtrack|$VANCO_ROOT/skills/YouTrack/create-ticket-in-youtrack"
    "youtrack-get-my-assigned-tickets-from-jira-into-youtrack|$VANCO_ROOT/skills/YouTrack/get-my-assigned-tickets-from-jira-into-youtrack"
    "youtrack-insert-specific-jira-ticket-in-youtrack|$VANCO_ROOT/skills/YouTrack/insert-specific-jira-ticket-in-youtrack"
    "youtrack-read-updates-from-tasks-and-generate-stand-up|$VANCO_ROOT/skills/YouTrack/read-updates-from-tasks-and-generate-stand-up"
    "youtrack-reconcile|$VANCO_ROOT/skills/YouTrack/reconcile"
    "youtrack-report-a-problem|$VANCO_ROOT/skills/YouTrack/report-a-problem"
    "youtrack-sync-jira-ticket-status-with-youtrack|$VANCO_ROOT/skills/YouTrack/sync-jira-ticket-status-with-youtrack"
    "daily-run-through-my-os-todo|$VANCO_ROOT/skills/daily/run-through-my-os-todo"
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
