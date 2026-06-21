---
name: create-a-repo
description: Creates a new Git repository on either Gitea (private) or GitHub (public), clones it locally to the correct directory, scaffolds README.md, RUNBOOK.md, and .gitignore, and (GitHub only) assigns an area-* category topic chosen at runtime from the live profile.yml.
---

# Create a Git Repo

> Interactively gather repo details, create the repo on the correct forge (Gitea for private, GitHub for public), clone it to the standard local path, and scaffold README.md, RUNBOOK.md, and .gitignore.

## Prerequisites

- `git` installed and available in `PATH`
- `gh` CLI installed and authenticated with GitHub (`gh auth status`)
- `tea` CLI installed and authenticated with Gitea (`tea whoami`)
- SSH key in place for GitHub (`ssh -T git@github.com`)
- SSH key in place for Gitea (`ssh -T git@git.kevininscoe.com -p 2223`)
- `~/.config/gitea/api` present (Gitea API token for description update)
- `~/Projects/public/kevinpinscoe/profile.yml` readable (GitHub category source of truth)
- `~/Projects/public/kevinpinscoe` cloned with push access (the GitHub profile repo, remote `git@github.com:kevinpinscoe/kevinpinscoe.git`)
- `~/Projects/public/kevinpinscoe/scripts/generate-readme.py` present (regenerates the profile README)
- `python3` with `pyyaml` available (for the runtime category chooser and the README generator)
- `~/ai/directives/root-directive.md` readable
- `~/ai/directives/when-creating-or-cloning-a-git-repo.md` readable
- `~/ai/directives/gitea.md` readable
- `~/ai/directives/gitignore.md` readable
- `~/ai/directives/when-creating-a-readme.md` readable
- `~/ai/directives/when-creating-a-runbook.md` readable
- `~/ai/directives/runbook-template.md` readable
- `~/ai/directives/when-generating-code-or-updating-code-in-an-outside-repo.md` readable

## Instructions

1. **Pre-flight — has the repo already been created?** — Ask the user: "Has this repo already been created on a remote forge?" 
   - If **yes**: Ask for the SSH-based clone URL (SSH is the only protocol used for git on this system). Clone it per Step 11, then skip directly to Step 12 (post-clone steps). Use the URL to infer the forge (Gitea vs GitHub) for later steps.
   - If **no**: Continue to Step 2.

2. **Read directives** — Read the following directives in full before taking any other action. This step is mandatory at every invocation:
   - `~/ai/directives/root-directive.md` (dispatcher — follow any additional directives it points to that apply to this task)
   - `~/ai/directives/when-creating-or-cloning-a-git-repo.md`
   - `~/ai/directives/gitignore.md`
   - `~/ai/directives/when-creating-a-readme.md`
   - `~/ai/directives/when-creating-a-runbook.md`
   - `~/ai/directives/runbook-template.md`
   - `~/ai/directives/when-generating-code-or-updating-code-in-an-outside-repo.md` (for GitHub repos)

3. **Determine forge** — Ask the user: "Will this repo be created on **git.kevininscoe.com** (Gitea — private) or **github.com/kevinpinscoe** (GitHub — public)?" Do not proceed without this answer.

4. **Get repo name** — Ask the user for the name of the new repo. Normalize it to lowercase-with-hyphens (e.g., "Repo Where Skills Live" → `repo-where-skills-live`). Present the normalized name to the user and ask them to confirm it before proceeding.

5. **Get About summary** — Ask the user for a short GitHub-style About/description for the repo. GitHub's About field has a 350-character limit. If the summary exceeds this limit, tell the user it is too long, suggest an edited version, and wait for them to confirm or supply their own edit. Do not move on until a correctly sized summary is accepted.

6. **Select a license (GitHub repos only)** — For GitHub repos, conduct the license interview from `~/ai/directives/when-creating-or-cloning-a-git-repo.md` step 4. Confirm the license with the user before proceeding. Have the canonical full license text ready (copyright holder: **Kevin P. Inscoe**) to write as `LICENSE` (no `.md` extension) in the repo root after cloning. Skip this step for Gitea repos.

7. **Select a category (GitHub repos only)** — For GitHub repos, determine which category the repo falls under by reading the **live** category list from `~/Projects/public/kevinpinscoe/profile.yml` at runtime. Do **not** rely on any hardcoded list — the categories must be read fresh every invocation, because they change over time. Use the bundled chooser script that ships next to this `SKILL.md` at `~/skills/skills/git/create-a-repo/category-chooser.py` (it reads `profile.yml` fresh on each run):
   - List the current categories:
     ```bash
     ~/skills/skills/git/create-a-repo/category-chooser.py --list
     ```
     This prints one `index<TAB>name<TAB>topic` line per category. Present the numbered category names to the user and ask them to pick exactly one. Do not pick on the user's behalf — ask and wait for their selection.
   - Resolve the user's selection to its `area-*` topic:
     ```bash
     ~/skills/skills/git/create-a-repo/category-chooser.py --resolve <selected-number>
     ```
     Capture the printed `area-*` topic — this is the GitHub topic that will be applied to the new repo in Step 9. Skip this step entirely for Gitea repos.

8. **Confirm creation details** — Present a full summary and ask the user to confirm before taking any action:
   - Forge: git.kevininscoe.com (Gitea, private) or github.com/kevinpinscoe (GitHub, public)
   - Normalized repo name
   - About/description text
   - License SPDX ID (GitHub repos only)
   - Category and its `area-*` topic (GitHub repos only)

9. **Create the repo** — Create the repo on the confirmed forge:
   - **GitHub (public)**:
     ```bash
     gh repo create kevinpinscoe/<repo-name> --public --description "<about-summary>"
     ```
     If the description was not accepted at creation time, set it with:
     ```bash
     gh repo edit kevinpinscoe/<repo-name> --description "<about-summary>"
     ```
     Set the license on the GitHub repo:
     ```bash
     gh repo edit kevinpinscoe/<repo-name> --license <spdx-id>
     ```
     Apply the category topic captured in Step 7 (GitHub repos only):
     ```bash
     gh repo edit kevinpinscoe/<repo-name> --add-topic <area-topic>
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

10. **Determine local clone path** — Decide where to clone based on the forge:
   - **GitHub (public)**: `~/Projects/public/<repo-name>`
   - **Gitea (private)**: `~/Projects/private/<repo-name>`

11. **Clone the repo** — Clone via SSH into the path determined in Step 10. Create the parent directory with `mkdir -p` if it does not exist.
    - **GitHub (public)**:
      ```bash
      git clone git@github.com:kevinpinscoe/<repo-name>.git ~/Projects/public/<repo-name>
      ```
    - **Gitea (private)**:
      ```bash
      git clone ssh://git@git.kevininscoe.com:2223/kinscoe/<repo-name>.git ~/Projects/private/<repo-name>
      ```

---
### Post-clone steps — apply whether the repo was just created or already existed

12. **Apply .gitignore** — Follow `~/ai/directives/gitignore.md` in full. Create a root `.gitignore` that blocks all files and patterns listed in that directive (OS cruft, AI/tool working dirs, editor artifacts, etc.) at all directory depths. The directive specifies exact entries and glob patterns to use.

13. **Propose directory scaffold** — Based on the repo's stated purpose (ask the user if not yet known), propose a sensible top-level directory structure. Present the proposal to the user and ask them to confirm or adjust it. Create the agreed-upon directories (empty directories get a `.gitkeep` placeholder).

14. **Create README.md** — Follow `~/ai/directives/when-creating-a-readme.md` in full. The directive requires conducting an interview with the user before writing. Walk through all interview groups in order (Identity, Getting Started, Understanding the Repo, Changing the Repo, Operations, Governance). Do not fabricate content for sections the user skips. The Repository Layout section must reflect the actual directory structure created in Step 13. Do not write the README until the interview is complete and the user has confirmed the proposed content.

15. **Create RUNBOOK.md** — Follow `~/ai/directives/when-creating-a-runbook.md` in full. Use `~/ai/directives/runbook-template.md` as the base structure. Interview the user for operational context relevant to this repo (how to build/install, how to troubleshoot, credentials/secrets, related services). Place the completed `RUNBOOK.md` at the repo root. Identify any operational gaps and prompt the user for additional information.

16. **Scaffold `mise.toml`** — Create a `mise.toml` at the repo root. Even if no tools are pinned yet, scaffold the file so the repo is mise-ready:
    ```toml
    [tools]
    # python = "3.12"
    # ruby = "3.3"
    # go = "1.23"
    # node = "22"
    ```
    For GitHub repos with a known primary language, uncomment and pin the relevant tool version. Run `mise install` after adding entries.

17. **Update parent directory README** — Add an entry for the new repo to the parent directory's README using the confirmed About text as the description:
    - GitHub repos → `~/Projects/public/README.md` (under the appropriate category table)
    - Gitea repos → `~/Projects/private/README.md` (under the appropriate category table)

18. **Commit and push initial files** — Write the agreed-upon content to all new files. For GitHub repos, also write the `LICENSE` file (canonical full text, no `.md` extension). Then commit and push:
    ```bash
    # GitHub repos
    git -C <clone-dir> add README.md RUNBOOK.md .gitignore mise.toml LICENSE
    git -C <clone-dir> commit -m "Initial commit: README, RUNBOOK, .gitignore, mise.toml, and LICENSE"
    git -C <clone-dir> push

    # Gitea repos
    git -C <clone-dir> add README.md RUNBOOK.md .gitignore mise.toml
    git -C <clone-dir> commit -m "Initial commit: README, RUNBOOK, .gitignore, and mise.toml"
    git -C <clone-dir> push
    ```
    If scaffold directories with `.gitkeep` files were created in Step 13, include them in the same commit.

19. **Verify** — Confirm the push succeeded by running `git -C <clone-dir> log --oneline -3` and reporting the output to the user.

20. **Register the repo in the GitHub profile catalog (GitHub repos only)** — Skip this step entirely for Gitea repos. The profile repo lives at `~/Projects/public/kevinpinscoe` (remote `git@github.com:kevinpinscoe/kevinpinscoe.git`). If the category/topic was not selected earlier (the pre-flight path in Step 1 skips Step 7 for an already-existing repo), run the Step 7 chooser now to obtain the `area-*` topic before continuing. Do all of the following from the profile repo directory:

    a. **Make the profile repo current.** Fetch and inspect status before touching anything:
       ```bash
       git -C ~/Projects/public/kevinpinscoe fetch origin
       git -C ~/Projects/public/kevinpinscoe status -sb
       ```
       Resolve based on what you find — do **not** blindly reset or force:
       - **Behind** `origin/main`: `git -C ~/Projects/public/kevinpinscoe pull --ff-only`
       - **Ahead** of `origin/main`: `git -C ~/Projects/public/kevinpinscoe push`
       - **Diverged** (both ahead and behind): stop and ask the user how to resolve — do not auto-merge or rebase.
       - **Pre-existing unrelated uncommitted changes** (e.g. edits under `scripts/` or `tests/`): do **not** commit or revert them. Leave them in place and stage only `profile.yml` and `README.md` in step (d). If they would block a `pull --ff-only`, surface this to the user instead of stashing without consent.

    b. **Add the new repo to `profile.yml`.** Edit `~/Projects/public/kevinpinscoe/profile.yml` and add the repo under the `repositories.categories:` map, mapping the repo name to the `area-*` topic chosen in Step 7 (place it beside the other repos in that category for tidiness):
       ```yaml
       <repo-name>: [<area-topic>]
       ```
       Optionally, if the GitHub About text should differ from what appears in the catalog, add a description override under `repositories.overrides:`:
       ```yaml
       <repo-name>:
         description: <about-summary>
       ```
       Do not edit `README.md` by hand — it is generated output (step c regenerates it).

    c. **Regenerate the profile README.** Run the generator from the profile repo root:
       ```bash
       cd ~/Projects/public/kevinpinscoe && GITHUB_TOKEN=$(gh auth token) python scripts/generate-readme.py
       ```
       Confirm it exits cleanly and that `README.md` now lists the new repo under the chosen category.

    d. **Commit and push.** Stage **only** `profile.yml` and `README.md` (never `git add -A` — unrelated working-tree changes must be left untouched), then commit and push:
       ```bash
       git -C ~/Projects/public/kevinpinscoe add profile.yml README.md
       git -C ~/Projects/public/kevinpinscoe commit -m "Adding repo <repo-name>"
       git -C ~/Projects/public/kevinpinscoe push
       ```

21. **Rebuild gitme cache** — `gitme --rebuild-cache` must be run by the user in their own
    interactive terminal session. The AI must NOT run this command directly — it calls a
    shell function (`_gitme_build_cache`) sourced from `.zshrc` that is not available in a
    non-interactive shell, so the command will silently fail. Remind the user to run it
    themselves:
    > Please run this in your own terminal to register the new repo in gitme:
    > ```bash
    > gitme --rebuild-cache
    > ```

## Success Criteria

- Remote repo exists on the correct forge (GitHub or Gitea) with the correct name, visibility, and About/description set
- GitHub repos: `LICENSE` file is present, committed, pushed, and the license is set on GitHub via `gh repo edit --license`
- GitHub repos: the category was chosen from the live `profile.yml` list via the chooser, and the matching `area-*` topic is set on the GitHub repo (verify with `gh repo view kevinpinscoe/<repo-name> --json repositoryTopics`)
- GitHub repos: the new repo is registered under `repositories.categories` in `~/Projects/public/kevinpinscoe/profile.yml`, `README.md` was regenerated by `scripts/generate-readme.py` and lists the repo, and both files are committed (`Adding repo <repo-name>`) and pushed to the profile repo's `origin/main` — with no unrelated working-tree changes swept into that commit
- Local clone exists at `~/Projects/public/<repo-name>` or `~/Projects/private/<repo-name>`
- Parent directory README (`~/Projects/public/README.md` or `~/Projects/private/README.md`) has an entry for the new repo
- `README.md`, `RUNBOOK.md`, `.gitignore`, and `mise.toml` are present, committed, and pushed on the `main` branch
- `.gitignore` covers all patterns required by `~/ai/directives/gitignore.md`
- `README.md` was produced via the full interview process from `~/ai/directives/when-creating-a-readme.md`
- `RUNBOOK.md` follows the template from `~/ai/directives/runbook-template.md` and is at the repo root
- Directory scaffold (if any) is committed with `.gitkeep` placeholders
- `git -C <clone-dir> log` shows the initial commit
- No uncommitted or unpushed changes remain

## Notes

- The directive path is `~/ai/directives/` (plural) — a common typo is `~/ai/directive/` (singular) which does not exist.
- Gitea SSH uses non-standard port 2223 — always use the full `ssh://git@git.kevininscoe.com:2223/kinscoe/` prefix.
- SSH is the only protocol used for git on this system — never use HTTPS clone URLs.
- All new repos default to the `main` branch, never `master`.
- GitHub About field limit is 350 characters — enforce this during Step 5.
- For GitHub repos, never create without a LICENSE file — always conduct the license interview in Step 6.
- The category list is read **at runtime** from `~/Projects/public/kevinpinscoe/profile.yml` by `category-chooser.py` — it is deliberately **not** hardcoded in this skill, so newly added categories are picked up automatically. Category selection and topic assignment apply to GitHub repos only, never Gitea.
- Each category maps to exactly one controlled `area-*` GitHub topic (the `topic:` field in `profile.yml`); the chooser returns that topic and Step 9 applies it with `gh repo edit --add-topic`.
- `~/Projects/public/kevinpinscoe/README.md` is **generated** by `scripts/generate-readme.py` from `profile.yml` and the live GitHub topics — never hand-edit it. The generator unions the `repositories.categories` map in `profile.yml` with the `area-*` topics already set on each repo, so registering the new repo in `profile.yml` (Step 20b) makes it appear even before topic propagation.
- Step 20 commits to a **different** repo than the one being scaffolded (the profile repo). Stage only `profile.yml` and `README.md` — never `git add -A` — so unrelated in-progress changes in that repo are not swept into the `Adding repo <repo-name>` commit.
- `mise.toml` is scaffolded for all repos; for Go repos, pin the Go version to match `go.mod` once the module is initialized.
- If the repo already existed and was cloned in Step 1, the forge is inferred from the SSH URL (git.kevininscoe.com → Gitea/private → `~/Projects/private/`; github.com → GitHub/public → `~/Projects/public/`).
- Related skill: `clone-a-repo` — for cloning an existing repo without the full scaffolding workflow.
