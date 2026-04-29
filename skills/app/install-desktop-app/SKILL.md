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
- You must create a runbook (`RUNBOOK.md`) describing what you did.

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

### 3) Create the runbook

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

### 5) Commit and push affected repos

After the user confirms the application works:

- Ask whether they want you to commit and push changes in each repository you modified (typically `~/.dotfiles`). Do not commit/push unless they explicitly say yes.
- Stage only relevant files (avoid `git add -A`)
- Use a short commit message (e.g. `chore: add <app> runbook`)

Important: `~/.dotfiles` uses `gitsign` (Sigstore/browser OAuth). Remind the user that signing may require a browser window and can fail over SSH without a display.
