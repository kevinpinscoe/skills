---
name: install-desktop-app
description: Install a desktop application on the current host and create a runbook in ~/.dotfiles.
---

# Install a Desktop App

> Install a desktop application on the current host (Fedora KDE Plasma, macOS, or Raspberry Pi 5/Debian), create a platform runbook in ~/.dotfiles, and optionally document install steps for other platforms.

## Prerequisites

- Official installation documentation (or a reputable source) for the application and target platform
- `~/.dotfiles` repo accessible and writable
- `~/todo/mac/TODO.md` and `~/todo/rpi/TODO.md` writable (for cross-platform TODO entries)

## Instructions

1. **Read directive** — read `~/.dotfiles/CLAUDE.md` in full before taking any other action (install paths, `gitsign` warning, GNU Stow conventions).

2. **Detect current platform** — run `uname -s` and `uname -m`; on Linux also read `/etc/os-release`. Use the result to choose the matching platform directory under `~/.dotfiles/desktop-setup/`:
   - `fedora-kde` for Fedora KDE Plasma
   - `MacOS` for macOS
   - `rpi5` for Raspberry Pi 5 (Debian Trixie)

3. **Gather information** — ask one question at a time; wait for each answer before asking the next:
   - Application name → derive `<app-slug>` (lowercase, spaces → hyphens, e.g. `it-commander`)
   - Primary website link
   - Installation documentation link for this OS/platform
   - Preferred install method (package manager / vendor download / Flatpak / Snap / Homebrew, etc.)

4. **Create the runbook** — write `~/.dotfiles/desktop-setup/<platform>/<app-slug>/RUNBOOK.md` with:
   - `# <App Name>`
   - `## Summary` — brief description of what the app does
   - `## Links` — unordered list: main website, install docs, source repo (if applicable), community/support links (if applicable)
   - `## Operation` — exact install steps/commands, config file locations, post-install setup
   - `## Troubleshooting` — leave blank unless issues occur

5. **Install and verify** — install the application, then ask the user to confirm the app is installed and launches without errors. Record any issues and resolutions in `## Troubleshooting`.

6. **Cross-platform inquiry** — ask one question at a time; wait for each answer before asking the next:

   **macOS**: "Should this app also be installed on macOS?"
   - If yes: ask for the macOS install docs URL (research if not provided); create `~/.dotfiles/desktop-setup/MacOS/<app-slug>/RUNBOOK.md` (same format as step 4, populated for macOS); append a TODO entry to `~/todo/mac/TODO.md`:
     ```
     YYYY-MM-DD cd ~/.dotfiles && git pull && <install command>  # install <App Name> on macOS (see <docs URL>, consult runbook: ~/.dotfiles/desktop-setup/MacOS/<app-slug>/RUNBOOK.md)
     ```

   **Raspberry Pi 5**: "Should this app also be installed on Raspberry Pi 5 (Debian Trixie)?"
   - If yes: ask for the RPi5 install docs URL (research if not provided); create `~/.dotfiles/desktop-setup/rpi5/<app-slug>/RUNBOOK.md` (same format, populated for Debian Trixie ARM64); append a TODO entry to `~/todo/rpi/TODO.md`:
     ```
     YYYY-MM-DD cd ~/.dotfiles && git pull && <install command>  # install <App Name> on Raspberry Pi 5 Debian Trixie (see <docs URL>, consult runbook: ~/.dotfiles/desktop-setup/rpi5/<app-slug>/RUNBOOK.md)
     ```

7. **Commit and push all changed repos** — do not mark the skill complete until every modified repo is pushed. For each repo (`~/.dotfiles`, `~/todo`, or both):
   1. Show a summary of files changed and the proposed commit message.
   2. Ask for explicit confirmation before committing.
   3. Stage only the relevant files (never `git add -A`), commit, and push to origin.
   - Commit message: `chore: add <app-slug> runbook` (for `~/.dotfiles`), `chore: add <app-slug> TODO entries` (for `~/todo`)
   - **`~/.dotfiles` uses gitsign (Sigstore/browser OAuth)** — signing requires a browser window and will fail over SSH without a display.

## Success Criteria

- `~/.dotfiles/desktop-setup/<platform>/<app-slug>/RUNBOOK.md` exists and is populated
- The app is confirmed installed and launches without errors on the current host
- Cross-platform runbooks created (if requested) and TODO entries appended (if requested)
- All modified repos committed and pushed

## Notes

- Always use today's date (not a relative date) in TODO entries.
- Keep each TODO entry on a single line. The `cd ~/.dotfiles && git pull &&` prefix ensures the runbook is present on the target host before the install runs.
- `gitsign` commits in `~/.dotfiles` require a browser window for Sigstore OAuth — remind the user if they're over SSH without a display.
