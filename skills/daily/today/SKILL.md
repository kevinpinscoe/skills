---
name: today
description: Syncs daily working repos, resolves user-approved divergence, then walks through the current platform TODO file.
---

# Today

> Syncs daily working repos, resolves user-approved divergence, then walks through the current platform TODO file.

---

> # ⚠️ STOP — THESE REPOS ARE NOT FORKS ⚠️
>
> **`~/Projects/public/skills` and `~/Projects/public/vermilian` are NOT forks. They have
> NEVER been forks. They are Kevin's OWN original repositories.**
>
> - **NEVER** call these repos "forks."
> - **NEVER** assume a repo is a fork because it lives under `~/Projects/public/`.
> - A repo is a fork **only** if `git remote -v` shows an `upstream` remote pointing at
>   someone else's account. If the only remote is `origin` under `github.com/kevinpinscoe`,
>   it is Kevin's own repo — **treat it as a normal repo** and pull it like any other.
> - Location on disk (`~/Projects/public/`) does **NOT** make a repo a fork. Verify with
>   `git remote -v`, never by guessing from the path.
>
> See section **4a** below for the full rules. This warning is repeated there and in the
> Notes because it has been gotten wrong before.

---

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

2. **Detect the host OS and resolve the host identity** — these are two separate things; do not
   conflate them:

   a. **`$OS_LABEL`** (OS family — used only to pick the `check-git-repos` flag in step 3):
      run `uname -s`. `Darwin` → `$OS_LABEL=mac`. `Linux` → `$OS_LABEL=linux`.

   b. **`$TODO_HOST`** (host identity — the *only* thing that decides which single `TODO.md`
      this run touches in steps 9–11): resolve by **hostname**, never by OS family alone.
      `~/ai/directives/kevins-federated-unix-universe.md` is the canonical, definitive registry
      for this — read it (required in step 1) and match the current `hostname` against its
      tables. As of that directive's current contents, the four hosts and their definitive
      hostnames are:

      | `hostname` | `$TODO_HOST` | Host |
      |---|---|---|
      | `KevinI-MBP24` | `mac` | `work-macbook` (physical work Mac, macOS) |
      | `kevin` | `fedora` | `FLDW` (home Fedora workstation) — **this label means FLDW specifically, never any other Linux/Fedora host** |
      | `core` | `rpi` | `RPi5 "core"` (aka rpi5) |
      | `b38e685e79b8` | `mac-container` | `mac-container` (Docker container on `work-macbook`, OS is Fedora Linux but is its own host) |

      Run `hostname` and match it against this table (fall back to `kevins-federated-unix-universe.md`
      directly if the table above has drifted from that file). If the hostname matches none of
      the rows, report the mismatch and stop rather than guessing from OS family — a new host
      needs a row added to the directive (and this table) before this skill can run on it.

      **Every host is concerned with exactly one `TODO.md` file — its own.** Once `$TODO_HOST`
      is resolved, that is the only TODO file this run ever reads, writes, or even looks at. Do
      not open, list, or reference any other host's `TODO.md` in the same run.

   If neither `uname -s` nor `hostname` can be resolved, report the command outputs and stop.

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

4a. **Repos in `~/Projects/public/` — DO NOT assume they are forks.**

    > # ⚠️ NOT FORKS ⚠️
    > **`~/Projects/public/skills` and `~/Projects/public/vermilian` are NOT forks and have
    > never been forks. They are Kevin's OWN repositories.** Do not call them forks. Do not
    > apply fork handling to them. Pull them like any other normal repo (steps 5–7).

    **Living under `~/Projects/public/` does NOT make a repo a fork.** Most repos here are
    Kevin's own original projects. Never infer "fork" from the directory location.

    **How to decide if a repo is actually a fork — verify, do not guess:**
    - Run `git remote -v`.
    - It is a **fork ONLY IF** there is an `upstream` remote pointing at a *different* account
      (i.e. not `github.com/kevinpinscoe`).
    - If the only remote is `origin` under `github.com/kevinpinscoe`, it is **Kevin's own
      repo** — treat it as a normal repo and process it through steps 5–7 like everything else.
    - If you are ever unsure, ASK Kevin. Never label a repo a fork without confirming via the
      remote.

    **The fork-handling rules below apply ONLY to a repo you have confirmed is a real fork**
    (has an `upstream` remote to a different account). They do NOT apply to Kevin's own repos:

    **Pull rules (confirmed forks only):**
    - Do NOT run `git pull` on a confirmed fork unless the currently checked-out branch is a
      personal branch (e.g. `personal`). Pulling on `main` would silently overwrite local
      personal work.
    - If the confirmed fork is BEHIND on `main`: report it but do not pull unless the user
      explicitly requests it.

    **UNTRACKED files (confirmed forks only):**
    1. Run `git branch --list personal` to check for a `personal` branch.
    2. If a `personal` branch exists: tell the user, switch to it, then ask the user to confirm
       which untracked files to stage before doing so.
    3. If no `personal` branch exists: warn the user — do not commit untracked files to `main`.

    **UNSTAGED files (confirmed forks only):**
    - If on `personal` branch: proceed normally through steps 5–7.
    - If on `main` or default branch: warn the user and do not stage or commit until the user
      clarifies whether to create a `personal` branch or commit directly.

    **AHEAD commits (confirmed forks only):**
    - AHEAD commits represent personal work intended for an upstream PR when ready. Do not push
      automatically. Ask the user whether to push to their fork remote, and remind them that
      contributing to the original project requires opening a PR from the fork to upstream.

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

9. **Open the platform TODO file** — using `$TODO_HOST` resolved in step 2b (by hostname, not
   OS family), select the **one** file for this host and open only that file:
   - `mac` -> `~/todo/mac/TODO.md`
   - `fedora` -> `~/todo/fedora/TODO.md` (FLDW only)
   - `rpi` -> `~/todo/rpi/TODO.md`
   - `mac-container` -> `~/todo/mac-container/TODO.md`

   Do not open, cat, or grep any other host's `TODO.md` as part of this step — this run is
   scoped to `$TODO_HOST`'s single file for the remainder of steps 9–11.

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

- **⚠️ `~/Projects/public/skills` and `~/Projects/public/vermilian` are NOT forks — they are
  Kevin's own repositories. Never call them forks. Never assume a repo is a fork based on its
  directory. A repo is a fork ONLY if `git remote -v` shows an `upstream` remote to a different
  account. See section 4a.**
- Use absolute dates in any generated TODO or commit context when dates matter.
- Preserve secrets: never print, store, stage, or commit tokens, passwords, private keys, or sensitive host details.
- Host mapping (`$TODO_HOST`, resolved by `hostname` per `kevins-federated-unix-universe.md` — see step 2b): `mac` is `work-macbook` (macOS), `rpi` is `RPi5 "core"` (Debian Linux), `fedora` is `FLDW` specifically (Fedora Linux on Intel — not any other Fedora/Linux host), and `mac-container` is the Docker container running Fedora Linux hosted on the macOS work machine. Four hosts, four `TODO.md` files, per `~/todo/CLAUDE.md`. Each run touches exactly one of them — the one matching this run's resolved `$TODO_HOST`, never inferred from OS family alone.
- This skill intentionally combines the behavior of daily repo sync and platform TODO processing; if only TODO processing is needed, use `run-through-my-os-todos`.
