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
   - `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md`
   - `~/ai/directives/gitea.md`
   - `~/ai/directives/resume-sh.md`
   - `~/ai/directives/when-creating-or-cloning-a-git-repo.md`
   - `~/ai/directives/storing-secrets.md`, if it exists

2. **Visit daily repos** — process each path below in order. If a path does not exist, skip it silently.
   - `~/.dotfiles`
   - `~/todo`
   - `~/tools`
   - `~/ai`
   - `~/.environment`
   - `~/private-tool`
   - `~/bin`
   - `~/Journal/Professional`
   - `~/Journal/Personal Journal`
   - `~/skills`
   - `~/WorkKnowledgeVault`
   - `~/KnowledgeVault`

3. **Check repo state** — for each existing path:
   - Confirm it is a git repo. If it is not a git repo, skip it silently.
   - Check for nested `.git/` directories below the repo root. If found, warn the user and ask which repo should receive any changes before proceeding in that path.
   - Run `git status --short --branch` and tell the user about modified, deleted, renamed, and untracked files before taking action.
   - Stage only files relevant to this daily sync work. Never use `git add -A`.

4. **Pull safely** — fetch and inspect upstream before merging:
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

5. **Resolve divergence** — when the user approves a merge:
   - Run `git merge @{u}`.
   - If conflicts occur, show the conflicted files with `git status --short` and show conflict diffs with `git diff`.
   - Ask the user how each conflict should be resolved before editing conflicted files.
   - After resolving conflicts, stage only the resolved files and commit the merge with a clear message such as:
     ```
     Merge remote changes for daily sync
     ```
   - If the merge completes without conflicts and Git created the merge commit automatically, report the commit hash.

6. **Push when needed** — after pull or merge handling:
   - Run `git status --short --branch`.
   - If the local branch is ahead of upstream, ask the user whether to push.
   - If approved, run `git push`.
   - If the working tree has changes that should be committed, show the diffs, ask the user what should be included, stage only approved files, commit with a clear message, then ask separately before pushing.

7. **Detect the current platform** — after all repos are processed, identify the platform:
   - `Darwin` from `uname -s` -> `mac`
   - `Linux` with `ID=fedora` in `/etc/os-release` -> `fedora`
   - `Linux` with `ID=debian` in `/etc/os-release` -> `rpi`
   - If the platform cannot be determined, report the command outputs and stop.

8. **Open the platform TODO file** — use the detected platform to select:
   - `mac` -> `~/todo/mac/TODO.md`
   - `fedora` -> `~/todo/fedora/TODO.md`
   - `rpi` -> `~/todo/rpi/TODO.md`

9. **Walk through TODO items** — read the selected `TODO.md` top-to-bottom. For each line:
   - Briefly explain the task and ask the user whether it should be performed now.
   - If the user says yes, perform the task interactively, asking clarifying questions as needed.
   - If the user says no or asks to skip it, leave the line in place and move to the next item.
   - If the task is already complete, show the evidence and ask whether to remove it as complete.
   - When a task is completed or the user confirms it is already complete, remove only that line from the platform `TODO.md`. Do not reorder or modify other lines.

10. **Commit TODO removals** — if any lines were removed from the platform TODO file:
    - Show the diff for the changed `TODO.md`.
    - Ask the user whether to commit the removal.
    - If approved, stage only the changed platform `TODO.md` and commit:
      ```
      git -C ~/todo add <platform>/TODO.md
      git -C ~/todo commit -m "todo: mark completed items done on <platform>"
      ```
    - Ask separately before pushing `~/todo`.

11. **Final report** — summarize:
    - Repos pulled cleanly
    - Repos merged after user approval
    - Repos pushed after user approval
    - TODO items completed and removed
    - TODO items skipped and left in place

## Success Criteria

- Every existing git repo in the daily list was fetched and either pulled, merged with user approval, pushed with user approval, or explicitly reported as skipped because it lacked an upstream or had an unresolved issue.
- No missing directory produced a complaint during processing.
- No divergent files were merged before the user saw the differences and confirmed the merge.
- Merge conflict resolutions were committed after approval.
- The current platform TODO file was processed top-to-bottom with user confirmation for each task.
- Completed TODO items were removed only from the current platform's `TODO.md`.

## Notes

- Use absolute dates in any generated TODO or commit context when dates matter.
- Preserve secrets: never print, store, stage, or commit tokens, passwords, private keys, or sensitive host details.
- Platform mapping: `mac` is macOS, `rpi` is Raspberry Pi Debian Linux, and `fedora` is Fedora Linux on Intel.
- This skill intentionally combines the behavior of daily repo sync and platform TODO processing; if only TODO processing is needed, use `run-through-my-os-todos`.
