---
name: today
description: Syncs daily working repos, resolves user-approved divergence, then walks through the current platform TODO file.
---

# Today

> Syncs daily working repos, resolves user-approved divergence, then walks through the current platform TODO file.

## Prerequisites

- Git is installed
- The user is present and ready to review diffs, approve merges, and confirm TODO actions
- The target repositories that exist locally have configured remotes
- Network access is available for `git pull` and `git push`

## Instructions

1. **Read required directives** — before touching any repo, read and follow:
   - `~/ai/directives/root-directive.md` (dispatcher — follow any additional directives it points to that apply to this task)
   - `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md`
   - `~/ai/directives/gitea.md`
   - `~/ai/directives/when-creating-or-cloning-a-git-repo.md`
   - `~/ai/directives/when-creating-a-runbook.md`
   - `~/ai/directives/storing-secrets.md`, if it exists

2. **Detect the host OS** — run `uname -s` and record the result:
   - Output is `Darwin` → macOS; set `$OS_LABEL=mac`
   - Output is `Linux` → check `/etc/os-release` for `ID=fedora` → `$OS_LABEL=fedora`; `ID=debian` → `$OS_LABEL=rpi`
   - If the platform cannot be determined, report the command outputs and stop.

3. **Run check-git-repos** — discover repos that need attention:
   - Locate the binary with `command -v check-git-repos`. If not found, report that `check-git-repos` is not installed and stop.
   - If `$OS_LABEL=mac`, run: `check-git-repos --ignore-prefix`
   - Otherwise, run: `check-git-repos`
   - Capture each repo path from the output. These are the only repos to process in the steps below.
   - If the command produces no output, report that all repos are clean and skip ahead to the TODO steps.

4. **Check repo state** — for each path flagged by `check-git-repos`:
   - Confirm it is a git repo. If it is not a git repo, skip it silently.
   - Check for nested `.git/` directories below the repo root. If found, warn the user and ask which repo should receive any changes before proceeding in that path.
   - Run `git status --short --branch` and tell the user about modified, deleted, renamed, and untracked files before taking action.
   - Stage only files relevant to this daily sync work. Never use `git add -A`.

5. **Pull safely** — fetch and inspect upstream before merging:
   - Run `git fetch --prune`.
   - Determine the current branch and its upstream with `git rev-parse --abbrev-ref HEAD` and `git rev-parse --abbrev-ref --symbolic-full-name @{u}`.
   - If there is no upstream, report that path as skipped and continue to the next repo.
   - Show the user the local-only commits with `git log --oneline @{u}..HEAD`, if any.
   - Show the user the remote-only commits with `git log --oneline HEAD..@{u}`, if any.
   - If local and remote have not diverged, run `git pull --ff-only`.
   - If a fast-forward pull is not possible, show the user the relevant differences before merging:
     ```
     git diff --stat HEAD...@{u}
     git diff HEAD...@{u}
     ```
     Then ask whether to merge the remote changes into the local branch. Do not merge until the user confirms.

6. **Resolve divergence** — when the user approves a merge:
   - Run `git merge @{u}`.
   - If conflicts occur, show the conflicted files with `git status --short` and show conflict diffs with `git diff`.
   - Ask the user how each conflict should be resolved before editing conflicted files.
   - After resolving conflicts, stage only the resolved files and commit the merge with a clear message such as:
     ```
     Merge remote changes for daily sync
     ```
   - If the merge completes without conflicts and Git created the merge commit automatically, report the commit hash.

7. **Push when needed** — after pull or merge handling:
   - Check whether the push remote is `no_push`: `git remote get-url --push origin 2>/dev/null`.
   - If the push remote is `no_push`, skip the push prompt entirely — note the repo in the final report (step 12) and move on.
   - Run `git status --short --branch`.
   - If the local branch is ahead of upstream, ask the user whether to push.
   - If approved, run `git push`.
   - If the working tree has changes that should be committed, show the diffs, ask the user what should be included, stage only approved files, commit with a clear message, then ask separately before pushing.

8. **Check default branch alignment** — after syncing, review branch state for every repo processed in steps 4–7:

   a. **Determine branches** — in each repo, run:
      ```
      git branch --no-color --show-current
      git remote show origin | sed -n '/HEAD branch/s/.*: //p'
      ```
      If the repo is already on its default branch, note it as aligned and move to the next repo.

   b. **Report misalignment** — for any repo whose current branch differs from the default branch, clearly state:
      - The repo path
      - The current branch name
      - The default branch name
      - How many commits the current branch is ahead of or behind the default: `git log --oneline <default>..<current>` and `git log --oneline <current>..<default>`

   c. **Check for uncommitted work** — before suggesting any branch action, run:
      ```
      git status --short
      git stash list
      ```
      If there are staged, modified, or untracked files, or any stash entries, report the full details to the user and ask what should happen to that work (commit it, stash it, or leave it) before proceeding. Do not switch or delete branches while uncommitted work exists unless the user has given explicit instructions for how to handle it.

   d. **Check for open pull requests** — check for PRs or unmerged commits:
      - If `gh` is available and the remote is GitHub, run: `gh pr list --head <current-branch> --json number,title,url`
      - If `tea` is available and the remote is Gitea, run: `tea pr list --output simple` and filter by the current branch
      - In all cases, run `git log origin/<default>..<current> --oneline` to show commits not yet merged into the default branch
      Report any open PRs or unmerged commits to the user before suggesting deletion.

   e. **Ask the user what to do** — present a clear summary of findings and ask the user to choose one of:
      1. Switch to the default branch and **keep** the current branch (no deletion)
      2. Switch to the default branch and **delete** the current branch locally — only offer this option if there is no uncommitted work, no open PRs, and no unmerged commits; otherwise explain why it is not safe yet
      3. Leave the repo on the current branch and skip it for now
      Do not take any branch action until the user has chosen.

   f. **Execute the user's choice** — if the user chooses to switch:
      - Run `git checkout <default>` then `git pull --ff-only`.
      - If deletion was approved, run `git branch -d <branch>` (safe delete; will refuse if unmerged). Only escalate to `git branch -D` (force delete) if the user explicitly requests it after being warned that unmerged commits will be lost.

9. **Open the platform TODO file** — using `$OS_LABEL` detected in step 2, select:
   - `mac` -> `~/todo/mac/TODO.md`
   - `fedora` -> `~/todo/fedora/TODO.md`
   - `rpi` -> `~/todo/rpi/TODO.md`

10. **Walk through TODO items** — read the selected `TODO.md` top-to-bottom. For each line:
    - Briefly explain the task and ask the user whether it should be performed now.
    - If the user says yes, perform the task interactively, asking clarifying questions as needed.
    - If the user says no or asks to skip it, leave the line in place and move to the next item.
    - If the task is already complete, show the evidence and ask whether to remove it as complete.
    - When a task is completed or the user confirms it is already complete, remove only that line from the platform `TODO.md`. Do not reorder or modify other lines.

11. **Commit TODO removals** — if any lines were removed from the platform TODO file:
    - Show the diff for the changed `TODO.md`.
    - Ask the user whether to commit the removal.
    - If approved, stage only the changed platform `TODO.md` and commit:
      ```
      git -C ~/todo add <platform>/TODO.md
      git -C ~/todo commit -m "todo: mark completed items done on <platform>"
      ```
    - Ask separately before pushing `~/todo`.

12. **Final report** — summarize:
    - Repos pulled cleanly
    - Repos merged after user approval
    - Repos pushed after user approval
    - Repos with a `no_push` remote: pulled normally, push skipped automatically
    - Repos on a non-default branch: whether switched, kept, or skipped; and whether any branches were deleted
    - TODO items completed and removed
    - TODO items skipped and left in place

## Success Criteria

- Every repo flagged by `check-git-repos` was fetched and either pulled, merged with user approval, pushed with user approval, or explicitly reported as skipped because it lacked an upstream or had an unresolved issue.
- No missing directory produced a complaint during processing.
- No divergent files were merged before the user saw the differences and confirmed the merge.
- Merge conflict resolutions were committed after approval.
- Every repo on a non-default branch was reported with its current branch, default branch, and outstanding commit delta; uncommitted work and open PRs were surfaced before any branch action; the user chose the outcome and no branch was deleted without explicit approval.
- `git branch -D` (force delete) was only used when the user explicitly requested it after being warned about unmerged commits.
- The current platform TODO file was processed top-to-bottom with user confirmation for each task.
- Completed TODO items were removed only from the current platform's `TODO.md`.

## Notes

- Use absolute dates in any generated TODO or commit context when dates matter.
- Preserve secrets: never print, store, stage, or commit tokens, passwords, private keys, or sensitive host details.
- Platform mapping: `mac` is macOS, `rpi` is Raspberry Pi Debian Linux, and `fedora` is Fedora Linux on Intel.
- This skill intentionally combines the behavior of daily repo sync and platform TODO processing; if only TODO processing is needed, use `run-through-my-os-todos`.
