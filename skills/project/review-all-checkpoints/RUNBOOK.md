# RUNBOOK.md — review-all-checkpoints

## Metadata

| Field | Value |
|---|---|
| **Owner** | Kevin Inscoe |
| **Last Updated** | 2026-08-12 |
| **Last Tested** | 2026-08-12 — run against nine live checkpoints on the FLDW |
| **Expected Duration** | Under a minute for the collector; a few minutes for the full reviewed report |
| **Risk Level** | Low — read-only, no writes anywhere |
| **Repo** | `~/skills` (GitHub `kevinpinscoe/skills`) |

---

## Purpose

> Covers operating the `review-all-checkpoints` skill: how it finds `CHECKPOINT.md` files, how
> `collect-checkpoints.py` decides what it decides, and what to do when the report looks wrong.

A `CHECKPOINT.md` on disk means an AI session left work unfinished. Several agents work on this
host without shared context, and the FLDW loses power without warning, so these files accumulate.
This skill answers the standing question — *what is outstanding, which issue tracks it, and where
do I stand to resume it* — without opening nine files by hand.

---

## When to Use This Runbook

- **Use when:** the skill reports the wrong issue, the wrong directory, or misses a checkpoint you
  know exists; or you are changing how the parser works.
- **Do NOT use when:** you want to resume one of the reported projects. Read that project's own
  `CHECKPOINT.md` and its `## Summary` instead — this skill points at it, it does not replace it.

---

## Prerequisites

- [ ] `check-git-repos` on `PATH` — verify with `check-git-repos --version`
- [ ] `python3` available — verify with `python3 --version` (3.11+; developed against 3.14)
- [ ] `git` available, and the reported repositories readable by `kinscoe`
- [ ] `mise.toml` is present at the repo root: run `mise install && mise doctor` before committing
      changes to this skill

---

## Stack

| Component | Details |
|---|---|
| **Language / Runtime** | Python 3 (standard library only — no third-party packages), Bash wrapper |
| **External Services** | None. Nothing leaves the host; no YouTrack or forge API is called |
| **Databases / File Stores** | None. Reads `CHECKPOINT.md` files in place; writes nothing |
| **Credentials / Secrets** | None required |

---

## Step-by-Step Procedure

### Step 1 — Run the collector

**Why:** produces the deterministic half of the report. Everything the parser can know without
judgment comes from here.

```bash
cd ~/skills/skills/project/review-all-checkpoints
python3 collect-checkpoints.py --format text
```

**Expected output:**
```
~/Projects/public/vermilian
  issue    : GH-4
  resume in: ~/Projects/public/vermilian
  worktree : ~/Projects/public/vermilian/ai-wt/GH-4 (branch GH-4)
  tasks    : 9/18 done
  next     : Confirm Kevin's pull-request approval is recorded on the forge
  PR       : https://github.com/kevinpinscoe/vermilian/pull/50
```

**If this fails:** `error: check-git-repos not found on PATH` means the binary is missing from
`/usr/bin`; reinstall it. A non-zero exit from the collector is reported verbatim with its stderr.

### Step 2 — Run the full skill

**Why:** the JSON carries facts; the report carries the judgment that makes them useful — which
checkpoints are blocked on Kevin, which on each other, and which are done but retained.

```bash
bash ~/skills/skills/project/review-all-checkpoints/run.sh
```

Or launch it interactively from the skill chooser:

```bash
~/skills/skills
```

**If this fails:** `~/.local/bin/claude` not found means the Claude Code CLI moved — update the
path in `run.sh`.

### Step 3 — Review one checkpoint only

**Why:** faster than a full scan when you already know which project you care about, and the only
way to inspect a checkpoint in a repository the collector does not report.

```bash
python3 collect-checkpoints.py --path ~/Projects/public/vermilian/CHECKPOINT.md
```

`--path` is repeatable and accepts either a `CHECKPOINT.md` or a directory to search.

---

## Verification

```bash
cd ~/skills/skills/project/review-all-checkpoints
diff <(check-git-repos --checkpoint | wc -l) \
     <(python3 collect-checkpoints.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["count"])')
```

**Expected output:** no output — the counts agree.

**Success criteria:** every repository `check-git-repos --checkpoint` reports produces at least
one record. The two numbers legitimately differ when a tracking repository holds more than one
project checkpoint (`~/admin` and `/opt/containers` each can), in which case the collector's count
is the higher one. Any other mismatch is a parser fault — see Troubleshooting.

---

## Rollback Procedure

None required — the skill writes nothing. If a run was interrupted, re-run it.

If a change to `collect-checkpoints.py` broke the parser, revert the file:

1. `cd ~/skills`
2. `git log --oneline -- skills/project/review-all-checkpoints/collect-checkpoints.py`
3. `git checkout <good-sha> -- skills/project/review-all-checkpoints/collect-checkpoints.py`

---

## Escalation

| Condition | Contact | How |
|---|---|---|
| A checkpoint's own session appears wedged or contradictory | Kevin | Report it in the run's output — do not edit another session's `CHECKPOINT.md` |
| Two checkpoints are deadlocked on each other | Kevin | Name both issues and the shared resource; the unblock is his call |

---

## Related Runbooks

- [`../../../RUNBOOK.md`](../../../RUNBOOK.md) — root runbook for the `skills` repo

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| A checkpoint is missing from the report | Its repository is outside `$HOME` and not in `$CHECK_GIT_REPOS`, or it is not a git repository at all | Add the path to `$CHECK_GIT_REPOS`, or pass `--path` explicitly. By decision (2026-08-12) the skill does not sweep non-git directories |
| Wrong issue reported | The H1 does not follow `# CHECKPOINT — <ISSUE>: <what>`, so the key came from a URL or the body instead | Check `issues.mentioned` and `issues.urls` in the JSON; the summary is authoritative |
| A CVE or advisory ID reported as an issue | A new identifier scheme shaped like an issue key | Add its prefix to `NOT_AN_ISSUE` in `collect-checkpoints.py` |
| `tasks.total` is 0 on a checkpoint that plainly has tasks | The file uses a checkbox style other than `- [ ]` / `- [x]` | Widen `TASK_OPEN` / `TASK_DONE`, or treat the file as prose and rely on the summary |
| Worktree not reported | The worktree directory is not named for the issue key | The matcher accepts `<KEY>`, `<KEY>-suffix`, or a branch equal to `<KEY>`; anything else needs the summary to spot |
| Report contradicts the checkpoint | Another session ticked tasks mid-run, or the file was written before its last action completed | Re-run the collector. A checkpoint whose ticks lag its own evidence is a real and recurring state — report it, do not "fix" the file |
| `permission denied` reading a checkpoint | A root-owned path with restrictive permissions | `/opt/containers/CHECKPOINT.md` is world-readable and needs no `sudo`; anything stricter is a genuine finding worth reporting |

---

## Logs

No log files — the skill runs in the foreground and reports to the terminal.

```bash
# Re-run and keep a copy of one run's raw facts for comparison
python3 collect-checkpoints.py > /tmp/checkpoints-$(date +%Y%m%d-%H%M).json
```

---

## Monitoring

| Field | Value |
|---|---|
| **Monitoring** | **Waived** — no health check, deadman, silent-fail, or error detection |
| **Rationale** | On-demand only. No systemd unit, no timer, no unattended execution, and no side effects — there is no run that can silently fail and nothing to be deadman-detected. `when-establishing-monitoring-for-a-job-or-service.md` applies to things that run unattended; this runs only when Kevin invokes it |
| **Revisit when** | The skill gains a timer or systemd unit, or is invoked from another automation. At that point the directive applies in full and this waiver is void |
| **Approved by** | Kevin Inscoe, 2026-08-12 |

---

## Maintenance Notes

- **Last game-day test:** 2026-08-12 — run against nine live checkpoints spanning `/opt/containers`,
  `~/admin`, four `~/Projects` repos, and `~/skills` itself.
- **Next scheduled review:** when `check-git-repos` changes its `--checkpoint` output format.
- **Known drift risks:**
  - The collector parses `check-git-repos --checkpoint` line by line, expecting
    `<path> is CHECKPOINT`. A format change in that Go binary breaks the scan silently — it would
    report zero checkpoints, which is indistinguishable from a genuinely clean host. The
    Verification step above is what catches it.
  - Checkpoint conventions are set by `project-planning-with-ai.md`. If the H1 form or the
    mandatory `## Summary` heading changes there, the extraction changes with it.
  - The YouTrack project roster changes without this repo being told. The parser matches the
    *shape* of an issue key rather than a fixed project list, so a new project needs no change
    here — but a new non-issue identifier shaped like one does.
