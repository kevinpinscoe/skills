---
name: os-todo
description: Append a dated TODO entry to one or more platform TODO files (fedora, mac, rpi) and commit/push to the todo repo.
---

# Add Platform TODO

> Append a dated TODO entry to one or more platform-specific `~/todo` files, detect potential duplicates, and commit+push to the todo repo.

## Prerequisites

- `~/todo` repo accessible and writable
- Network access for `git push`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `TASK` | The shell command or action to record as a TODO | _(required — ask the user)_ |
| `REASON` | Short comment explaining why the task is needed | _(required — ask the user)_ |
| `PLATFORMS` | Which platforms: `fedora`, `mac`, `rpi`, or `all` | _(required — ask the user)_ |

## Instructions

1. **Read grounding file** — read `~/todo/CLAUDE.md` in full before doing anything else to confirm the current entry format and platform-to-file mapping.

2. **Gather information** — ask one question at a time; wait for each answer before asking the next:
   - What is the TODO task — the exact shell command or action the user needs to perform on the target machine?
   - What is the reason or comment to append after the `#` in the entry?
   - Which platform(s) should this be added to? Options: `fedora`, `mac`, `rpi`, or `all`.

3. **Detect install tasks and build the full command** — if the task installs a command-line tool, software package, or desktop application, prepend the appropriate pull step to ensure local files are up to date before the install runs:
   - If the install depends on `~/tools`: prepend `cd ~/tools && git pull && `
   - If the install depends on `~/.dotfiles`: prepend `cd ~/.dotfiles && git pull && `
   - If neither applies (e.g. bare `curl` download, `brew install`, `apt install`): no prefix needed.
   Keep the entire entry on a single line.

4. **Check for duplicates** — for each selected platform, read that platform's `TODO.md` and scan every existing entry for overlap with the new task (same command, same package, same file being edited, etc.). If a similar or identical entry is found:
   - Show the existing entry to the user.
   - Ask whether to: (a) add the new entry anyway, (b) skip this platform, or (c) replace the existing entry.
   Wait for the user's answer before proceeding.

5. **Format and append the entry** — construct the line using today's absolute date:
   ```
   YYYY-MM-DD <full command>  # <reason>
   ```
   Append this line to the bottom of each selected platform's `TODO.md`. Platform mapping:
   - `fedora` → `~/todo/fedora/TODO.md`
   - `mac`    → `~/todo/mac/TODO.md`
   - `rpi`    → `~/todo/rpi/TODO.md`

6. **Commit and push** — from the `~/todo` directory, stage only the modified `TODO.md` files (never `git add -A`), then commit and push to origin:
   - Commit message: `todo: <short task description> for <platform(s)>`
   - Push to origin on the default branch (`main`).

## Success Criteria

- The new dated entry appears at the bottom of each selected platform's `TODO.md`
- No unintended duplicate entries exist in any modified file
- Changes committed and pushed to the `~/todo` repo

## Notes

- Always use today's absolute date in entries — never relative dates like "today" or "tomorrow".
- Keep every entry on a single line regardless of length.
- The two-space gap before `#` in the entry format (`<command>  # <reason>`) matches existing entries — preserve it.
- If the user selects `all` and the task is platform-specific (e.g. a `brew`-only command), flag the mismatch and ask for clarification before appending.
