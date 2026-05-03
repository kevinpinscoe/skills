---
name: create-a-repo
description: Creates a new Git repository on either Gitea (private) or GitHub (public), clones it locally to the correct directory, and commits an initial README.md.
---

# Create a Git Repo

> Interactively gather repo details, create the repo on the correct forge (Gitea for private, GitHub for public), clone it to the standard local path, and commit an initial README.md.

## Prerequisites

- `git` installed and available in `PATH`
- `gh` CLI installed and authenticated with GitHub (`gh auth status`)
- `tea` CLI installed and authenticated with Gitea (`tea whoami`)
- SSH key in place for GitHub (`ssh -T git@github.com`)
- SSH key in place for Gitea (`ssh -T git@git.kevininscoe.com -p 2223`)
- `~/.config/gitea/api` present (Gitea API token for description update)
- `~/ai/directives/when-creating-or-cloning-a-git-repo.md` readable
- `~/ai/directives/gitea.md` readable
- `~/ai/directives/resume-sh.md` readable

## Instructions

1. **Read directive** — Read `~/ai/directives/when-creating-or-cloning-a-git-repo.md` and `~/ai/directives/resume-sh.md` in full before taking any other action. This step is mandatory at every invocation.

2. **Determine forge** — Ask the user: "Will this repo be private?" If yes, it will be created on Gitea. If no, it will be created on GitHub. Do not proceed without this answer.

3. **Get repo name** — Ask the user for the name of the new repo. Normalize it to lowercase-with-hyphens (e.g., "Repo Where Skills Live" → `repo-where-skills-live`). Present the normalized name to the user and ask them to confirm it before proceeding.

4. **Get About summary** — Ask the user for a short GitHub-style About/description for the repo. GitHub's About field has a 350-character limit. If the summary exceeds this limit, tell the user it is too long, suggest an edited version, and wait for them to confirm or supply their own edit. Do not move on until a correctly sized summary is accepted.

5. **Get repo purpose** — Ask the user for the purpose of this new repo. This information is required to generate the initial README.md content.

6. **Propose README.md contents** — Based on the user's stated purpose, draft the full contents of the initial README.md. Present the proposed content to the user and wait for their confirmation or edits. Do not proceed until the README.md content is agreed upon.

7. **Confirm all details** — Present a full summary and ask the user to confirm before taking any action:
   - Visibility: public or private
   - Forge: GitHub (`https://github.com/kevinpinscoe`) or Gitea (`https://git.kevininscoe.com`)
   - Normalized repo name
   - About/description text
   - Repo purpose
   - Proposed README.md contents

8. **Create the repo** — Create the repo on the confirmed forge:
   - **GitHub (public)**:
     ```bash
     gh repo create kevinpinscoe/<repo-name> --public --description "<about-summary>"
     ```
     If the description was not accepted at creation time, set it with:
     ```bash
     gh repo edit kevinpinscoe/<repo-name> --description "<about-summary>"
     ```
   - **Gitea (private)**:
     ```bash
     tea repo create --name <repo-name> --private
     ```
     Then set the description via the Gitea API:
     ```bash
     curl -s -X PATCH "https://git.kevininscoe.com/api/v1/repos/kinscoe/<repo-name>" \
       -H "Authorization: token $(cat ~/.config/gitea/api)" \
       -H "Content-Type: application/json" \
       -d '{"description": "<about-summary>"}'
     ```

9. **Clone the repo** — Clone into the correct local directory per the directive. Create the parent directory with `mkdir -p` if it does not exist.
   - **GitHub (public)** — clone via SSH into `~/Projects/public/<repo-name>`:
     ```bash
     git clone git@github.com:kevinpinscoe/<repo-name>.git ~/Projects/public/<repo-name>
     ```
   - **Gitea (private)** — clone via SSH into `~/Projects/private/<repo-name>`:
     ```bash
     git clone ssh://git@git.kevininscoe.com:2223/kinscoe/<repo-name>.git ~/Projects/private/<repo-name>
     ```

10. **Apply .gitignore** — Follow `~/ai/directives/resume-sh.md` to create a root `.gitignore` in the cloned repo that blocks `resume.sh`, `.DS_Store`, `.claude`, `.codex`, `.trash/`, and `.obsidian/workspace.json` at all directory depths.

11. **Create and push README.md** — Write the agreed-upon content to `<clone-dir>/README.md`, then commit and push both new files:
    ```bash
    git -C <clone-dir> add README.md .gitignore
    git -C <clone-dir> commit -m "Initial commit: README and .gitignore"
    git -C <clone-dir> push
    ```

12. **Verify** — Confirm the push succeeded by running `git -C <clone-dir> log --oneline -3` and reporting the output to the user.

13. **Rebuild gitme cache** — Run `gitme --rebuild-cache` to register the new repo in the local gitme index:
    ```bash
    gitme --rebuild-cache
    ```

## Success Criteria

- Remote repo exists on the correct forge (GitHub or Gitea) with the correct name, visibility, and About/description set
- Local clone exists at `~/Projects/public/<repo-name>` or `~/Projects/private/<repo-name>`
- `README.md` and `.gitignore` are present, committed, and pushed on the `main` branch
- `git -C <clone-dir> log` shows the initial commit
- No uncommitted or unpushed changes remain

## Notes

- The directive path is `~/ai/directives/` (plural) — a common typo is `~/ai/directive/` (singular) which does not exist.
- Gitea SSH uses non-standard port 2223 — always use the full `ssh://git@git.kevininscoe.com:2223/kinscoe/` prefix.
- All new repos default to the `main` branch, never `master`.
- GitHub About field limit is 350 characters — enforce this during Step 4.
- Related skill: `clone-a-repo` — for cloning an existing repo without creating it.
