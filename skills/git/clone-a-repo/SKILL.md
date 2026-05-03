---
name: clone-a-repo
description: Asks for a git repo URL, determines the correct local clone directory per the AI directive, confirms with the user, then clones the repo.
---

# Clone a Git Repo

> Ask the user for a git repo URL, determine the correct local directory per the cloning directive, confirm the destination, then clone.

## Prerequisites

- `git` installed and available in `PATH`
- SSH key or credentials in place for the target host (if a private repo)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `REPO_URL` | Full URL of the git repo to clone | _(mandatory — always ask the user)_ |

## Instructions

1. **Read directive** — Read `~/ai/directives/when-creating-or-cloning-a-git-repo.md` in full before taking any other action. This step is mandatory at every invocation.

2. **Ask for the URL** — Ask the user: "What is the URL of the git repo you want to clone?" This is mandatory — do not proceed without a URL supplied directly by the user.

3. **Determine clone directory** — Using the URL provided and the location rules in the directive's "Cloned repos" section, determine the full target path:
   - `https://git.kevininscoe.com/` → `~/Projects/private/<repo-name>`
   - `https://github.com/kevinpinscoe` → `~/Projects/public/<repo-name>`
   - `https://github.com/acst` → `~/Projects/acst/<repo-name>`
   - Anything else → `~/Projects/3rd-party-repos/<repo-name>`

   Derive `<repo-name>` from the last path segment of the URL, stripping any `.git` suffix.

4. **Confirm with user** — Before running any command, tell the user the resolved destination path and ask them to confirm. Example: "I will clone `<REPO_URL>` into `<TARGET_DIR>`. Confirm?" Do not proceed until they confirm.

5. **Clone** — Run:
   ```bash
   git clone <REPO_URL> <TARGET_DIR>
   ```

6. **Verify** — Confirm the clone succeeded by checking that `<TARGET_DIR>/.git` exists and reporting the output of `git -C <TARGET_DIR> log --oneline -3`.

## Success Criteria

- `<TARGET_DIR>/.git` exists on disk
- `git -C <TARGET_DIR> log` returns at least one commit (or reports an empty repo for a freshly initialized remote)
- The destination directory matches the path specified by the directive and confirmed by the user

## Notes

- If the user wants a non-standard clone path (not covered by the directive's rules), ask them to confirm explicitly before proceeding — the directive allows special exceptions that the user must approve.
- Do not create the parent directory tree manually; `git clone` creates it. If the parent does not exist, create it with `mkdir -p` first.
