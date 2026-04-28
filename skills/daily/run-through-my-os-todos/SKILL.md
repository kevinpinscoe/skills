---
name: run-through-my-os-todos
description: Syncs the ~/todo repo and walks through the current OS's TODO.md items one at a time, executing or skipping each and removing completed entries.
---

# Daily To Do Run Through

> Syncs the `~/todo` repo from remote origin, detects the current operating system, then walks through that system's `TODO.md` items top-to-bottom — executing tasks interactively with the user and removing completed entries.

## Prerequisites

- `~/todo` is a git repo with a configured remote origin
- Git is installed and the remote is accessible
- The user is present and ready to interact

## Instructions

1. **Sync the todo repo** — run `cd ~/todo && git pull` to fetch the latest entries from remote origin. If the pull fails, report the error and stop — do not proceed with a potentially stale `TODO.md`.

2. **Detect the current operating system** — run `uname -s` and, if the result is `Linux`, read `/etc/os-release` to identify the distribution:
   - `Darwin` → platform is `mac`
   - `Linux` + `ID=fedora` in `/etc/os-release` → platform is `fedora`
   - `Linux` + `ID=debian` in `/etc/os-release` → platform is `rpi`
   - If the platform cannot be determined, report the output of both commands and stop.

3. **Read the TODO.md** — read `~/todo/<platform>/TODO.md`. Each line follows the format:
   ```
   YYYY-MM-DD <shell command or task description>  # <reason>
   ```
   If the file is empty or contains no lines, say **"No todos for this system today."** and stop.

4. **Walk through items top-to-bottom** — for each line in order:

   a. **Evaluate completeness** — examine the item and determine whether it appears to already be complete on this system (e.g. a package is already installed, a config change is already applied, a command has clearly already been run). If it appears complete, report `[ALREADY DONE] <item>`, remove the line from the file (see step 5), and move to the next item.

   b. **Propose execution** — if the item is not already complete, briefly explain what the task involves and ask: `"Do you want me to execute this task?"` Wait for the user's response before proceeding.

   c. **Execute with dialogue** — if the user says yes, carry out the task. Ask confirming or clarifying questions as needed throughout execution. The user may redirect or change course at any point — follow their direction. If the user says no or asks to skip, leave the line in place and move to the next item.

   d. **Mark complete** — when a task finishes successfully (whether Claude executed it or the user confirms they handled it manually), remove the line from the file (see step 5).

5. **Remove completed lines** — edit `~/todo/<platform>/TODO.md` in place, deleting only the completed line. Do not reorder or modify any other lines.

6. **Commit removals** — after all items have been processed, if any lines were removed, ask the user: `"Shall I commit the updated TODO.md to the todo repo?"` If yes, run:
   ```
   cd ~/todo && git add <platform>/TODO.md && git commit -m "todo: mark completed items done on <platform>"
   ```
   Then ask separately: `"Shall I push to remote origin?"`

7. **Final report** — summarize the session:
   - Items already done (removed automatically)
   - Items executed and completed (removed)
   - Items skipped by the user (left in file)

## Success Criteria

- The `~/todo` repo was pulled successfully before reading any items.
- Every item in the `TODO.md` was either evaluated for completeness or presented to the user — none were silently skipped.
- Completed items have been removed from the file.
- No action was taken without the user's confirmation.

## Notes

- Platform mapping: `mac` → `~/todo/mac/TODO.md`, `fedora` → `~/todo/fedora/TODO.md`, `rpi` → `~/todo/rpi/TODO.md`.
- Each TODO entry is a shell command with an inline `# reason` comment — the command itself is what Claude should execute (or verify), not just a natural-language description.
- On the Fedora host, use `sudo -A` for commands that require elevated privileges (a stored askpass is configured).
- Per `~/skills/CLAUDE.md`, always confirm with the user before committing or pushing changes to the `~/todo` repo.
