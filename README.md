# My personal skills

There are repetitive prompts which have graduated into skills.

Many of these skills are run from command line however they will become over time agentic.

## Skills TUI

The [`skills` TUI](https://github.com/kevinpinscoe/skills-tui) lets you browse and launch skills interactively from the terminal.

## Structure

Skills are three levels deep: **category directory** → **skill directory** → **`SKILL.md`**, paired
with a **`run.sh`** that launches it. Every skill directory in this repo now carries a `run.sh` —
see "Why every skill has a `run.sh`" below.

```
skills/
├── app/
│   ├── create-new-external-webapp/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── install-desktop-app/
│       ├── SKILL.md
│       └── run.sh
├── command-line/
│   └── install-command-line-command/
│       ├── SKILL.md
│       ├── run.sh
│       └── .claude/settings.local.json   # per-skill permission allowlist
├── daily/
│   ├── put-email-offers-on-my-calendar/
│   │   ├── SKILL.md
│   │   └── run.sh
│   ├── run-through-my-os-todos/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── today/
│       ├── SKILL.md
│       └── run.sh
├── decision/
│   └── kevins-values-system-decision-matrix/
│       ├── SKILL.md
│       └── run.sh
├── docker/
│   ├── check-for-or-upgrade-docker-containers-on-this-system/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── create-a-self-hosted-docker-container/
│       ├── SKILL.md
│       └── run.sh
├── food/
│   └── make-me-a-bagel/
│       ├── SKILL.md
│       └── run.sh
├── git/
│   ├── clone-a-repo/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── create-a-repo/
│       ├── SKILL.md
│       ├── run.sh
│       └── category-chooser.py   # runtime category chooser (reads profile.yml live)
├── knowledge/
│   ├── create-a-pcm-note/
│   │   ├── SKILL.md
│   │   └── run.sh
│   ├── create-a-pkm-note/
│   │   ├── SKILL.md
│   │   └── run.sh
│   ├── first-moc-level/
│   │   ├── SKILL.md
│   │   └── run.sh
│   ├── second-moc-level/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── third-moc-level/
│       ├── SKILL.md
│       └── run.sh
├── project/
│   └── review-all-checkpoints/
│       ├── SKILL.md
│       ├── RUNBOOK.md
│       ├── collect-checkpoints.py   # parses every CHECKPOINT.md the host reports
│       └── run.sh
├── raspberry-pi-5/
│   └── unplanned-restart/
│       ├── SKILL.md
│       └── run.sh
├── services/
│   └── check-improvmx-logs/
│       ├── SKILL.md
│       └── run.sh
├── task-management/
│   ├── human-todos/
│   │   ├── SKILL.md
│   │   └── run.sh
│   └── os-todo/
│       ├── SKILL.md
│       └── run.sh
└── template.md
```

In this repo, the skills live under `skills/` (so if you clone this repo to `~/skills`, that
directory is `~/skills/skills`). The `skills` command reads `~/skills/skills` by default
(overridable via `SKILLS_DIR`) and only lists directories that contain a `SKILL.md` file.

### Why every skill has a `run.sh`

When a skill directory has no `run.sh`, `skills` falls back to launching Claude Code with the
raw `SKILL.md` content as the prompt and no framing around it — which can read as more
background documentation rather than an active task to execute, instead of being acted on.
Every skill here now ships a `run.sh` that wraps its `SKILL.md` content in an explicit "this is
your active task, begin at Step 1" directive before invoking `claude`, run as a normal
interactive session (no `-p`, no `--dangerously-skip-permissions`) unless the skill is meant to
run unattended. A follow-up to make `skills-tui` itself refuse a no-`run.sh` skill directory is
tracked as `FSM-2`.
