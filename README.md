# My personal skills

There are repetitive prompts which have graduated into skills.

Many of these skills are run from the command line; over time they will become agentic.

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

```text
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
├── parzival-maintain-k-fed-config/
│   ├── SKILL.md
│   └── run.sh
├── prescription-check-for-refills/
│   ├── SKILL.md
│   ├── check-for-refills.py     # reads the prescription inventory's Next due rows
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
├── youtrack-create-alert-ticket/
│   ├── SKILL.md
│   ├── create_alert_ticket.py
│   ├── run.sh
│   └── run_inner.sh          # the work itself; run.sh wraps it in the credential broker
├── youtrack-create-a-security-triage-investigation/
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
├── youtrack-move-a-youtrack-ticket/
│   ├── SKILL.md
│   ├── run.sh
│   └── scripts/              # yt_move.py, yt-move (parzival wrapper), tests, fixtures
├── youtrack-read-updates-from-tasks-and-generate-stand-up/    # symlink → vanco-skills
├── youtrack-reconcile/                                 # symlink → vanco-skills
├── youtrack-report-a-fldw-swap-issue-and-investigate/
│   ├── SKILL.md
│   └── run.sh
├── youtrack-report-a-problem/                          # symlink → vanco-skills
├── youtrack-sync-jira-ticket-status-with-youtrack/     # symlink → vanco-skills
├── daily-run-through-my-os-todo/      # symlink → vanco-skills
├── synced/            # claude.ai skills synced in by Claude Code — tracked, see below
├── install.sh
├── sync-skill-overrides.sh   # per-host: keeps untracked skills out of model context
├── template.md
├── mise.toml          # pins Python for the skill helper scripts
├── LICENSE
├── ai-wt/             # project worktrees, one per YouTrack issue — gitignored
├── gsd-*/             # ~65 dirs — third-party, gitignored, not owned by this repo
└── ...                # this repo's own README.md, RUNBOOK.md, CLAUDE.md, etc.
```

The `skills` command reads `~/.claude/skills` by default (overridable via `SKILLS_DIR`), lists
directories that contain a `run.sh` or a `SKILL.md`, and excludes anything matched by
`~/.claude/skills/.gitignore` — which is how the `gsd-*` plugin content stays out of the
chooser without the tool needing to know anything about `get-shit-done` specifically.

### Skills synced in from claude.ai

`synced/` is not a skill directory. Claude Code writes the claude.ai account's skills into it
(`docx`, `pdf`, `pptx`, `xlsx`, `deep-research` and others), one level further down, under an
ID-named directory. Each sync is committed here as a `chore: sync claude.ai …` commit, so a
change to one of those skills shows up as a diff. `manifest.json` is tracked; the
per-machine `.last-complete-round` marker is gitignored.

Nothing in `synced/` is written or maintained in this repo, so do not edit it by hand. The
chooser does not list it, because `synced/` itself holds neither a `SKILL.md` nor a `run.sh`.
`sync-skill-overrides.sh` does not look inside it either.

### Skills bridged in from `vanco-skills`

`jira-*`, the `youtrack-*` entries marked as symlinks in the tree above, and
`daily-run-through-my-os-todo` are symlinks — their content lives
in, and is owned by, the private `~/Projects/private/vanco-skills` repo, not this one. Git
tracks only the symlinks, and they are **relative** (`../../Projects/private/vanco-skills/skills/<name>`,
resolved from `~/.claude/skills`), so the committed text is identical on every host and never needs a
local rewrite (AI-53). `install.sh` recreates them if a target goes missing or a link gets clobbered,
and rewrites an old absolute link to the relative form; see `RUNBOOK.md`. The relative text assumes
this repo is checked out at `~/.claude/skills` (the FLDW layout). Where it is not — the work Mac keeps
its clone at `~/Projects/public/skills` and wires `~/.claude/skills` with `vanco-skills`'s
`wire-claude-skills.sh` — the links dangle inside the clone (harmless: Claude Code reads only
`~/.claude/skills`), and `install.sh` leaves them untouched and says so. `vanco-skills` itself now matches this naming convention (flat
`jira-<skill-name>`/`youtrack-<skill-name>` directories with complete frontmatter) as of
WORK-193.

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

### Why every skill is user-invocable only

Claude Code puts the name and description of every skill it may invoke on its own into the
model's context at the start of **every** session. With ~40 skills here plus ~65 `gsd-*`
plugin skills, that costs tokens in every session for skills that are only ever run on purpose,
by typing `/<skill-name>` or through `skills`/`run.sh`. So none of them are model-invocable
(AI-52):

- **Skills this repo owns** set `disable-model-invocation: true` in their `SKILL.md`
  frontmatter, and so does `template.md`. That setting is tracked, so it reaches every host
  with `git pull`.
- **Skills this repo does not own** (`gsd-*`, and the `vanco-skills` symlinks) cannot carry
  that edit. `sync-skill-overrides.sh` covers them instead: for every skill that does not set
  the flag, it adds a `"<skill>": "user-invocable-only"` entry under `skillOverrides` in the
  host's `~/.claude/settings.json`. That file is per-machine and never reaches git, so the
  script is **run once on each host** after pulling, and again after a `get-shit-done` update.
  See `RUNBOOK.md`.

Neither change affects `/<skill-name>`, `skills`, or `run.sh`, which pass the `SKILL.md`
content to `claude` directly. What changes is that Claude no longer starts a skill on its own.
To make a skill model-invocable again, remove the flag from its frontmatter. Do that only
deliberately — see `~/ai/directives/when-creating-a-new-skill.md`.
