#!/usr/bin/env bash
# Keeps every skill under ~/.claude/skills out of the model's context unless
# the skill itself opts in (AI-52).
#
# Claude Code loads the name and description of every model-invocable skill
# into every session, which costs tokens for skills Kevin only ever runs by
# typing /name. Skills tracked in this repo opt out in their own frontmatter
# (`disable-model-invocation: true`), which reaches every host via git. Skills
# this repo does not own - the gitignored gsd-* plugin content and the
# vanco-skills symlinks - cannot carry that edit, so this script covers them
# instead: it adds `"<skill>": "user-invocable-only"` under `skillOverrides`
# in the host's ~/.claude/settings.json, a per-machine file git never sees.
#
# Run it on every host after `git pull`, and again after a get-shit-done
# plugin update (new gsd-* skills).
#
# Usage:
#   bash sync-skill-overrides.sh           # add missing overrides
#   bash sync-skill-overrides.sh --check   # report only; exit 1 if any are missing
#
# Re-runnable: no-op when nothing is missing. Only ever ADDS entries; an
# existing override (whatever its value) is left alone, and entries for
# skills that no longer exist are reported, never deleted.
#
# Portable to macOS's bash 3.2: no associative arrays, no mapfile.

set -euo pipefail

SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
CHECK_ONLY=0

case "${1:-}" in
    "") ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1 (try --help)" >&2; exit 2 ;;
esac

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required" >&2; exit 1; }
[ -d "$SKILLS_DIR" ] || { echo "ERROR: skills directory not found: $SKILLS_DIR" >&2; exit 1; }
[ -f "$SETTINGS" ] || { echo "ERROR: settings file not found: $SETTINGS" >&2; exit 1; }
jq empty "$SETTINGS" 2>/dev/null || { echo "ERROR: $SETTINGS is not valid JSON" >&2; exit 1; }

# True when the SKILL.md's leading frontmatter block sets the opt-out flag.
has_optout() {
    awk 'NR==1 { if ($0 != "---") exit 1; next }
         /^---$/ { exit 1 }
         /^disable-model-invocation:[[:space:]]*true[[:space:]]*$/ { found=1; exit 0 }
         END { exit found ? 0 : 1 }' "$1"
}

missing=()
covered=0
optout=0
broken=0

for dir in "$SKILLS_DIR"/*; do
    name="$(basename "$dir")"
    skill="$dir/SKILL.md"
    if [ -L "$dir" ] && [ ! -e "$dir" ]; then
        # A dangling symlink (e.g. a vanco-skills link whose target lives on another host).
        echo "skip: $name (symlink target missing on this host)"
        broken=$((broken + 1))
        continue
    fi
    [ -f "$skill" ] || continue
    if has_optout "$skill"; then
        optout=$((optout + 1))
        continue
    fi
    if jq -e --arg n "$name" '.skillOverrides // {} | has($n)' "$SETTINGS" >/dev/null; then
        covered=$((covered + 1))
        continue
    fi
    missing+=("$name")
done

# Overrides naming skills that are no longer on disk: harmless, reported only.
stale="$(jq -r '.skillOverrides // {} | keys[]' "$SETTINGS" | while read -r n; do
    [ -d "$SKILLS_DIR/$n" ] || echo "$n"
done)"

echo "opted out in frontmatter: $optout"
echo "already overridden:       $covered"
echo "missing override:         ${#missing[@]}"
[ "$broken" -eq 0 ] || echo "dangling symlinks:        $broken"
if [ -n "$stale" ]; then
    echo "stale overrides (skill not on disk; left in place):"
    while IFS= read -r n; do echo "  $n"; done <<< "$stale"
fi

if [ "${#missing[@]}" -eq 0 ]; then
    echo "ok: nothing to add"
    exit 0
fi

printf '  + %s\n' "${missing[@]}"

if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "check: ${#missing[@]} skill(s) would be loaded into model context" >&2
    exit 1
fi

backup="$SETTINGS.bak-$(date +%Y%m%d-%H%M%S)"
cp -p "$SETTINGS" "$backup"

# Write via a same-directory temp file that already carries the original's
# mode (settings.json is 0600), then rename over the original atomically.
tmp="$(dirname "$SETTINGS")/.settings.json.tmp.$$"
cp -p "$SETTINGS" "$tmp"
trap 'rm -f "$tmp"' EXIT
jq --args '.skillOverrides = ((.skillOverrides // {}) + (reduce $ARGS.positional[] as $n ({}; .[$n] = "user-invocable-only")))' \
    "${missing[@]}" < "$SETTINGS" > "$tmp"
jq empty "$tmp"
mv -f "$tmp" "$SETTINGS"
trap - EXIT

echo "added ${#missing[@]} override(s) to $SETTINGS"
echo "backup: $backup"
echo "Restart Claude Code sessions for the change to take effect."
