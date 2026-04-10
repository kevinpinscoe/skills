# My personal skills

There are repetitive prompts which have graduated into skills.

Many of these skills are run from command line however they will become over time agentic.

## Skills TUI

The [`skill` TUI](https://github.com/kevinpinscoe/skills-tui) lets you browse and launch skills interactively from the terminal.

## Structure

Skills are three levels deep: **category directory** → **skill directory** → **`SKILL.md`**.

```
~/skills/skills/
├── daily/
│   └── put-email-offers-on-my-calendar/
│       └── SKILL.md
└── <category>/
    └── <skill-name>/
        └── SKILL.md
```

The `skill` command reads `~/skills/skills` by default (overridable via `SKILLS_DIR`). It only lists directories that contain a `SKILL.md` file.

