---
name: install-command-line-command
description: Prompts me for required information before installing a command line tool and then generates a cheat sheet for it
---

# Install a Command-Line Tool

> Install a command-line tool (script or binary) on the current host, generate a cheat sheet in `~/cheats`, and append TODO entries to `~/todo/<os>/TODO.md` for each non-current operating system.

## Prerequisites

- `~/.dotfiles` repo accessible and writable (`~/cheats` is a GNU Stow symlink into `~/.dotfiles/home/cheats/`)
- `~/todo/<os>/TODO.md` writable for each target OS
- Network access to download the tool or its documentation

## Instructions

1. **Read grounding files** — read the following files in full before taking any other action:
   - `~/.dotfiles/CLAUDE.md` — binary install paths, gitsign warning, stow structure
   - `~/todo/CLAUDE.md` — TODO entry format and folder mapping
   - `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md` — git workflow rules and guardrails that apply to all commits in `~/.dotfiles` and `~/todo`

2. **Gather information** — ask one question at a time; wait for each answer before asking the next:
   - Command name → check for collisions with `command -v`, `type -a`, and a direct check of `~/.local/bin`; if the name collides, ask the user to rename it (or suggest a rename)
   - Link to the best documentation to use for installation instructions (required — do not proceed without it)
   - One or more tags to associate with the command
   - A short summary of what the command does (always ask directly — do not infer from docs)
   - Operating systems to support: `all` or a specific list (e.g. `fedora`, `mac`, `rpi`)
   - If installation is more complex than a single file, ask clarifying questions before proceeding
   - If multiple executables will be installed: gather the command name for each, perform collision evaluation for each, and create a separate cheat sheet for each

3. **Install on the current host** — detect the platform with `uname -s` (and `/etc/os-release` on Linux):

   - **Fedora Linux**: prefer downloading the binary to `~/.local/bin/` (create it first if needed):
     ```bash
     curl -sSfL <download-url> -o ~/.local/bin/<command> && chmod +x ~/.local/bin/<command>
     ```
     If the tool provides a `dnf` package or official installer, that is also acceptable.
   - **macOS (Apple Silicon)**: prefer `brew install <package>`. If no Homebrew formula exists, fall back to `~/.local/bin/`.
   - **Raspberry Pi 5 (Debian Trixie)**: prefer downloading to `~/.local/bin/`. If the tool provides an `apt` package or official installer, that is also acceptable.

   If the tool requires or creates config files under the home directory, add them to `~/.dotfiles` using the GNU Stow symlink method.

4. **Create the cheat sheet** — choose the template and destination based on the OS scope from step 2:

   | Scope | Template | Destination |
   |---|---|---|
   | `all` | `~/cheats/templates/all.md` | `~/cheats/all/<command_name>` |
   | `fedora` | `~/cheats/templates/fedora.md` | `~/cheats/fedora/<command_name>` |
   | `mac` | `~/cheats/templates/mac.md` (or `all.md` if absent) | `~/cheats/mac/<command_name>` |
   | `rpi` | `~/cheats/templates/rpi.md` (or `all.md` if absent) | `~/cheats/rpi/<command_name>` |

   Fill in all `{{VARIABLE}}` placeholders directly when writing the file — do not run `generate-cheat.sh` or update `GENERATE-CHEAT.md`:

   | Variable | Value |
   |---|---|
   | `{{COMMAND_NAME}}` | the executable name being installed |
   | `{{TAGS}}` | comma-delimited tag list from step 2 |
   | `{{SUMMARIZE}}` | the command summary from step 2 |
   | `{{DOCUMENTATION_URL}}` | the documentation URL from step 2 |
   | `{{INSTALL_METHOD_FEDORA}}` | command(s) to install on Fedora Linux 42/43 |
   | `{{INSTALL_METHOD_MAC}}` | command(s) to install on Apple Silicon macOS |
   | `{{INSTALL_METHOD_RPI}}` | command(s) to install on Raspberry Pi 5 (Debian Trixie) |
   | `{{COMMAND_PATH_FEDORA}}` | run `which <command>` after installing — e.g. `/usr/bin/<command>` or `~/.local/bin/<command>` |
   | `{{COMMAND_PATH_MAC}}` | e.g. `/opt/homebrew/bin/<command>` for brew, `~/.local/bin/<command>` for manual |
   | `{{COMMAND_PATH_RPI}}` | e.g. `/usr/bin/<command>` for apt, `~/.local/bin/<command>` for manual |

   Fill in the "Command options" section by reading the tool's `--help` output or documentation.

5. **Append TODO entries for other hosts** — for each non-current host in the user's requested OS list, append one line to `~/todo/<os>/TODO.md`:
   ```
   YYYY-MM-DD <shell command to install the tool>  # install <command_name>: <one-line summary>
   ```
   Host mapping: macOS → `~/todo/mac/TODO.md`, Fedora → `~/todo/fedora/TODO.md`, Raspberry Pi 5 → `~/todo/rpi/TODO.md`.

6. **Commit and push all affected repos** — ask for explicit confirmation before committing each repo. Stage only the relevant files (never `git add -A`):
   - `~/.dotfiles` — cheat sheet added under `home/cheats/`; commit message: `chore: install <command_name> cheat sheet`
   - `~/todo` — TODO entries appended; commit message: `chore: add <command_name> TODO entries`
   - **`~/.dotfiles` uses gitsign (Sigstore/browser OAuth)** — signing requires a browser window and will fail over SSH without a display.

## Success Criteria

- Tool is installed and `which <command>` returns the expected path on the current host
- Cheat sheet file exists at the correct path under `~/cheats/`
- TODO entries appended for all non-current hosts in the user's requested OS list
- All modified repos committed and pushed

## Notes

- Prefer `~/.local/bin/` for third-party tools; only use a system package manager if it is the tool's standard/recommended install method.
- If the tool requires config files, add them to `~/.dotfiles` via GNU Stow symlinking.
- `gitsign` commits in `~/.dotfiles` require a browser window for Sigstore OAuth — remind the user if they're over SSH without a display.
