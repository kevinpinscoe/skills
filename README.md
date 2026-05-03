# My personal skills

There are repetitive prompts which have graduated into skills.

Many of these skills are run from command line however they will become over time agentic.

## Skills TUI

The [`skill` TUI](https://github.com/kevinpinscoe/skills-tui) lets you browse and launch skills interactively from the terminal.

## Structure

Skills are three levels deep: **category directory** → **skill directory** → **`SKILL.md`**.

```
skills/
├── app/
│   └── install-desktop-app/
│       └── SKILL.md
├── command-line/
│   └── install-command-line-command/
│       └── SKILL.md
├── daily/
│   ├── put-email-offers-on-my-calendar/
│   │   └── SKILL.md
│   ├── read-my-gmail-for-tldr-articles/
│   │   └── SKILL.md
│   └── run-through-my-os-todos/
│       └── SKILL.md
├── docker/
│   ├── check-for-or-upgrade-docker-containers-on-this-system/
│   │   └── SKILL.md
│   └── create-a-self-hosted-docker-container/
│       └── SKILL.md
├── food/
│   └── make-me-a-bagel/
│       └── SKILL.md
├── git/
│   ├── clone-a-repo/
│   │   └── SKILL.md
│   └── create-a-repo/
│       └── SKILL.md
└── template.md
```

In this repo, the skills live under `skills/` (so if you clone this repo to `~/skills`, that directory is `~/skills/skills`). The `skill` command reads `~/skills/skills` by default (overridable via `SKILLS_DIR`) and only lists directories that contain a `SKILL.md` file.
