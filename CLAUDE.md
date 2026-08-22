# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Kevin's personal collection of AI task automation skills, plus the `skills` Go CLI used to browse and execute them via Claude Code.

## Directory layout

```
~/skills/
├── CLAUDE.md               # This file
├── README.md
└── skills/
    ├── template.md         # Template for new skill files
    ├── app/
    │   └── install-desktop-app/
    │       └── SKILL.md
    ├── command-line/
    │   └── install-command-line-command/
    │       ├── SKILL.md
    │       └── .claude/settings.local.json   # per-skill permission allowlist
    ├── daily/
    │   └── put-email-offers-on-my-calendar/
    │       ├── SKILL.md
    ├── docker/
    │   └── check-for-or-upgrade-docker-containers-on-this-system/
    │       └── SKILL.md
    └── task-management/
    │   └── human-todos/
    │       └── SKILL.md
```

Skills are organized three levels deep: **category directory** → **skill directory** → `SKILL.md` (optionally paired with a `run.sh`). The `skills` CLI only lists skill directories that contain a `SKILL.md` file.

## The `skills` CLI

Skills (via `SKILL.md` or `run.sh`) are designed to be launched through the **skills-tui** tool, installed as the system `skills` command — on this host (Fedora) via `dnf install skills-tui` from the `kevinpinscoe` RPM repo (source: https://github.com/kevinpinscoe/rpm), landing at `/usr/bin/skills`. The binary is **not** part of this repo; `~/skills/skills` is this repo's skill-content directory, which the tool reads as its default `SKILLS_DIR` (overridable via the env var of that name). Source and full behavior documentation: https://github.com/kevinpinscoe/skills-tui.

**Behavior:**
1. Presents an interactive chooser listing category directories under `~/skills/skills` (overridable via `SKILLS_DIR`)
2. After a category is chosen, presents a second chooser listing skill directories that contain a `run.sh` or a `SKILL.md`
3. If the skill directory has a `run.sh`, changes into that directory and executes it (stdin wired through); otherwise launches Claude Code with the `SKILL.md` content as the prompt — **prefer giving every skill a `run.sh`** (see `FSM-2`): the bare-`SKILL.md` fallback passes the content with no framing, which Claude Code can mistake for background documentation instead of an active task.

## Skill file format

See `skills/template.md` for the canonical template. **YAML frontmatter is required** on every `SKILL.md`. When creating a new skill, read the existing `SKILL.md` files in this repo as reference for style and structure.

Every `SKILL.md` must begin with YAML frontmatter:

```markdown
---
name: skill-directory-name
description: One sentence describing what this skill does.
---

# Skill Title
...
```

Required sections after frontmatter:
- **H1 title** — name of the skill
- **Description** — one-sentence summary (as a blockquote `>`)
- **Prerequisites** — required tools, credentials, or state
- **Parameters** _(optional)_ — runtime inputs the human can provide (table format)
- **Instructions** — explicit numbered steps for Claude to execute
- **Success Criteria** — how to verify the task completed correctly
- **Notes** _(optional)_ — caveats, edge cases, related skills

## Per-skill Claude settings

A skill directory may contain a `.claude/settings.local.json` to grant skill-specific permissions (e.g. allowing certain `Bash` patterns). Use this when a skill needs permissions beyond the project defaults.

## Naming conventions

- Category directories: lowercase, hyphenated (e.g. `daily`, `aws`)
- Skill directories: lowercase, hyphenated, descriptive verb-noun (e.g. `put-email-offers-on-my-calendar`)
- Skill file inside each directory is always named `SKILL.md`

## Session resumption

Some tools may generate small helper scripts to resume prior sessions. Keep these untracked and out of documentation.

## Committing side-effect changes

Skills frequently modify files outside this repo. Before committing or pushing any changes in these directories, **always confirm with the user first**:

| Directory | Repo |
|---|---|
| `~/.dotfiles` | dotfiles repo |
| `~/tools` | tools repo |
| `~/todo` | todo repo |
| `~/ai` | ai repo |
| `~/.environment` | environment repo |

After confirmation, commit only the relevant files (not `git add -A`) and push to the remote origin.

## Cross-host TODO entries

If a skill installs or configures something on this host, **ask the user** whether the same action should be added as a TODO for the other hosts (`~/todo/mac/TODO.md`, `~/todo/rpi/TODO.md`) before appending anything — the action may not be applicable on those platforms.

## Keeping README.md current

**Always update `README.md` when any of the following change in this repo:**

- A new skill directory is added or removed
- A new category directory is added or removed
- A skill is renamed or moved

The `## Structure` tree in `README.md` must exactly reflect the directories that contain a `SKILL.md` file. After updating skills, update the tree before committing — the README and the directory layout must never diverge.

## Claude's role

- Human-authored skills are the norm; Claude may create skills when explicitly asked
- **When creating a new skill: read `skills/template.md` first, then follow it exactly.** Place the new file at `skills/<category>/<skill-name>/SKILL.md`. YAML frontmatter is required. Use existing `SKILL.md` files as additional style reference, but `template.md` is the authoritative source of truth for structure.
- **When creating or modifying any skill: update `README.md` to reflect the current directory layout before committing.**
- Do not modify existing skills unless asked
- When executing a skill, follow its Instructions section precisely and report against its Success Criteria
