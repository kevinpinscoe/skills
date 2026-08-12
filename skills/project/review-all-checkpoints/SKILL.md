---
name: review-all-checkpoints
description: Review every CHECKPOINT.md on this host and report which YouTrack issue each one tracks and which directory to resume it from.
---

# Review All Checkpoints

> Review every `CHECKPOINT.md` on this host and report which YouTrack issue each one tracks and which directory to resume it from.

A `CHECKPOINT.md` is the only artifact one AI session leaves where another can find it. Several
agents work on this host at once without sharing context, so a checkpoint left on disk means
unfinished work — and a pile of them means Kevin has lost track of what is outstanding. This
skill reads all of them and answers, per checkpoint: **which issue, which directory, what is
blocking it.**

**This skill only reads.** It never edits, ticks a task in, or deletes another session's
`CHECKPOINT.md`. Those files belong to the sessions that wrote them.

## Prerequisites

- `check-git-repos` on `PATH` (`/usr/bin/check-git-repos`) — supplies the repository list
- `python3` — runs `collect-checkpoints.py`
- `git` — resolves each repository's primary working tree and worktree list
- Read access to the reported repositories. `/opt/containers` is root-owned but world-readable,
  so no `sudo` is needed to read a checkpoint there

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `COMMAND` | Collector command supplying the repository list | `check-git-repos --checkpoint` |
| `PATH_OVERRIDE` | Review one specific `CHECKPOINT.md` or repository instead of scanning | _(none — scans everything)_ |

## Instructions

1. **Collect** — from this skill's own directory, run:

   ```bash
   python3 collect-checkpoints.py
   ```

   It runs `check-git-repos --checkpoint`, finds every `CHECKPOINT.md` in the reported
   repositories (searching each in full, because in a tracking repository like `~/admin` or
   `/opt/containers` a checkpoint lives in the project's own subdirectory), and emits JSON.

   To review a single checkpoint instead, pass `--path ~/some/repo/CHECKPOINT.md`.

2. **Stop early if the output is empty** — `check-git-repos --checkpoint` prints nothing when no
   checkpoint exists anywhere. That silence is a real answer: report "no unfinished AI work is
   outstanding" and stop. Do not go looking for checkpoints another way.

3. **Read each `summary` field in full.** The script extracts facts; the `## Summary` section
   carries the judgment. Every checkpoint on this host opens with one, written specifically to be
   read cold by an agent with no context. Read it before drawing any conclusion about a
   checkpoint's state — the JSON alone will mislead you.

4. **Determine the YouTrack issue.** `issues.primary` is taken from the H1 title, which on this
   host reads `# CHECKPOINT — <ISSUE>: <what>`. Treat it as a strong default, not gospel:

   - **Several primaries** means the checkpoint genuinely covers more than one issue (a checkpoint
     spanning `KSEIM-5` and `KSEIM-6`, for example). Report all of them.
   - **`issues.mentioned`** are other sessions' issues, named to explain a collision or a
     dependency. Do not report one as the checkpoint's own issue.
   - **No issue at all** is a real state, not a parse failure — a project may be mid-setup with
     the issue not yet filed. Say so, and say which workflow step files it.
   - Cross-check against the summary: if a checkpoint's own issue is closed and the file survives
     only to hold a *successor* issue open, report the successor as what to resume.

5. **Determine the resume directory.** Default to `checkpoint_dir` — the directory the checkpoint
   sits in, which is the repository's primary working tree, or the project's subdirectory in a
   tracking repository.

   Two cases override it, and both need the summary to spot:

   - **A live worktree.** When `worktrees` is non-empty, code changes belong in
     `<repo>/ai-wt/<ISSUE-ID>/`, never the primary tree. Report both: the primary tree for merge
     and cleanup steps, the worktree for the code.
   - **The work is somewhere else entirely.** A checkpoint can sit in the repo whose ground it
     claims while the remaining work lives elsewhere — a checkpoint in `~/admin` whose one
     outstanding item is a job under `~/PCM`, for instance. Follow the summary, not the file's
     location.

6. **Determine what is blocking it.** Use `tasks.next_open` as the resume point and
   `blocker_lines` plus the summary to classify each checkpoint as one of:

   - **Blocked on Kevin** — an open pull request awaiting his approval on the forge. Report the
     PR URLs from `pull_requests`.
   - **Blocked on another session** — waiting on a different checkpoint's work. Name the other
     issue.
   - **Ready to resume** — nothing in the way; give the next open task verbatim.
   - **Complete but retained** — every task ticked, or the file explicitly kept to hold a
     successor issue visible. Say what has to happen before it can be deleted.

7. **Report** — one Markdown table, in the order the collector returned, with these columns:

   | Column | Contents |
   |---|---|
   | `CHECKPOINT.md` | `checkpoint_dir` in `~/` form |
   | YouTrack issue | Every primary issue key, with its full `https://youtrack.kevininscoe.com/issue/<KEY>` URL as bare text |
   | `cd` here to resume | Resume directory from step 5, noting the worktree where one exists |
   | State | The classification from step 6, plus `tasks.done`/`tasks.total` |

   Below the table, add a short prose section for anything the table cannot hold: contradictions
   between a checkpoint's ticked state and what the summary says, two checkpoints deadlocked on
   each other, or a stale worktree left behind. Keep it to what changes Kevin's next action.

   Report every pull request as a full FQDN URL in bare text — never `<repo>#<n>`, and never
   wrapped in Markdown link syntax, which hides the URL in a terminal.

## Success Criteria

- Every `CHECKPOINT.md` reported by `check-git-repos --checkpoint` appears in the table exactly once
- Each row names a YouTrack issue with its full URL, or states plainly that no issue exists yet
- Each row names a directory that exists on disk
- Every checkpoint is classified as blocked, ready, or complete-but-retained — none left ambiguous
- No `CHECKPOINT.md` was modified, and `git status` in every reported repository is unchanged
- When no checkpoint exists, the report says so in one line rather than emitting an empty table

## Notes

- **Checkpoints move while you read them.** Other sessions tick tasks, and new checkpoints appear
  mid-run. Treat the collector's output as a snapshot, and prefer re-running it over reasoning
  from an earlier one.
- A checkpoint may record an observation appended by a *different* session (`/opt/containers`
  carries one). Attribute it correctly rather than reading it as the owning session's own note.
- The issue-key pattern matches any `ABC-123` token, so `CVE-2026-69152` and `GHSA-…` are
  filtered out explicitly. A new identifier scheme shaped like an issue key would need adding to
  `NOT_AN_ISSUE` in the script.
- This skill creates and updates nothing in YouTrack, so the `Issue domain` obligation from
  https://youtrack.kevininscoe.com/issue/AI-3 does not reach it.
- Operational detail — installation, troubleshooting, and how the parser decides things — is in
  `RUNBOOK.md` beside this file.
