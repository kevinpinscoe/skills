# My personal skills

Repetitive prompts that have graduated into reusable Claude Code skills.

## Skills TUI

Skills in this repo are organized to be run with the [skills-tui](https://github.com/kevinpinscoe/skills-tui) — a terminal UI for browsing and executing skills via Claude Code. The binary installs to `~/skills/skills`.

They can also be run directly with the Claude CLI:

```
claude "$(cat skills/<category>/<skill>.md)"
```

## Structure

Skills are organized in two levels: **category directory** → **skill Markdown file**.

```
skills/
├── template.md
├── task-management/
├── aws/
└── ...
```
