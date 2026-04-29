# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Kevin's personal collection of AI task automation skills, plus the `skill` Go CLI used to browse and execute them via Claude Code.

## Directory layout

```
~/skills/
├── CLAUDE.md               # This file
├── README.md
├── skills                  # Compiled Go binary (from github.com/kevinpinscoe/skills-tui)
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
    │       └── resume.sh
    ├── docker/
    │   └── check-for-or-upgrade-docker-containers-on-this-system/
    │       └── SKILL.md
    └── task-management/    # placeholder category, no skills yet
```

Skills are organized three levels deep: **category directory** → **skill directory** → `SKILL.md`. The `skill` CLI only lists skill directories that contain a `SKILL.md` file.

Each skill directory may also contain a `resume.sh` that resumes a prior Claude Code session for that skill (`claude --resume <session-id>`).

## The `skill` CLI

Skills (via `SKILL.md` or `run.sh`) are designed to be launched through the **skills-tui** tool, installed locally as the `skill` command. Binary lives at `~/skills/skills`. Source and full behavior documentation: https://github.com/kevinpinscoe/skills-tui.

**Behavior:**
1. Presents an interactive chooser listing category directories under `~/skills/skills` (overridable via `SKILLS_DIR`)
2. After a category is chosen, presents a second chooser listing skill directories that contain a `SKILL.md`
3. Launches Claude Code with the selected `SKILL.md` as the prompt

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

After every session, a `resume.sh` script is saved to the repo root containing the command to resume the last Claude session. This file is git-ignored and should never be committed.

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

## Claude's role

- Human-authored skills are the norm; Claude may create skills when explicitly asked
- **When creating a new skill: read `skills/template.md` first, then follow it exactly.** Place the new file at `skills/<category>/<skill-name>/SKILL.md`. YAML frontmatter is required. Use existing `SKILL.md` files as additional style reference, but `template.md` is the authoritative source of truth for structure.
- Do not modify existing skills unless asked
- When executing a skill, follow its Instructions section precisely and report against its Success Criteria
