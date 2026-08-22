---
title: RUNBOOK.md — skills
tags: [runbook, operations]
vault_link: runbooks/home-kinscoe-skills.md
source_path: /home/kinscoe/.claude/skills/RUNBOOK.md
---

> 📓 Indexed in the PKM knowledge vault at `runbooks/home-kinscoe-skills.md` (symlink → this file).
# RUNBOOK.md — skills

## Metadata

| Field | Value |
|---|---|
| **Owner** | Kevin Inscoe |
| **Last Updated** | 2026-08-21 |
| **Last Tested** | 2026-08-21 |
| **Expected Duration** | Varies by skill |
| **Risk Level** | Low — this repo holds prompts and wrappers, not services |
| **Repo** | `~/.claude/skills` (GitHub `kevinpinscoe/skills`) |

---

## Purpose

> The entry point for every runbook in the `skills` repo. Covers how skills are launched, and
> points at the per-skill runbooks for those that need one.

This repo is a collection of AI task automation skills plus the `skills` Go TUI used to browse and
run them. It is not a service, so most skills need no runbook — the ones that run unattended on a
timer, or that carry operational detail worth writing down, have their own, listed below.

Its working tree is `~/.claude/skills` — Claude Code's own officially-recognized skill path,
shared with the ~65 `gsd-*` directories installed by the separate `get-shit-done` plugin. This
repo's `.gitignore` excludes `gsd-*`; see `README.md` → "Structure" for the full model.

---

## When to Use This Runbook

- **Use when:** you need to find the runbook for a particular skill, or you need the general
  launch procedure.
- **Do NOT use when:** you are operating one specific skill — go straight to its own runbook in
  the list below.

---

## Prerequisites

- [ ] Claude Code CLI at `~/.local/bin/claude`
- [ ] `mise.toml` is present at the repo root: run `mise install && mise doctor` before committing
- [ ] The `skills` TUI binary at `~/.local/bin/skills` (source: `github.com/kevinpinscoe/skills-tui`)

---

## Stack

| Component | Details |
|---|---|
| **Language / Runtime** | Markdown prompts; Bash `run.sh` wrappers; occasional Python helper scripts; Go TUI |
| **External Services** | Per skill — Gmail, Google Calendar, YouTrack, and Gitea appear in various skills |
| **Databases / File Stores** | None at the repo level |
| **Credentials / Secrets** | Never stored here. Secrets live in OpenBao — see `~/ai/directives/storing-secrets.md` |

---

## Step-by-Step Procedure

### Step 1 — Launch a skill interactively

**Why:** the chooser is the normal path; it lists every skill under `~/.claude/skills` that has
a `run.sh` or a `SKILL.md` and is not excluded by `.gitignore`.

```bash
skills
```

**If this fails:** a skill directory missing both `run.sh` and `SKILL.md`, or matched by
`.gitignore` (e.g. `gsd-*`), will not be listed — that is the filter working, not a fault.

### Step 2 — Run a skill directly

**Why:** bypasses the chooser for a skill you can name, and is how a timer invokes one.

```bash
bash ~/.claude/skills/<skill-name>/run.sh
```

Skills without a `run.sh` are launched through the chooser, or by handing `SKILL.md` to Claude
Code yourself.

---

## Verification

```bash
find ~/.claude/skills -mindepth 1 -maxdepth 1 -type d -name 'gsd-*' -prune -o \
  -mindepth 1 -maxdepth 1 -type d -print | \
  xargs -I{} sh -c 'test -e "{}/SKILL.md" -o -e "{}/run.sh" || echo "{}"'
```

**Expected output:** nothing.

**Success criteria:** every non-`gsd-*` directory contains a `SKILL.md` or a `run.sh`. Any path
printed is a directory the TUI will not list.

---

## Rollback Procedure

1. `cd ~/.claude/skills`
2. `git log --oneline -- <skill-name>/`
3. `git checkout <good-sha> -- <skill-name>/`

---

## Escalation

| Condition | Contact | How |
|---|---|---|
| A skill modified files outside this repo unexpectedly | Kevin | Report before committing anything — see the side-effect rules in `CLAUDE.md` |

---

## Subdirectory Runbooks

- [`daily-put-email-offers-on-my-calendar/RUNBOOK.md`](daily-put-email-offers-on-my-calendar/RUNBOOK.md) — reads Gmail offer emails and creates Google Calendar events; user timer
- [`project-review-all-checkpoints/RUNBOOK.md`](project-review-all-checkpoints/RUNBOOK.md) — reviews every `CHECKPOINT.md` on this host; on demand, not scheduled

**Not listed here:** `jira-*`, `youtrack-*`, and `daily-run-through-my-os-todo` are symlinks into
`~/Projects/private/vanco-skills/skills/`. Their skills and runbooks belong to that repository and
are maintained there — per `when-creating-a-runbook.md` step 4, a runbook for a tool in another
repo is updated in that tool's own repo. They appear in the chooser because the TUI follows the
symlinks; they are not files this repo owns.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| A skill is not listed in the chooser | No `run.sh`/`SKILL.md`, or excluded by `.gitignore` | Add one, check `.gitignore`, or launch its `run.sh` directly |
| `claude: command not found` in a `run.sh` | Non-interactive shell without `~/.local/bin` on `PATH` | The wrappers call `$HOME/.local/bin/claude` by absolute path; update the path if the CLI moved |
| A timer-driven skill did not run | User timer not enabled after a reinstall | `systemctl --user list-timers`, then enable per that skill's runbook |
| A `jira-*`/`youtrack-*` symlink is broken or missing | `vanco-skills` was moved, or the link was clobbered | Run `bash ~/.claude/skills/install.sh` to recreate it |

---

## Logs

Skills run in the foreground and report to the terminal. Timer-driven skills log to the journal:

```bash
journalctl --user -u <skill-name>.service -n 100
```

---

## Monitoring

> Monitoring belongs to the individual timer-driven skills, not to the repository. See each
> skill's own runbook `## Monitoring` section.

| Field | Value |
|---|---|
| **Monitoring** | **Waived at the repository level** — a repo of prompts has no run to monitor |
| **Rationale** | Nothing executes at the repo level. Each unattended skill carries its own monitoring decision in its own runbook |
| **Revisit when** | Something in this repo runs on a schedule other than through a per-skill timer |
| **Approved by** | Kevin Inscoe, 2026-08-12 |

---

## Maintenance Notes

- **Last game-day test:** 2026-08-21
- **Next scheduled review:** when a skill gains or loses a timer
- **Known drift risks:**
  - The `## Structure` tree in `README.md` and the runbook list above are both maintained by hand
    and drift as skills are added. `CLAUDE.md` requires the README tree to be updated whenever a
    skill is added, renamed, or removed; this list needs the same care.
  - The two dead legacy directories that used to sit under `skills/daily/` and
    `skills/task-management/` (an empty, no-`SKILL.md` directory and a misspelled empty one) were
    dropped entirely during the FSM-3 flattening rather than migrated — nothing to track here now.
  - This file's own `vault_link` symlink in the PKM vault (`runbooks/home-kinscoe-skills.md`)
    still points at the pre-FSM-3 path and needs repointing once this repo's working tree is
    physically re-homed from `~/skills` to `~/.claude/skills`.
