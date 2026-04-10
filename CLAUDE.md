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
    └── daily/              # Category directory
        └── put-email-offers-on-my-calendar/
            ├── SKILL.md    # Skill definition
            └── resume.sh   # claude --resume <session-id> helper
```

Skills are organized in three levels: **category directory** → **skill directory** → `SKILL.md`.

Each skill directory may also contain a `resume.sh` that resumes a prior Claude Code session for that skill (`claude --resume <session-id>`).

## The `skill` CLI

Binary lives at `~/skills/skills`. Source is at https://github.com/kevinpinscoe/skills-tui.

**Behavior:**
1. Presents an interactive chooser listing category directories under `~/skills/skills`
2. After a category is chosen, presents a second chooser listing skill directories in that category
3. Launches Claude Code with the selected `SKILL.md` as the prompt

## Skill file format

See `skills/template.md` for the canonical template. Every `SKILL.md` should have:

- **H1 title** — name of the skill
- **Description** — one-sentence summary (as a blockquote `>`)
- **Prerequisites** — required tools, credentials, or state
- **Parameters** _(optional)_ — runtime inputs the human can provide (table format)
- **Instructions** — explicit numbered steps for Claude to execute
- **Success Criteria** — how to verify the task completed correctly
- **Notes** _(optional)_ — caveats, edge cases, related skills

## Naming conventions

- Category directories: lowercase, hyphenated (e.g. `daily`, `aws`)
- Skill directories: lowercase, hyphenated, descriptive verb-noun (e.g. `put-email-offers-on-my-calendar`)
- Skill file inside each directory is always named `SKILL.md`

## Session resumption

After every session, a `resume.sh` script is saved to the repo root containing the command to resume the last Claude session. This file is git-ignored and should never be committed.

## Claude's role

- Human-authored skills are the norm; Claude may create skills when explicitly asked
- When creating a skill, follow the template in `skills/template.md` exactly, placing it at `skills/<category>/<skill-name>/SKILL.md`
- Do not modify existing skills unless asked
- When executing a skill, follow its Instructions section precisely and report against its Success Criteria
