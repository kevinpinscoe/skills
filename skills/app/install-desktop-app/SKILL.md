---
name: install-desktop-app
description: Install a desktop application on the current host and create a runbook in ~/.dotfiles.
---

# Install a desktop app

Install a desktop application on the current host (for example: Fedora KDE Plasma, macOS Tahoe on Apple Silicon, or Debian Trixie+ on Raspberry Pi 5/ARM).

Before proceeding, determine the current host platform (OS + architecture). Do not guess.

## Grounding and background

Before doing anything, read:

- `~/.dotfiles/CLAUDE.md` — install paths, `gitsign` warning, and GNU Stow conventions (if relevant)

## Requirements

- You must have official installation documentation (or a reputable source) for the application and platform.
- You must create a runbook (`RUNBOOK.md`) describing what you did — **for every platform the app is confirmed for**, including the current host.

## Actions to take

### 1) Detect the current host platform

Detect platform using:

- `uname -s` and `uname -m`
- On Linux: `/etc/os-release`

Use that information to choose (or create) the correct directory under:

- `~/.dotfiles/desktop-setup/<platform>/<app-slug>/`

### 2) Gather information (ask one question at a time)

Ask questions one at a time — do not present multiple questions at once. Wait for the user's answer before asking the next question.

- Application name
- Primary website link
- Installation documentation link for *this* OS/platform (if different)
- Any preferred install method (package manager vs. vendor download vs. Flatpak/Snap/Homebrew, etc.)

Use the application name given by the user to create an `<app-slug>`.

Where:

- `<platform>` maps into already defined directories in `~/.dotfiles/desktop-setup/` (e.g. `fedora-kde`, `MacOS`, `rpi5`). Choose the platform directory that matches the platform gathered in Step 1.
- `<app-slug>` is the application name lowercased, with spaces replaced by hyphens (e.g. `it-commander`).

### 3) Create the runbook for the current platform

Create:

- `~/.dotfiles/desktop-setup/<platform>/<app-slug>/RUNBOOK.md`

Populate `RUNBOOK.md` with:

- `# <App Name>`
- `## Summary` — brief, informative description of what the app does
- `## Links` — unordered list (`-`) including:
  - Main website
  - Installation docs
  - Source repo (GitHub/GitLab/Gitea/etc.), if applicable
  - Community/support links, if applicable
- `## Operation` — include:
  - Exact install steps/commands for this OS/platform
  - Where configuration files live and their names
  - Any post-install setup steps
- `## Troubleshooting` — leave blank unless issues occur

### 4) Verify application function

Ask the user to verify:

- The app is installed
- The app launches without errors

If there are issues, record symptoms and the resolution steps in the `## Troubleshooting` section of the runbook.

### 5) Cross-platform inquiry

Ask one question at a time and wait for each answer before asking the next.

**5a) macOS inquiry**

Ask: "Should this app also be installed on macOS?"

If yes:
- Ask: "Do you have an installation documentation link for macOS?"
- If the user provides a link, use it. If not, research and find a reputable official source.
- Create `~/.dotfiles/desktop-setup/MacOS/<app-slug>/RUNBOOK.md` using the same format as Step 3, populated for macOS.
- Append a TODO entry to `~/todo/mac/TODO.md` in the format used by that file:
  ```
  YYYY-MM-DD cd ~/.dotfiles && git pull && <install command>  # install <App Name> on macOS (see <docs URL>, consult runbook: ~/.dotfiles/desktop-setup/MacOS/<app-slug>/RUNBOOK.md)
  ```
  Use today's date. Keep the entry on a single line. The `cd ~/.dotfiles && git pull &&` prefix ensures the runbook is present before the install runs.

**5b) Raspberry Pi 5 inquiry**

Ask: "Should this app also be installed on Raspberry Pi 5 (Debian Trixie)?"

If yes:
- Ask: "Do you have an installation documentation link for Raspberry Pi 5 / Debian Trixie?"
- If the user provides a link, use it. If not, research and find a reputable official source.
- Create `~/.dotfiles/desktop-setup/rpi5/<app-slug>/RUNBOOK.md` using the same format as Step 3, populated for Debian Trixie on ARM64.
- Append a TODO entry to `~/todo/rpi/TODO.md` in the format used by that file:
  ```
  YYYY-MM-DD cd ~/.dotfiles && git pull && <install command>  # install <App Name> on Raspberry Pi 5 Debian Trixie (see <docs URL>, consult runbook: ~/.dotfiles/desktop-setup/rpi5/<app-slug>/RUNBOOK.md)
  ```
  Use today's date. Keep the entry on a single line. The `cd ~/.dotfiles && git pull &&` prefix ensures the runbook is present before the install runs.

### 6) Commit and push all changed repos

This step is **required** — the skill is not complete until every file changed by this skill has been committed and pushed. Do not skip or defer.

For each repository modified (`~/.dotfiles`, `~/todo`, or both):

1. Show the user a summary of files changed and the proposed commit message.
2. Ask for explicit confirmation before committing.
3. Once confirmed, stage only the relevant files (never `git add -A`), commit, and push to origin.

Commit message format: `chore: add <app-slug> runbook` (for `~/.dotfiles`), `chore: add <app-slug> TODO entries` (for `~/todo`).

Important: `~/.dotfiles` uses `gitsign` (Sigstore/browser OAuth). Remind the user that signing may require a browser window and can fail over SSH without a display.

Do not mark the skill complete until `git push` has succeeded for every repository that was modified.
