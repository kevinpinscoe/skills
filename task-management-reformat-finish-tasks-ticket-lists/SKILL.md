---
name: task-management-reformat-finish-tasks-ticket-lists
category: task-management
description: Reformat the YouTrack ticket lists in a finish-tasks notes file to one consistent checklist line per ticket, adding missing ticket URLs and correcting spelling and grammar without adding writing or re-ordering anything.
disable-model-invocation: true
---

# Reformat Finish-Tasks Ticket Lists

> Reformat the YouTrack ticket lists in a finish-tasks notes file to one consistent checklist line per ticket, adding missing ticket URLs and correcting spelling and grammar without adding writing or re-ordering anything.

## Prerequisites

- The target file exists and sits in a git repository, so the result can be reviewed with `git diff` and undone
- The target file has no uncommitted changes before the run, so the diff shows only this skill's work
- `python3` for the verification check in the Instructions
- No YouTrack access is needed: a ticket URL is built from the ticket key, and nothing is read from or written to YouTrack

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `FILE` | The notes file to reformat | `~/Projects/workspaces/finish-tasks.md` |
| `YOUTRACK_ISSUE_URL` | The URL prefix a ticket key is appended to | `https://youtrack.kevininscoe.com/issue/` |

## Instructions

The target line, for every ticket that is listed:

```text
- [ ] <YOUTRACK_ISSUE_URL><KEY> - Explanation or summary of the ticket
```

A ticket key is uppercase letters, a hyphen, and a number, such as `POE-48`.

1. **Read the file and check its state** — read `FILE` in full. Run `git status --short -- FILE` in its repository. If the file already has uncommitted changes, tell the human and ask whether to continue before changing anything.

2. **Reformat every ticket line** — a ticket line is a list item whose subject is one ticket. Apply these rules to each one, and change nothing else about it:
   - **Checkbox first.** The line starts with `- [ ]`. Keep the state it already has: `[ ]`, `[X]` and `[-]` are all left as they are. Repair a malformed checkbox such as `-[ ] -`.
   - **URL second.** The ticket URL follows the checkbox directly. Move anything that sits between them, such as a rank number or a parenthetical, to after the separator.
   - **Plain URL.** Use `YOUTRACK_ISSUE_URL` plus the key and nothing more. Where a URL carries a title slug after the key, cut the slug and use its words as the summary.
   - **Separator.** One space, a hyphen, one space (` - `) between the URL and the summary. Replace an em-dash or any other separator there. Leave em-dashes that sit inside the summary alone.
   - **Rank numbers.** Write a rank or step number as `<URL> - 1. summary`.
   - **No summary.** A ticket line with only a URL stays that way. Do not write a summary for it.

3. **Convert tickets listed in another shape** — tickets given as a table, including a box-drawing table pasted onto one line, become one checklist line each, in the same order. Keep every piece of information the table held: put a row number in as the rank number, and append the other columns to the summary using the table's own column heading as the words, for example `Depends on PKM-50, PKM-51.`

4. **Add missing ticket URLs** — inside a list item, where a ticket is named by its key and that ticket's URL appears nowhere in the file, replace the first mention of the key with its URL. Leave alone:
   - a key whose URL already appears elsewhere in the file;
   - a key in prose outside a list item, where a URL would force the sentence to be reworded;
   - a key inside an ASCII diagram or a code block.

5. **Correct spelling and grammar** — across the whole file, fix misspellings, wrong articles, misplaced apostrophes, run-on sentences, the capitalization of proper nouns and product names, doubled spaces, and trailing spaces. Never "correct" a coined name; `Vermilian` is spelled with an `a` on purpose. A hostname keeps the case the host uses.

6. **Hold to the limits** — these apply to every step above:
   - Do not add writing. No new summaries, notes, headings, or explanations.
   - Do not re-order or sort anything. Every ticket stays where it is.
   - Do not remove a duplicate ticket line, an empty checklist item, or a heading.
   - Do not check or uncheck a box.
   - Do not touch list items that are not about a ticket, such as a file path or a plain to-do, beyond step 5.

7. **Verify** — every ticket line must match the target shape. This prints each one that does not, and must print nothing:

   ```bash
   python3 - "$FILE" "$YOUTRACK_ISSUE_URL" << 'PY'
   import re, sys
   path, base = sys.argv[1], sys.argv[2]
   good = re.compile(r"- \[[ xX-]\] " + re.escape(base) + r"[A-Z0-9]+-\d+( - .+)?$")
   for number, line in enumerate(open(path, encoding="utf-8"), 1):
       line = line.rstrip("\n")
       if re.match(r"\s*-\s*\[", line) and base in line and not good.match(line):
           print(number, line)
   PY
   ```

   A line it prints is acceptable only when the item is not about a ticket and merely mentions one in its text. Say so in the report.

   Then read `git diff -- FILE` once from top to bottom and confirm that no line moved and that no sentence was added.

8. **Report** — tell the human, in this order: what changed, grouped by kind (separator, table conversion, URLs added, spelling and grammar); what was deliberately left alone and why, including bare keys left as they are, duplicate ticket lines, and tickets with no summary; and any heading or sentence that reads oddly but was not changed. Leave the file uncommitted and say so. Commit and push only when the human asks.

## Success Criteria

- Every ticket line in `FILE` reads `- [ ] <URL> - summary`, or `- [ ] <URL>` where it had no summary
- The check in step 7 prints nothing
- The tickets are in the same order as before, and none was added, removed, checked, or unchecked
- No new writing was added to the file
- The change is uncommitted and the human has been told what was left alone

## Notes

- The first run was done by hand on 2026-10-11 against `~/Projects/workspaces/finish-tasks.md`, under POE-48 (`https://youtrack.kevininscoe.com/issue/POE-48`). This skill records the rules that run settled on.
- That repository is ordinary maintenance: commits go directly to `main`, with no worktree, branch, or pull request. Its `README.md` says so. Check the target repository's own rules before committing a file that lives elsewhere.
- The majority style in the file decides the separator. If a future file uses a different majority style, follow the file and tell the human.
- A related file, `finish-mac-tasks.md`, sits beside the default target. Pass it as `FILE` to reformat it the same way.
