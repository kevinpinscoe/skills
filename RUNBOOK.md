---
title: RUNBOOK.md — skills
tags: [runbook, operations]
vault_link: runbooks/home-kinscoe-.claude-skills.md
source_path: /home/kinscoe/.claude/skills/RUNBOOK.md
---

> 📓 Indexed in the PKM knowledge vault at `runbooks/home-kinscoe-.claude-skills.md` (symlink → this file).
>
# RUNBOOK.md — skills

## Metadata

| Field | Value |
| --- | --- |
| **Owner** | Kevin Inscoe |
| **Last Updated** | 2026-10-10 |
| **Last Tested** | 2026-08-21 |
| **Expected Duration** | Varies by skill |
| **Risk Level** | Low — this repo holds prompts and wrappers, not services |
| **Repo** | `~/.claude/skills` (GitHub `kevinpinscoe/skills`) |

---

## Purpose

> The entry point for every runbook in the `skills` repo. Covers how skills are launched and how a
> new one is added, and points at the per-skill runbooks for those that need one.

This repo is a collection of AI task automation skills, browsed and run with the `skills` Go TUI
(a separate project, `skills-tui`). It is not a service, so most skills need no runbook — the ones
that carry operational detail worth writing down have their own, listed below. No skill in this
repo runs on a timer today.

Its working tree is `~/.claude/skills` — Claude Code's own officially-recognized skill path,
shared with the ~65 `gsd-*` directories installed by the separate `get-shit-done` plugin. This
repo's `.gitignore` excludes `gsd-*`; see `README.md` → "Structure" for the full model. It also
holds `synced/`, the claude.ai skills Claude Code syncs in, which is tracked but not maintained
here.

---

## When to Use This Runbook

- **Use when:** you need to find the runbook for a particular skill, you need the general launch
  procedure, or you are adding a skill.
- **Do NOT use when:** you are operating one specific skill — go straight to its own runbook in
  the list below.

---

## Prerequisites

- [ ] Claude Code CLI at `~/.local/bin/claude`
- [ ] `mise.toml` is present at the repo root: run `mise install && mise doctor` before committing
- [ ] The `skills` TUI binary at `/usr/bin/skills`, from the `skills-tui` RPM (`dnf install skills-tui`;
      source: `github.com/kevinpinscoe/skills-tui`). `~/private-tools/skills` is a wrapper ahead of it on
      `PATH`; on this host it only hands off to that binary

---

## Stack

| Component | Details |
| --- | --- |
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

**Why:** bypasses the chooser for a skill you can name, and is how a timer would invoke one.

```bash
bash ~/.claude/skills/<skill-name>/run.sh
```

Skills without a `run.sh` are launched through the chooser, or by handing `SKILL.md` to Claude
Code yourself.

Inside a Claude Code session that is already open, type `/<skill-name>` instead. That loads the
skill into the current session and does not start a new one.

### Step 3 — Keep skills out of model context (once per host, AI-52)

**Why:** every model-invocable skill's description is loaded into every Claude Code session. This
repo's own skills opt out in their frontmatter (`disable-model-invocation: true`, tracked). The
untracked ones (`gsd-*`, `vanco-skills` symlinks) are opted out per host in
`~/.claude/settings.json` → `skillOverrides`, which git never carries. See `README.md`, "Why
skills outside `synced/` are user-invocable only".

Run after the first clone on a host, after pulling a change that adds a skill, and after a
`get-shit-done` plugin update:

```bash
git -C ~/.claude/skills pull --ff-only origin main
bash ~/.claude/skills/sync-skill-overrides.sh --check   # report only; exit 1 = gaps
bash ~/.claude/skills/sync-skill-overrides.sh           # add the missing overrides
```

The script only **adds** entries, backs up `settings.json` to `settings.json.bak-<timestamp>`
first, and keeps the file's mode (`0600`). It reports stale entries (skills no longer on disk)
but never deletes them. Restart open Claude Code sessions afterwards.

### Step 4 — Add a new skill

**Why:** every skill has the same shape, and three things break quietly when it does not: the
chooser groups by `category:`, Claude Code matches `name:` to the directory, and a missing
`disable-model-invocation` line puts the skill back into every session's context. These steps
apply to whoever adds the skill: a person, an LLM, or a coding agent.

**1. Create the directory and its two files.** The name is `<category>-<verb-noun>`, lowercase
and hyphenated. Never use the `gsd-` prefix; it is gitignored.

```bash
cd ~/.claude/skills
NAME=docker-prune-unused-images        # your skill's directory name
mkdir "$NAME"
cp template.md "$NAME/SKILL.md"
cp food-make-me-a-bagel/run.sh "$NAME/run.sh"
```

That `run.sh` is the standard interactive wrapper, shared unchanged by most skills here. It
finds the `claude` CLI, then starts a normal session with the `SKILL.md` content framed as the
active task. It needs no editing. Write a different one only when the skill must run unattended
or needs a credential broker around it; `youtrack-create-alert-ticket/run.sh` is an example.

**2. Fill in `SKILL.md`.** Edit the frontmatter first:

| Field | Rule |
| --- | --- |
| `name:` | Exactly the directory name |
| `category:` | Lowercase, hyphenated slug matching the directory prefix, e.g. `docker`, `raspberry-pi-5` |
| `description:` | One sentence |
| `disable-model-invocation: true` | Leave it. Remove it only when Kevin has asked for a skill Claude may start on its own, and say why in the skill's `## Notes` |

Then write the sections the template lists: the H1 title, the one-sentence blockquote,
Prerequisites, Parameters (optional), Instructions as explicit numbered steps, Success Criteria,
and Notes (optional). Helper scripts go in the same directory. Never put a secret, token, or
password in any of these files; this repo is published on GitHub.

**3. Update the documentation.** Add the directory to the tree under "Structure" in `README.md`.
If the skill gets its own `RUNBOOK.md`, add it under "Subdirectory Runbooks" below.

**4. Check it.**

```bash
head -6 "$NAME/SKILL.md"                          # name: must equal the directory name
test -x "$NAME/run.sh" && echo "run.sh is executable"
bash sync-skill-overrides.sh --check              # must end: ok: nothing to add
skills                                            # the skill appears under its category
```

Also run the first command under "Verification" below; it must print nothing.

**5. Commit on a branch and open a pull request against `main`.** Stage only the new directory and
the documentation you changed. In Kevin's own workflow the branch is named for the YouTrack
issue, and he merges the pull request himself.

**A skill that belongs to `vanco-skills`** is created in that repository, not here. This repo
then gets a relative symlink to it: add one entry to `LINKS` in `install.sh`, run
`bash install.sh`, and commit the symlink.

**If this fails:** a skill missing from the chooser has no `SKILL.md` or `run.sh`, or is matched
by `.gitignore`. A `--check` that reports the new skill is missing the frontmatter flag.

---

## Verification

```bash
find ~/.claude/skills -mindepth 1 -maxdepth 1 \( -type d -o -type l \) \
  ! -name 'gsd-*' ! -name '.*' ! -name ai-wt ! -name synced -print | \
  xargs -I{} sh -c 'test -e "{}/SKILL.md" -o -e "{}/run.sh" || echo "{}"'
```

**Expected output:** nothing.

**Success criteria:** every skill directory contains a `SKILL.md` or a `run.sh`. Any path printed
is a directory the TUI will not list, or a `vanco-skills` symlink whose target is missing. The
command leaves out `gsd-*`, the dot-directories, `ai-wt/` and `synced/`, none of which is a skill
directory.

```bash
bash ~/.claude/skills/sync-skill-overrides.sh --check
```

**Expected output:** ends `ok: nothing to add`, exit 0. **Success criteria:** no skill on this
host is model-invocable. In a new Claude Code session, the skill list the model is shown
contains none of this repo's skills and no `gsd-*` skill, while `/<skill-name>` still runs each
one.

---

## Rollback Procedure

1. `cd ~/.claude/skills`
2. `git log --oneline -- <skill-name>/`
3. `git checkout <good-sha> -- <skill-name>/`

---

## Escalation

| Condition | Contact | How |
| --- | --- | --- |
| A skill modified files outside this repo unexpectedly | Kevin | Report before committing anything — see the side-effect rules in `CLAUDE.md` |

---

## Subdirectory Runbooks

- [`project-review-all-checkpoints/RUNBOOK.md`](project-review-all-checkpoints/RUNBOOK.md) — reviews every `CHECKPOINT.md` on this host; on demand, not scheduled

**Not listed here:** the `jira-*` skills, `daily-run-through-my-os-todo`, and nine of the
`youtrack-*` skills are symlinks into `~/Projects/private/vanco-skills/skills/` (`install.sh` has
the full list). Their skills and runbooks belong to that repository and are maintained there — per
`when-creating-a-runbook.md` step 4, a runbook for a tool in another repo is updated in that tool's
own repo. They appear in the chooser because the TUI follows the symlinks; they are not files this
repo owns. The other five `youtrack-*` skills are owned here and have no runbook of their own.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| A skill is not listed in the chooser | No `run.sh`/`SKILL.md`, or excluded by `.gitignore` | Add one, check `.gitignore`, or launch its `run.sh` directly |
| `claude: command not found` in a `run.sh` | Non-interactive shell without `~/.local/bin` on `PATH` | The wrappers call `$HOME/.local/bin/claude` by absolute path; update the path if the CLI moved |
| A `vanco-skills` symlink (`jira-*`, some `youtrack-*`) is broken or missing | `vanco-skills` was moved, the link was clobbered, or it is an old absolute link | Run `bash ~/.claude/skills/install.sh`; it recreates the relative link (`../../Projects/private/vanco-skills/skills/<name>`) and reports `ok` for correct ones |
| `install.sh` prints `skip: … is not ~/.claude/skills` | The clone is elsewhere (the work Mac's `~/Projects/public/skills`, or an `ai-wt/` worktree), where the committed relative links cannot resolve | Expected — nothing was changed. On the Mac, `~/.claude/skills` is wired by `~/Projects/private/vanco-skills/wire-claude-skills.sh`. Set `VANCO_ROOT` only for a deliberate local rewrite |
| `git status` shows the `vanco-skills` symlinks modified after a pull | A pre-AI-53 absolute link was rewritten locally, or `VANCO_ROOT` was used | `git checkout -- <link>` to restore the committed relative text, then `bash ~/.claude/skills/install.sh` should report `ok` without changing it |
| Claude starts a skill on its own, or skill descriptions are back in every session's context | A new skill without the frontmatter flag, or new `gsd-*` skills from a plugin update | `bash ~/.claude/skills/sync-skill-overrides.sh`, and add `disable-model-invocation: true` to any skill this repo owns |
| `/<skill-name>` is not recognized | The skill was set to `off` rather than `user-invocable-only`, or the session predates the change | Check `jq .skillOverrides ~/.claude/settings.json`; restart the session |

---

## Logs

Skills run in the foreground and report to the terminal. Nothing in this repo logs anywhere else
today. A skill that is later put on a user timer would log to the journal:

```bash
journalctl --user -u <skill-name>.service -n 100
```

---

## Monitoring

> Monitoring belongs to an individual timer-driven skill, not to the repository, and is recorded in
> that skill's own runbook `## Monitoring` section. No skill here runs on a timer today.

| Field | Value |
| --- | --- |
| **Monitoring** | **Waived at the repository level** — a repo of prompts has no run to monitor |
| **Rationale** | Nothing executes at the repo level. Each unattended skill carries its own monitoring decision in its own runbook |
| **Revisit when** | Something in this repo runs on a schedule other than through a per-skill timer |
| **Approved by** | Kevin Inscoe, 2026-08-12 |

---

## Maintenance Notes

- **Last game-day test:** 2026-08-21
- **Next scheduled review:** when a skill gains or loses a timer
- **Known drift risks:**
  - `skillOverrides` in `~/.claude/settings.json` is per-host and untracked. A `get-shit-done`
    update adds `gsd-*` skills that are model-invocable until `sync-skill-overrides.sh` is re-run
    on that host (AI-52).
  - The `## Structure` tree in `README.md` and the runbook list above are both maintained by hand
    and drift as skills are added. `CLAUDE.md` requires the README tree to be updated whenever a
    skill is added, renamed, or removed; this list needs the same care.
  - The two dead legacy directories that used to sit under `skills/daily/` and
    `skills/task-management/` (an empty, no-`SKILL.md` directory and a misspelled empty one) were
    dropped entirely during the FSM-3 flattening rather than migrated — nothing to track here now.
  - `synced/` changes whenever Claude Code syncs the claude.ai skills, which leaves the working
    tree modified until the change is committed as a `chore: sync claude.ai …` commit.
