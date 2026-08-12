# RUNBOOK.md — skills

## Metadata

| Field | Value |
|---|---|
| **Owner** | Kevin Inscoe |
| **Last Updated** | 2026-08-12 |
| **Last Tested** | 2026-08-12 |
| **Expected Duration** | Varies by skill |
| **Risk Level** | Low — this repo holds prompts and wrappers, not services |
| **Repo** | `~/skills` (GitHub `kevinpinscoe/skills`) |

---

## Purpose

> The entry point for every runbook in the `skills` repo. Covers how skills are launched, and
> points at the per-skill runbooks for those that need one.

This repo is a collection of AI task automation skills plus the `skills` Go TUI used to browse and
run them. It is not a service, so most skills need no runbook — the ones that run unattended on a
timer, or that carry operational detail worth writing down, have their own, listed below.

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
- [ ] The `skills` TUI binary at `~/skills/skills` (source: `github.com/kevinpinscoe/skills-tui`)

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

**Why:** the chooser is the normal path; it lists categories, then the skills in the chosen
category that have a `SKILL.md`.

```bash
~/skills/skills
```

**If this fails:** a skill directory missing its `SKILL.md` will not be listed — that is the
filter working, not a fault.

### Step 2 — Run a skill directly

**Why:** bypasses the chooser for a skill you can name, and is how a timer invokes one.

```bash
bash ~/skills/skills/<category>/<skill-name>/run.sh
```

Skills without a `run.sh` are launched through the chooser, or by handing `SKILL.md` to Claude
Code yourself.

---

## Verification

```bash
find ~/skills/skills -mindepth 2 -maxdepth 2 -type d '!' -exec test -e '{}/SKILL.md' ';' -print
```

**Expected output:** nothing.

**Success criteria:** every skill directory contains a `SKILL.md`. Any path printed is a directory
the TUI will not list. `-type d` does not follow symlinks, so the `Jira/` and `YouTrack/`
categories are deliberately out of scope — they belong to `vanco-skills`.

---

## Rollback Procedure

1. `cd ~/skills`
2. `git log --oneline -- skills/<category>/<skill-name>/`
3. `git checkout <good-sha> -- skills/<category>/<skill-name>/`

---

## Escalation

| Condition | Contact | How |
|---|---|---|
| A skill modified files outside this repo unexpectedly | Kevin | Report before committing anything — see the side-effect rules in `CLAUDE.md` |

---

## Subdirectory Runbooks

- [`skills/daily/put-email-offers-on-my-calendar/RUNBOOK.md`](skills/daily/put-email-offers-on-my-calendar/RUNBOOK.md) — reads Gmail offer emails and creates Google Calendar events; user timer
- [`skills/daily/read-my-gmail-for-tldr-articles/RUNBOOK.md`](skills/daily/read-my-gmail-for-tldr-articles/RUNBOOK.md) — extracts TLDR newsletter articles to the Obsidian vault; user timer, daily 10:30
- [`skills/project/review-all-checkpoints/RUNBOOK.md`](skills/project/review-all-checkpoints/RUNBOOK.md) — reviews every `CHECKPOINT.md` on this host; on demand, not scheduled

**Not listed here:** `skills/Jira/` and `skills/YouTrack/` are symlinks into
`~/Projects/private/vanco-skills/skills/`. Their skills and runbooks belong to that repository and
are maintained there — per `when-creating-a-runbook.md` step 4, a runbook for a tool in another
repo is updated in that tool's own repo. They appear in the chooser because the TUI follows the
symlinks; they are not files this repo owns.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| A skill is not listed in the chooser | Its directory has no `SKILL.md` | Add one, or launch its `run.sh` directly |
| `claude: command not found` in a `run.sh` | Non-interactive shell without `~/.local/bin` on `PATH` | The wrappers call `$HOME/.local/bin/claude` by absolute path; update the path if the CLI moved |
| A timer-driven skill did not run | User timer not enabled after a reinstall | `systemctl --user list-timers`, then enable per that skill's runbook |

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

- **Last game-day test:** 2026-08-12
- **Next scheduled review:** when a skill gains or loses a timer
- **Known drift risks:**
  - The `## Structure` tree in `README.md` and the runbook list above are both maintained by hand
    and drift as skills are added. `CLAUDE.md` requires the README tree to be updated whenever a
    skill or category is added, renamed, or removed; this list needs the same care.
  - `skills/task-management/youtraack-todo/` is empty — no `SKILL.md`, so the TUI does not list
    it. Its name is also misspelled (`youtraack`). Both are pre-existing and left alone.
