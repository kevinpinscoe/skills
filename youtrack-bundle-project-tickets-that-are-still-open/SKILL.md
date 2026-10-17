---
name: youtrack-bundle-project-tickets-that-are-still-open
category: youtrack
description: Bundle every issue in one YouTrack project whose Status is neither Done nor Wont do into a single Markdown file of complete yt-export output, with an index and a dependency overview, for backlog refinement and dependency analysis.
disable-model-invocation: true
---

# Bundle a YouTrack Project's Still-Open Tickets

> Bundle every issue in one YouTrack project whose Status is neither Done nor Wont do into a single Markdown file of complete yt-export output, with an index and a dependency overview, for backlog refinement and dependency analysis.

The bundle is written to `~/tmp/gather-youtrack-project-<project name>.md` and is meant to be
handed to a later analysis session. It **preserves**; it does not decide. Every included issue
appears as its complete, unmodified `yt-export` output, and the opening overview is built only
from the Dependency Metadata those exports already carry.

## Prerequisites

- The FLDW (or `core`), with `parzival` able to run `parzival exec --as ai youtrack-claude-code`.
  That is the AI's own YouTrack read path (user `Claude_Code`); the token reaches `curl` through
  `$YOUTRACK_CURL_CONFIG` and never appears on a command line or in the bundle.
- `yt-export` (`~/private-tools/yt-export`) on `PATH`, with the dependency-metadata release of
  the exporter (POE-53). Inside an AI session it exports as `Claude_Code` by itself (KTA-44).
- `gather` 1.2.0 or later on `PATH` (for `--non-interactive`), plus `curl` and `python3`.

## Restrictions

- **Read-only against YouTrack.** Never change an issue, status, priority, dependency,
  assignment or comment while running this skill — not even to fix something the bundle shows.
- **Selection is by `Status` (`157-2`) only**: everything except exactly `Done` and `Wont do`
  (no apostrophe). Never substitute `#Unresolved` or the `resolved` timestamp. A set `Category`
  keeps `Done` issues unresolved, and `Wont do` is not a resolved state. On 2026-10-17 `POE`
  had 13 issues by Status and 16 by `#Unresolved`.
- Never run `parzival get`, read the token, or reach for another credential. If the brokered
  call is refused, stop and report it.
- Do not summarise, trim or rewrite any export. The bundle is evidence for a later session.

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `PROJECT` | The YouTrack project, by short name (`POE`) or full name (`PCT or POE Tooling`) | _(required — ask the user)_ |
| `OVERWRITE` | Replace an existing bundle of the same name | `no` — ask only if the file exists |

## Instructions

1. **Ask for the project.** Ask Kevin which YouTrack project to bundle, by short name or full
   name. Do not guess one from the repository or the conversation.

2. **Check the output path.** The helper derives the file name from the project's full name
   (anything other than letters, digits, `.`, `_` and `-` becomes `-`). If
   `~/tmp/gather-youtrack-project-<that name>.md` already exists, ask Kevin whether to replace
   it. Pass `--overwrite` only on an explicit yes. Without it the helper stops and writes
   nothing.

3. **Run the helper** (one command; it resolves the project, reads the live Status values,
   pages through every issue, runs `yt-export` once per selected issue, and calls
   `gather --non-interactive` to write the bundle):

   ```bash
   parzival exec --as ai youtrack-claude-code -- \
     python3 ~/.claude/skills/youtrack-bundle-project-tickets-that-are-still-open/bundle.py \
     --project "<PROJECT>"            # add --overwrite only if Kevin said yes in step 2
   ```

   - Exit `0`: the bundle was written.
   - Exit `3`: it was written, but some selected issue could not be exported. The header says
     `INCOMPLETE`, and *Missing data and limitations* names each failed issue. Report them; do
     not retry by another credential path.
   - Exit `1`: nothing was written. Report the `ERROR:` line. "No YouTrack project matches"
     lists close matches; ask Kevin which one he meant. A message that the Status bundle no
     longer has `Done` or `Wont do` means the configuration changed; stop and tell Kevin rather
     than choosing a replacement value.

4. **Verify the file.** Confirm that the path printed after `Wrote` exists. Confirm that its
   *Included issues* count equals the "open selected" count the helper printed, minus any
   failures. Confirm that the index lists the same number of rows.

5. **Report.** Give Kevin the absolute path of the bundle, the project name and short name, how
   many issues were scanned and included, the counts by Status, and anything in *Missing data
   and limitations*: failed exports, inaccessible linked issues, issues without a Status.
   Mention any cycles and how many text-only candidates were found. Do not analyse the backlog
   or recommend an order unless Kevin asks. That is a separate step that reads this bundle.

## What the bundle contains

- **Header:** project name, short name, ID and URL; export time and host; the selection rule;
  the configured Status values; issue counts in total, by Status, and included.
- **Index:** each included issue's ID, title, Status and URL, in key order.
- **Dependency overview**, from formal `Depend` links only. It lists:
  - what can start or continue now;
  - what waits on open work inside the selection, and what waits on work outside it;
  - blockers already completed, and cross-project dependencies;
  - a layered working order, where issues in one layer can proceed in parallel;
  - cycles;
  - informational parent/subtask, related, duplicate and other links, kept separate from
    blocking ones.

  It is labelled a **dependency-based working order, not a critical path**, because no issue
  carries a duration estimate.
- **Text-only candidates:** issue keys mentioned in descriptions or comments without a formal
  link, and lines that read like blockers ("blocked by", "waiting on", …). They are labelled
  unconfirmed and are never mixed into the formal dependencies.
- **Missing data and limitations:** failed exports, exports without metadata, inaccessible
  linked issues, issues without a Status, missing estimates, and the native-links-only limit.
- **Exports:** every included issue's complete `yt-export` output, in index order, each in a
  fenced block written by `gather` under a `## <path>` heading. Linked issues outside the
  selection appear inside those exports as references (key, title, project, Status); they are
  context, not selected tickets.

## Success Criteria

- `~/tmp/gather-youtrack-project-<project name>.md` exists, and its absolute path was reported.
- The bundle names the project's full name and short name, the export time, the selection rule,
  and the included-issue count.
- Every issue in the project whose Status is not `Done` or `Wont do` is in the index and has a
  complete export below it, or is named in *Missing data and limitations* as not exported.
- No YouTrack issue was changed.

## Notes

- **Tests:** `cd ~/.claude/skills/youtrack-bundle-project-tickets-that-are-still-open &&
  python3 test_bundle.py`. There are 20 offline tests, with no YouTrack, no `yt-export` and no
  `gather`. They cover selection, pagination, dependency preservation, an empty project, safe
  naming, overwrite refusal and failed exports.
- **Run time** is roughly one `yt-export` call per selected issue, about a second each. The
  per-issue exports go to a temporary directory under `~/tmp` that is removed once `gather`
  succeeds. Add `--keep-exports` to keep it, and it is kept anyway if `gather` fails.
- **Chooser label:** `skills` shows a skill by its directory name with hyphens turned into
  spaces, so this one appears as "youtrack bundle project tickets that are still open" under
  `youtrack`. skills-tui has no separate label field.
- **Limits that remain:** the overview sees formal links only, and the text candidates are a
  pattern match, not a judgement. Inaccessible linked issues are detected from YouTrack's
  `issuesSize` count, and none existed for `Claude_Code` when this was written. No estimates
  exist, so no critical path is computed.
- Related: `youtrack-prioritize-youtrack-tickets`.
