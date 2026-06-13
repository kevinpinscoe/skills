---
name: install-desktop-app
description: Install a desktop application on the current host and create a runbook in ~/Projects/private/app-configuration.
---

# Install a Desktop App

> Install a desktop application on the current host (Fedora KDE Plasma, macOS, or Raspberry Pi 5/Debian), create a runbook in ~/Projects/private/app-configuration, and optionally document install steps for other platforms.

## Prerequisites

- Official installation documentation (or a reputable source) for the application and target platform
- `~/Projects/private/app-configuration` repo accessible and writable
- `~/todo/mac/TODO.md` and `~/todo/rpi/TODO.md` writable (for cross-platform TODO entries)

## Instructions

1. **Read directives** — read the following files in full before taking any other action:
   - `~/.dotfiles/CLAUDE.md` — install paths, `gitsign` warning, GNU Stow conventions
   - `~/todo/CLAUDE.md` — TODO entry format and folder mapping
   - `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md` — git workflow rules and guardrails that apply to all commits in `~/.dotfiles` and `~/todo`
   - `~/ai/directives/when-creating-a-runbook.md` — runbook structure and template (required before step 4)

2. **Detect current platform** — run `uname -s` and `uname -m`; on Linux also read `/etc/os-release`. Record the platform for use in step 4 (platform-specific config subdirectories inside the app directory, if needed):
   - `fedora` for Fedora KDE Plasma
   - `mac` for macOS
   - `rpi5` for Raspberry Pi 5 (Debian Trixie)

3. **Gather information** — ask one question at a time; wait for each answer before asking the next:
   - Application name → derive `<app-slug>` (lowercase, spaces → hyphens, e.g. `it-commander`)
   - Primary website link
   - Installation documentation link for this OS/platform
   - Preferred install method (package manager / vendor download / Flatpak / Snap / Homebrew, etc.)

4. **Create the runbook** — write `~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md`. Use `~/ai/directives/runbook-template.md` as the base structure, adapting it to desktop app documentation. If the app has platform-specific config files, place them under `~/Projects/private/app-configuration/<app-slug>/<platform>/`. At minimum include:
   - `# <App Name>`
   - `## Summary` — brief description of what the app does
   - `## Links` — unordered list: main website, install docs, source repo (if applicable), community/support links (if applicable)
   - `## Operation` — exact install steps/commands, config file locations, post-install setup
   - `## Troubleshooting` — leave blank unless issues occur

   Follow all rules in `~/ai/directives/when-creating-a-runbook.md`.

5. **Install and verify** — install the application, then ask the user to confirm the app is installed and launches without errors. Record any issues and resolutions in `## Troubleshooting`.

6. **Cross-platform inquiry** — ask one question at a time; wait for each answer before asking the next:

   **macOS**: "Should this app also be installed on macOS?"
   - If yes: ask for the macOS install docs URL (research if not provided); add a `## macOS` section to `~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md` populated for macOS; append a TODO entry to `~/todo/mac/TODO.md`:
     ```
     YYYY-MM-DD <install command>  # install <App Name> on macOS (see <docs URL>, consult runbook: ~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md)
     ```

   **Raspberry Pi 5**: "Should this app also be installed on Raspberry Pi 5 (Debian Trixie)?"
   - If yes: ask for the RPi5 install docs URL (research if not provided); add a `## Raspberry Pi 5` section to `~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md` populated for Debian Trixie ARM64; append a TODO entry to `~/todo/rpi/TODO.md`:
     ```
     YYYY-MM-DD <install command>  # install <App Name> on Raspberry Pi 5 Debian Trixie (see <docs URL>, consult runbook: ~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md)
     ```

7. **Commit and push all changed repos** — do not mark the skill complete until every modified repo is pushed. For each repo (`~/Projects/private/app-configuration`, `~/todo`, or both):
   1. Show a summary of files changed and the proposed commit message.
   2. Ask for explicit confirmation before committing.
   3. Stage only the relevant files (never `git add -A`), commit, and push to origin.
   - Commit message: `chore: add <app-slug> runbook` (for `app-configuration`), `chore: add <app-slug> TODO entries` (for `~/todo`)

## Success Criteria

- `~/Projects/private/app-configuration/<app-slug>/RUNBOOK.md` exists and is populated
- The app is confirmed installed and launches without errors on the current host
- Cross-platform sections added to the runbook (if requested) and TODO entries appended (if requested)
- All modified repos committed and pushed

## Notes

- Always use today's date (not a relative date) in TODO entries.
- Keep each TODO entry on a single line.
- Platform-specific config files (scripts, assets) go in `~/Projects/private/app-configuration/<app-slug>/<platform>/`.
