# Skills Repo — Claude Guide

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
    ├── task-management/    # Task management related skills
    ├── aws/                # AWS-related skills
```

Skills are organized in two levels: **category directory** → **skill Markdown file**.

## The `skill` CLI

Binary lives at `~/skills/skills`. Source is at https://github.com/kevinpinscoe/skills-tui.

**Behavior:**
1. Presents an interactive chooser listing category directories under `~/skills/skills`
2. After a category is chosen, presents a second chooser listing skill files in that category
3. Launches Claude Code with the selected skill file as the prompt

## Skill file format

See `skills/template.md` for the canonical template. Every skill file should have:

- **H1 title** — name of the skill
- **Description** — one-sentence summary
- **Prerequisites** — required tools, credentials, or state
- **Parameters** _(optional)_ — runtime inputs the human can provide
- **Instructions** — explicit steps for Claude to execute
- **Success Criteria** — how to verify the task completed correctly
- **Notes** _(optional)_ — caveats, edge cases, related skills

## Naming conventions

- Category directories: lowercase, hyphenated (e.g. `task-management`, `aws`)
- Skill files: lowercase, hyphenated, descriptive verb-noun (e.g. `check-backup-is-current.md`, `create-task-for-inbox.md`)

## Claude's role

- Human-authored skills are the norm; Claude may create skills when explicitly asked
- When creating a skill, follow the template in `skills/template.md` exactly
- Do not modify existing skills unless asked
- When executing a skill, follow its Instructions section precisely and report against its Success Criteria
