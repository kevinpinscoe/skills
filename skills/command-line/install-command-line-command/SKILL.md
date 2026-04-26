---
name: install-command-line-command
description: Prompts me for required information before installing a command line tool and then generates a cheat sheet for it
---

# Install a command-line tool

Install a command-line tool (script or binary; assume a single file unless clarified) using the information the user provides. Then:

- Create a cheat sheet for the installed command.
- Append TODO entries to `~/todo/<os>/TODO.md` for each non-current operating system.

## Grounding and background

Before doing anything, read:

- `~/.dotfiles/CLAUDE.md` — binary install paths, gitsign warning, stow structure
- `~/todo/CLAUDE.md` — TODO entry format and folder mapping

## Requirements

- Documentation is required to correctly install the tool.
- The command name must be evaluated for collisions before installing:
  - Check OS built-ins and commands already in `PATH` (including `~/bin`, `~/tools`, and `~/.local/bin`).
  - If the new command name would collide, ask the user to rename it (or suggest a rename).
- Ask the user for:
  - One or more tags to associate with the command.
  - A short summary of what the command does. Always ask the user directly — do not infer or suggest one from docs.
  - The operating systems to support in the cheat sheet and TODOs.
    - Acceptable answers: `all` or a specific list (e.g., `fedora`, `mac`, `rpi`).

## Actions to take

### 1. Gather information

**Ask questions one at a time** — do not present multiple questions at once. Wait for the user's answer before asking the next question.

- Ask for the command name, then perform the uniqueness/collision evaluation.
  - Use `command -v`, `type -a`, and a direct check of `~/.local/bin` to detect collisions.
- Ask for a link to the best documentation to use for installation instructions.
- If installation is more complex than a single file, ask clarifying questions before proceeding.
- If multiple executables will be installed:
  - Create a separate cheat sheet for each executable.
  - Perform uniqueness/collision evaluation for each executable name.

### 2. Install on the current host

**Install location preference:** Prefer installing third-party tools to `~/.local/bin/`. However, if the tool's native installer or a system package manager (e.g. `dnf`, `brew`, `apt`, `npm`) is the standard/recommended method, use that instead — do not fight the tool's ecosystem.

Detect the current platform with `uname -s` (and `/etc/os-release` on Linux):

- **Fedora Linux**: Prefer downloading the binary to `~/.local/bin/`:
  ```bash
  curl -sSfL <download-url> -o ~/.local/bin/<command> && chmod +x ~/.local/bin/<command>
  ```
  Create `~/.local/bin/` first if it does not exist. If the tool provides a `dnf` package or official installer, that is also acceptable.
- **macOS (Apple Silicon)**: Prefer `brew install <package>` — Homebrew manages the PATH automatically. If no Homebrew formula exists, fall back to `~/.local/bin/`.
- **Raspberry Pi 5 (Debian Trixie)**: Prefer downloading to `~/.local/bin/`:
  ```bash
  curl -sSfL <download-url> -o ~/.local/bin/<command> && chmod +x ~/.local/bin/<command>
  ```
  If the tool provides an `apt` package or official installer, that is also acceptable.

If the tool requires or creates configuration files under the home directory:
- Add them to `~/.dotfiles` using the GNU Stow symlink method.
- Only `git commit`/`git push` changes to `~/.dotfiles` after explicit user confirmation.

### 3. Create the cheat sheet

`~/cheats` is a GNU Stow symlink into `~/.dotfiles/home/cheats/`, so writing here edits the dotfiles repo directly.

The cheat sheet template location depends on the OS scope requested:
- `all` → use `~/cheats/templates/all.md`, write to `~/cheats/all/<command_name>`
- `fedora` → use `~/cheats/templates/fedora.md`, write to `~/cheats/fedora/<command_name>`
- `mac` → use `~/cheats/templates/mac.md` (if it exists, else use `all.md`), write to `~/cheats/mac/<command_name>`
- `rpi` → use `~/cheats/templates/rpi.md` (if it exists, else use `all.md`), write to `~/cheats/rpi/<command_name>`

Fill in all `{{VARIABLE}}` placeholders directly when writing the file — do not update `GENERATE-CHEAT.md` or run `generate-cheat.sh` (those are for standalone, non-skill use):

| Variable | Value |
|---|---|
| `{{COMMAND_NAME}}` | the executable name being installed |
| `{{TAGS}}` | comma-delimited tag list collected from the user |
| `{{SUMMARIZE}}` | the command summary collected from the user (or inferred from docs) |
| `{{DOCUMENTATION_URL}}` | the documentation URL provided by the user |
| `{{INSTALL_METHOD_FEDORA}}` | command(s) to install on Fedora Linux 42/43 |
| `{{INSTALL_METHOD_MAC}}` | command(s) to install on Apple Silicon macOS |
| `{{INSTALL_METHOD_RPI}}` | command(s) to install on Raspberry Pi 5 (Debian Trixie) |
| `{{COMMAND_PATH_FEDORA}}` | actual installed path — run `which <command>` after installing on Fedora (e.g. `/usr/bin/<command>` for dnf, `~/.local/bin/<command>` for curl installs) |
| `{{COMMAND_PATH_MAC}}` | actual installed path — run `which <command>` after installing on macOS (e.g. `/opt/homebrew/bin/<command>` for brew) |
| `{{COMMAND_PATH_RPI}}` | actual installed path — run `which <command>` after installing on RPi (e.g. `/usr/bin/<command>` for apt, `~/.local/bin/<command>` for curl installs) |

Fill in the "Command options" section by reading the tool's `--help` output or docs.

After writing the cheat file, commit the change to `~/.dotfiles` only after explicit user confirmation.

### 4. Append TODO entries for other hosts

After installing and creating the cheat sheet, append one entry per non-current host to the appropriate `~/todo/<os>/TODO.md` file. Format — one line per entry, appended at the bottom:

```
YYYY-MM-DD <shell command to install the tool>  # install <command_name>: <one-line summary>
```

Example:
```
2026-04-24 curl -sSfL https://example.com/tool -o ~/.local/bin/tool && chmod +x ~/.local/bin/tool  # install tool: does X
```

Host mapping:
| Target host | Todo file |
|---|---|
| macOS | `~/todo/mac/TODO.md` |
| Fedora workstation | `~/todo/fedora/TODO.md` |
| Raspberry Pi 5 (Debian) | `~/todo/rpi/TODO.md` |

Only append to hosts that were included in the user's requested OS list and are not the current host. Commit changes to `~/todo` only after explicit user confirmation.

### 5. Commit and push all affected repos

After the user confirms, commit and push changes in every repository that was modified. The affected repos for a typical install are:

- `~/.dotfiles` — cheat sheet added under `home/cheats/`
- `~/todo` — TODO entries appended
- `~/skills` — SKILL.md updated (if modified during the session)

For each repo:
1. `cd` into the repo root
2. Stage only the relevant files (not `git add -A`)
3. Commit with a short message describing the change (e.g. `chore: install lfk cheat sheet`)
4. Push to the remote

**Important — `~/.dotfiles` uses gitsign (Sigstore/browser OAuth).** Remind the user that commits in `~/.dotfiles` require a browser window to complete signing and will fail over SSH without a display.
