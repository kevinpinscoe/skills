---
name: human-todos
description: Manage a personal task list in ~/TODO.md — add, view, triage, and work tasks with optional codebase analysis.
---

# Human TODOs

> Manage a personal task list in `~/TODO.md` — add tasks individually, view the list, work a task with system analysis, or run a brain-dump triage session.

## Prerequisites

- `~/TODO.md` exists (created alongside this skill)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `MODE` | What to do: `add`, `view`, `work`, or `triage` | _(ask the user if not stated)_ |

## Instructions

### Determine mode

If the user's message already implies a mode, use it. Otherwise ask:
- **add** — capture one task
- **view** — read and display the current list
- **work** — pick a task and help complete it
- **triage** — brain-dump mode: many ideas at once

---

### Mode: add

1. Ask the user to describe the task in any form — freeform, messy, or half-formed is fine.
2. If the task is ambiguous, ask one clarifying question. No more.
3. If the task involves a codebase, service, file, or system: read the relevant files or run `git log --oneline -10` / `find` to understand current state, then refine the description based on what you find.
4. Format the task as a single actionable line using today's absolute date:
   ```
   - [ ] YYYY-MM-DD <Verb-led action description>
   ```
   Start with a verb: Fix, Add, Update, Write, Investigate, Move, etc.
5. Show the formatted line to the user and ask for approval or edits.
6. After approval, append the line to `~/TODO.md` under the `## Tasks` section.

---

### Mode: view

1. Read `~/TODO.md`.
2. Display all open tasks (`- [ ]`) and done tasks (`- [x]`) in the order they appear.
3. Summarize: "X open, Y done."
4. If there are more than 10 open tasks, ask the user if they want to triage or reprioritize.

---

### Mode: work

1. Read `~/TODO.md` and list the open tasks numbered.
2. Ask which task to work on (by number or keyword).
3. If the task references a system, codebase, or config:
   - Read relevant files, run `git log`, grep for symbols, or inspect running services as needed.
   - Summarize findings in 2–3 sentences before proceeding.
4. Propose one concrete next step (a command, an edit, a question to resolve). Ask the user to confirm or redirect.
5. Continue until the task is complete or the user pauses.
6. When done, ask whether to mark it complete. If yes, update the line in `~/TODO.md`:
   ```
   - [x] YYYY-MM-DD <original description>  # completed YYYY-MM-DD
   ```

---

### Mode: triage

> Use this when the user has many things swirling in their head and needs help sorting them into actionable tasks.

1. Say: "Tell me everything on your mind — tasks, ideas, half-thoughts, anything. I'll sort it out. Just dump it all."
2. Let the user write freely. Do not interrupt or ask questions during the dump.
3. When the user signals they are done (says "done", "that's it", sends a blank line, or similar), stop collecting.
4. Parse the dump and extract discrete actionable items. For each:
   - Ask one clarifying question only if the action is genuinely ambiguous — batch all clarifying questions together, not one at a time.
   - Format each as a dated `- [ ]` line.
5. Present the full extracted list to the user for review. Allow edits, drops, or reordering before writing anything.
6. After approval, append all lines to `~/TODO.md` under `## Tasks`.

---

## Success Criteria

- **add**: New dated `- [ ]` line at the bottom of `~/TODO.md`'s Tasks section
- **view**: All tasks displayed with an open/done count
- **work**: Task progressed; marked `[x]` with completion date if finished
- **triage**: All approved extracted tasks written to `~/TODO.md`

## Notes

- Always use today's absolute date — never "today", "tomorrow", or relative dates.
- `~/TODO.md` is not in a git repo — no commit needed after writes.
- For tasks that involve any repo under `~/Projects/`: read `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md` before touching files there.
- Related skill: `os-todo` — for platform-specific shell-command TODOs (fedora/mac/rpi).
