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
#
# Links are RELATIVE (AI-53), so the text git stores is identical on every host:
# from ~/.claude/skills, "../../Projects/private/vanco-skills/skills/<name>"
# reaches ~/Projects/private/vanco-skills whatever the home directory is. An old
# absolute link to the same place is rewritten to the relative form.
#
# The relative text assumes this repo is checked out at ~/.claude/skills. On a
# host where it is not (e.g. the work Mac, where the clone is
# ~/Projects/public/skills and ~/.claude/skills is wired by vanco-skills'
# wire-claude-skills.sh), or inside an ai-wt/ worktree, the committed links would
# only be rewritten into something host-specific, so the script reports that and
# changes nothing. Set VANCO_ROOT to override (a relative path is computed from
# the repo to it) — that is a deliberate local rewrite.

set -euo pipefail

REPO="$(cd -P "$(dirname "$0")" && pwd)"
CLAUDE_SKILLS="$(cd -P "$HOME/.claude/skills" 2>/dev/null && pwd || true)"

if [ -n "${VANCO_ROOT:-}" ]; then
    # Local override: relative path from $REPO to the chosen vanco-skills root.
    SKILLS_REL="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$VANCO_ROOT/skills" "$REPO")"
elif [ "$REPO" = "$CLAUDE_SKILLS" ]; then
    SKILLS_REL="../../Projects/private/vanco-skills/skills"
else
    echo "skip: $REPO is not ~/.claude/skills, so the committed relative links" >&2
    echo "do not resolve from here and are left untouched (AI-53). Run this on a" >&2
    echo "host whose clone is ~/.claude/skills, or set VANCO_ROOT to override." >&2
    exit 0
fi

# Each entry: "<link path relative to $REPO>|<skill directory name>"
LINKS=(
    "jira-create-a-jira-ticket|jira-create-a-jira-ticket"
    "jira-create-jira-tickets-bookmark|jira-create-jira-tickets-bookmark"
    "jira-update-menu-app-yaml-from-jira-html|jira-update-menu-app-yaml-from-jira-html"
    "youtrack-check-for-duplicate-tickets-and-tag|youtrack-check-for-duplicate-tickets-and-tag"
    "youtrack-create-a-youtrack-project|youtrack-create-a-youtrack-project"
    "youtrack-create-ticket-in-youtrack|youtrack-create-ticket-in-youtrack"
    "youtrack-get-my-assigned-tickets-from-jira-into-youtrack|youtrack-get-my-assigned-tickets-from-jira-into-youtrack"
    "youtrack-insert-specific-jira-ticket-in-youtrack|youtrack-insert-specific-jira-ticket-in-youtrack"
    "youtrack-read-updates-from-tasks-and-generate-stand-up|youtrack-read-updates-from-tasks-and-generate-stand-up"
    "youtrack-reconcile|youtrack-reconcile"
    "youtrack-report-a-problem|youtrack-report-a-problem"
    "youtrack-sync-jira-ticket-status-with-youtrack|youtrack-sync-jira-ticket-status-with-youtrack"
    "daily-run-through-my-os-todo|daily-run-through-my-os-todo"
)

link_one() {
    local link="$1"
    local name="$2"
    local target="$SKILLS_REL/$name"

    if [ ! -d "$(dirname "$link")/$target" ]; then
        echo "ERROR: target does not exist: $(dirname "$link")/$target" >&2
        echo "Clone/update vanco-skills (~/Projects/private/vanco-skills) first." >&2
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
    name="${entry#*|}"
    link_one "$REPO/$link_rel" "$name" || status=1
done

exit "$status"
