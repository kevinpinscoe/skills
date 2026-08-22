# My personal skills

There are repetitive prompts which have graduated into skills.

Many of these skills are run from command line however they will become over time agentic.

## Skills TUI

The [`skills` TUI](https://github.com/kevinpinscoe/skills-tui) lets you browse and launch skills interactively from the terminal.

## Structure

This repo's working tree lives at **`~/.claude/skills`** — Claude Code's own
officially-recognized skill path — flat, one level deep: **skill directory** → **`SKILL.md`**,
paired with a **`run.sh`** that launches it. That same directory also holds ~65 `gsd-*`
directories installed by the separate `get-shit-done` Claude Code plugin; this repo's
`.gitignore` excludes `gsd-*` so that third-party content is never vendored or tracked here.
Every skill directory in this repo carries a `run.sh` — see "Why every skill has a `run.sh`"
below.

Directory names carry their old category as a naming-convention prefix
(`docker-create-a-self-hosted-docker-container`) purely for human browsability — there is no
category subdirectory. `skills-tui` determines a skill's actual category from a `category:`
field in its `SKILL.md` frontmatter, never from the directory name (several categories are
themselves multi-hyphen — `raspberry-pi-5`, `task-management`, `command-line` — so parsing the
prefix back out of the name would be ambiguous).

```
~/.claude/skills/
├── app-create-new-external-webapp/
│   ├── SKILL.md
│   └── run.sh
├── app-install-desktop-app/
│   ├── SKILL.md
│   └── run.sh
├── command-line-install-command-line-command/
│   ├── SKILL.md
│   └── run.sh
├── daily-put-email-offers-on-my-calendar/
│   ├── SKILL.md
│   └── run.sh
├── daily-run-through-my-os-todos/
│   ├── SKILL.md
│   └── run.sh
├── daily-today/
│   ├── SKILL.md
│   └── run.sh
├── decision-kevins-values-system-decision-matrix/
│   ├── SKILL.md
│   └── run.sh
├── docker-check-for-or-upgrade-docker-containers-on-this-system/
│   ├── SKILL.md
│   └── run.sh
├── docker-create-a-self-hosted-docker-container/
│   ├── SKILL.md
│   └── run.sh
├── food-make-me-a-bagel/
│   ├── SKILL.md
│   └── run.sh
├── git-clone-a-repo/
│   ├── SKILL.md
│   └── run.sh
├── git-create-a-repo/
│   ├── SKILL.md
│   ├── run.sh
│   └── category-chooser.py   # runtime category chooser (reads profile.yml live)
├── knowledge-create-a-pcm-note/
│   ├── SKILL.md
│   └── run.sh
├── knowledge-create-a-pkm-note/
│   ├── SKILL.md
│   └── run.sh
├── knowledge-first-moc-level/
│   ├── SKILL.md
│   └── run.sh
├── knowledge-second-moc-level/
│   ├── SKILL.md
│   └── run.sh
├── knowledge-third-moc-level/
│   ├── SKILL.md
│   └── run.sh
├── project-review-all-checkpoints/
│   ├── SKILL.md
│   ├── RUNBOOK.md
│   ├── collect-checkpoints.py   # parses every CHECKPOINT.md the host reports
│   └── run.sh
├── raspberry-pi-5-unplanned-restart/
│   ├── SKILL.md
│   └── run.sh
├── services-check-improvmx-logs/
│   ├── SKILL.md
│   └── run.sh
├── task-management-human-todos/
│   ├── SKILL.md
│   └── run.sh
├── task-management-os-todo/
│   ├── SKILL.md
│   └── run.sh
├── jira-create-a-jira-ticket/         # symlink → vanco-skills, see below
├── jira-create-jira-tickets-bookmark/ # symlink → vanco-skills
├── jira-update-menu-app-yaml-from-jira-html/  # symlink → vanco-skills
├── youtrack-check-for-duplicate-tickets-and-tag/       # symlink → vanco-skills
├── youtrack-create-a-youtrack-project/                 # symlink → vanco-skills
├── youtrack-create-ticket-in-youtrack/                 # symlink → vanco-skills
├── youtrack-get-my-assigned-tickets-from-jira-into-youtrack/  # symlink → vanco-skills
├── youtrack-insert-specific-jira-ticket-in-youtrack/   # symlink → vanco-skills
├── youtrack-read-updates-from-tasks-and-generate-stand-up/    # symlink → vanco-skills
├── youtrack-reconcile/                                 # symlink → vanco-skills
├── youtrack-report-a-problem/                          # symlink → vanco-skills
├── youtrack-sync-jira-ticket-status-with-youtrack/     # symlink → vanco-skills
├── daily-run-through-my-os-todo/      # symlink → vanco-skills
├── install.sh
├── template.md
├── gsd-*/             # ~65 dirs — third-party, gitignored, not owned by this repo
└── ...                # this repo's own README.md, RUNBOOK.md, CLAUDE.md, etc.
```

The `skills` command reads `~/.claude/skills` by default (overridable via `SKILLS_DIR`), lists
directories that contain a `run.sh` or a `SKILL.md`, and excludes anything matched by
`~/.claude/skills/.gitignore` — which is how the `gsd-*` plugin content stays out of the
chooser without the tool needing to know anything about `get-shit-done` specifically.

### Skills bridged in from `vanco-skills`

`jira-*`, `youtrack-*`, and `daily-run-through-my-os-todo` are symlinks — their content lives
in, and is owned by, the private `~/Projects/private/vanco-skills` repo, not this one. Git
tracks only the symlinks. `install.sh` recreates them if a target goes missing or a link gets
clobbered; see `RUNBOOK.md`. A companion restructuring of `vanco-skills` itself, to match this
naming convention and add complete frontmatter to those skills, is tracked separately.

### Why every skill has a `run.sh`

When a skill directory has no `run.sh`, `skills` falls back to launching Claude Code with the
raw `SKILL.md` content as the prompt and no framing around it — which can read as more
background documentation rather than an active task to execute, instead of being acted on.
Every skill here now ships a `run.sh` that wraps its `SKILL.md` content in an explicit "this is
your active task, begin at Step 1" directive before invoking `claude`, run as a normal
interactive session (no `-p`, no `--dangerously-skip-permissions`) unless the skill is meant to
run unattended. An earlier ticket, `FSM-2`, tried to make `skills-tui` itself refuse a
no-`run.sh` skill directory — it's now `Wont do`, superseded by this flat + `.gitignore`-filtered
layout (`FSM-3`), which solves the same underlying problem (distinguishing "mine" from
"bundled") without needing `run.sh` presence as the signal.
