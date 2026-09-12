---
name: youtrack-report-a-fldw-swap-issue-and-investigate
category: youtrack
description: Capture a pasted Telegram swap alert for the FLDW, investigate it with sar/atop/docker logs/journalctl and other FLDW diagnostics, and log the alert plus findings as one comment on the standing tracker issue FLDW-47.
---

# Report a FLDW Swap Issue and Investigate

> Take a pasted Telegram alert about a FLDW swap/memory-pressure event, investigate it with
> `sar`, available process/application history, Docker logs, and system messages for the
> alert's time window, then log the verbatim alert and a summary of what was found as one
> comment on the standing tracker issue
> [FLDW-47](https://youtrack.kevininscoe.com/issue/FLDW-47). Investigation and logging only —
> this skill never applies a fix.

## Scope — read this before anything else

**FLDW-47 is a permanent, never-closed tracker.** It is not worked and closed like an ordinary
issue — it accumulates one comment per swap event, indefinitely. This skill therefore:

- **Never** changes `Status`, `Assignee`, `Priority`, or any other custom field on FLDW-47.
- **Never** creates a worktree, a `CHECKPOINT.md`, or a Ghostty tab rename for this work —
  those apply to discrete units of implementation work, not to appending a diagnostic comment
  to a standing log.
- **Never** counts against Kevin's one-ticket-at-a-time policy
  (`~/ai/directives/when-creating-a-youtrack-ticket.md` §11) — commenting on an existing issue
  is not "starting work" on it in that sense, the same way filing an alert ticket doesn't touch
  the lock in `../youtrack-create-alert-ticket/`.
- **Investigates before summarizing**, but never proposes or applies a remediation — this is a
  read-only diagnostic pass, logged for the record, per the same discipline as
  `../youtrack-report-a-problem/`.

The target issue is fixed and is never asked for — every swap event logged by this skill goes
to **FLDW-47**, and only FLDW-47.

## Prerequisites

- **Runs on the FLDW** (`hostname` = `kevin`). This skill is specific to that host's swap
  configuration and diagnostic tooling; stop and say so if run elsewhere.
- **Kevin is present** — this skill is interactive. It asks Kevin to paste the alert and, if
  the alert text doesn't make it obvious, to confirm the time window to investigate. It must
  never run unattended.
- **YouTrack reachable** and an API token in OpenBao at mount `app`, secret
  `YouTrack-Claude-Code`, field `token` (**not** `app/YouTrack`, **not**
  `app/YouTrack-backups`). Credential access goes through **parzival**, never a direct `bao kv
  get` — see `../youtrack-create-alert-ticket/SKILL.md`'s Prerequisites for why
  (`~/.environment/.vault-token` was revoked under PARZIVAL-2).
  - On the FLDW, API calls can use `http://127.0.0.1:9000`; any link handed to Kevin always
    uses the FQDN `https://youtrack.kevininscoe.com`.
- `sar`/`sysstat`, `journalctl`, and `docker` available. `atop` and `zramctl` are optional —
  the investigation step says what to do when they're missing.
- Read access to `/var/log/sa/`, the systemd journal, and Docker logs for the containers under
  `/opt/containers` and `/home/containers`.

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `ISSUE_KEY` | The standing tracker issue — fixed, never asked | `FLDW-47` |
| `YT_BASE` | YouTrack base URL for API calls | `http://127.0.0.1:9000` on the FLDW |
| `YT_WEB_BASE` | YouTrack base URL for any link handed to Kevin | `https://youtrack.kevininscoe.com` |

## Instructions

### 1. Confirm this is the FLDW

```bash
hostname
```

If it does not read `kevin`, stop — this skill's diagnostics (sar, the FLDW's swap
configuration, the containers under `/opt/containers`/`/home/containers`) are specific to this
host and will not apply elsewhere.

### 2. Capture the alert, verbatim

Ask Kevin to paste the Telegram alert (or block of alerts) below, then type a line containing
only `END` and press Enter to finish (`Ctrl-D` also works). Preserve it exactly as pasted —
punctuation, line breaks, and any typo the alert itself carries. **Do not correct or tidy
machine-generated text** — this is evidence, not prose, the same rule `../youtrack-report-a-problem/`
applies to a pasted alert.

Refuse an empty paste and ask again.

### 3. Establish the investigation window

Look for a timestamp in the alert text itself — most FLDW Telegram alerts name when the check
fired. If one is present, use it as the window's center. If the alert names a duration or
threshold-breach period, use that instead.

If no usable timestamp is in the alert text, ask Kevin what time window to investigate (e.g.
"the last hour," "since this morning").

Default to a window of **30 minutes before to 15 minutes after** the alert time when nothing
more specific is given — swap pressure typically builds before the alert fires and the
consequences (OOM kills, container restarts) often land just after it. Widen the window if the
early evidence suggests the pressure started earlier.

Compute the window bounds once and reuse them for every command below:

```bash
WIN_START="<YYYY-MM-DD HH:MM:SS>"
WIN_END="<YYYY-MM-DD HH:MM:SS>"
```

### 4. Investigate — work through each diagnostic, as relevant

This is a **read-only** pass. Do not restart services, clear swap, kill processes, or change
any configuration while investigating — that requires Kevin's explicit approval and is out of
scope for this skill.

Keep a running note of **observed facts** vs. **inferences** vs. **open questions**, the same
discipline as `../youtrack-report-a-problem/` step 3 — the investigation summary in step 6
depends on that separation.

#### 4a. `sar` — memory, swap, and paging history

Confirm the collector actually ran through the window before trusting its output:

```bash
systemctl is-active sysstat
ls -la /var/log/sa/
```

Then, for the window's date (use `-f /var/log/sa/saDD` when the window is not today):

```bash
sar -r -s "$WIN_START" -e "$WIN_END"   # memory utilization (%memused, kbcommit, ...)
sar -S -s "$WIN_START" -e "$WIN_END"   # swap space utilization (%swpused, kbswpfree)
sar -W -s "$WIN_START" -e "$WIN_END"   # swapping activity (pswpin/s, pswpout/s)
sar -B -s "$WIN_START" -e "$WIN_END"   # paging activity (majflt/s, pgscank/s, pgsteal/s)
```

If `sysstat` is not installed or not running, note that as a diagnostic gap in the summary —
there is no retroactive substitute for it — and suggest `sudo -A dnf install sysstat &&
sudo -A systemctl enable --now sysstat` as a follow-up so the next event has this data.

#### 4b. What was running — available applications and processes

There is usually no exact historical process list unless one of these was already running:

```bash
which atop && systemctl is-active atop
```

- **If `atop` is running**, it keeps interval snapshots including per-process memory and swap
  usage — replay the window:
  ```bash
  atop -r /var/log/atop/atop_<YYYYMMDD> -b <HHMM> -e <HHMM>
  ```
- **If `atop` is not available**, there is no per-process history for the window. Say so
  explicitly, and fall back to the *current* state as a weaker signal, clearly labeled as
  current-not-historical:
  ```bash
  ps aux --sort=-%mem | head -20
  free -h
  ```
- As a coarser proxy for what was open, check user session activity in the window:
  ```bash
  journalctl --user --since "$WIN_START" --until "$WIN_END" --no-pager | head -100
  loginctl list-sessions
  ```

If `atop` is missing, note it as a diagnostic gap and suggest installing it (`sudo -A dnf
install atop && sudo -A systemctl enable --now atop`) as a follow-up — it is the one tool that
would make this step retroactive instead of a current-state guess next time.

#### 4c. Docker logs within the window

```bash
docker ps -a --format '{{.Names}}'
```

For each container that plausibly correlates (or all of them, if nothing stands out yet):

```bash
docker logs --since "$WIN_START" --until "$WIN_END" <container> 2>&1 | tail -200
```

Also check the daemon itself and any container the kernel OOM-killer touched:

```bash
journalctl -u docker --since "$WIN_START" --until "$WIN_END" --no-pager
```

Look for restart loops, an in-container OOM message, or a container that stopped and was
restarted by its policy — a restart with no corresponding OOM-killer log entry (4d) points at
the container's own memory limit rather than host-level swap pressure.

#### 4d. System messages — OOM, swap pressure, and general log

```bash
journalctl --since "$WIN_START" --until "$WIN_END" --no-pager

journalctl -k --since "$WIN_START" --until "$WIN_END" --no-pager \
  | grep -iE "oom|out of memory|invoked oom-killer|killed process|swap"

journalctl -u systemd-oomd --since "$WIN_START" --until "$WIN_END" --no-pager
```

Fedora runs `systemd-oomd` by default — it can act on swap/memory pressure *before* the kernel
OOM-killer ever fires, so its log is often the more relevant one. Current pressure-stall
figures are a live-only supplement, not historical, but worth capturing if the window includes
"now":

```bash
cat /proc/pressure/memory
```

#### 4e. Other FLDW-specific diagnostics — suggest and use what applies

- **Swap configuration** — confirm what kind of swap is actually in play; a disk-backed swap
  and zram behave completely differently under pressure (I/O-bound vs. CPU-bound):
  ```bash
  swapon --show
  cat /proc/swaps
  zramctl 2>/dev/null
  ```
- **Known FLDW memory-pressure correlate — the backup job.** `backup-local-disks.service`
  mirrors all of `/home` to `/home_backup` five times daily (see `~/CLAUDE.md`). Check whether
  a run overlapped the window:
  ```bash
  systemctl list-timers backup-local-disks.timer
  journalctl -u backup-local-disks.service --since "$WIN_START" --until "$WIN_END" --no-pager
  ```
- **libvirt VMs** — a running VM with a generous memory reservation is a plausible swap
  contributor:
  ```bash
  virsh list --all 2>/dev/null
  ```
- **Observability stack, if deployed** — if Prometheus/node_exporter is running for the FLDW
  (`~/Projects/private/observability`), its history is finer-grained and longer-retained than
  `sar`'s. Query it for the window if it's reachable rather than relying on `sar` alone:
  - `node_memory_SwapFree_bytes` / `node_memory_SwapTotal_bytes`
  - `rate(node_vmstat_pswpout[5m])` / `rate(node_vmstat_pswpin[5m])`
- **Disk I/O wait**, when swap is disk-backed and the symptom looks I/O-bound rather than
  CPU-bound:
  ```bash
  sar -d -s "$WIN_START" -e "$WIN_END"
  ```

Stop investigating once the evidence is sufficient to state plainly what happened during the
window — which process/container class was consuming memory, whether swap or `systemd-oomd`
or the kernel OOM-killer actually acted, and whether the diagnostic gaps above (no `sysstat`,
no `atop`) left anything unanswerable. If something remains genuinely unknown, say so in the
summary rather than guessing.

### 5. Confirm FLDW-47 is reachable

```bash
source ~/.environment/openbao/openbao-env.sh
export YT_BASE=http://127.0.0.1:9000   # FLDW; elsewhere https://youtrack.kevininscoe.com

parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -H "Accept: application/json" \
    "$YT_BASE/api/issues/FLDW-47?fields=idReadable,summary,resolved"
'
```

If this 404s or the issue is archived, stop and tell Kevin — do not silently redirect the log
to a different issue.

### 6. Compose and post one comment — alert plus investigation summary

Read the clock at the moment of posting, per
`~/ai/directives/when-creating-a-youtrack-ticket.md` §9 — never a time noted earlier in the
investigation:

```bash
date '+%Y-%m-%d %H:%M'
```

Build **one** comment in this shape — the verbatim alert first, the investigation summary
second, both in the same comment:

```text
Swap alert logged 2026-09-12 08:14

    <the pasted alert text, exactly as received, indented, unedited>

Investigation window: 2026-09-12 07:40–08:25

Observed:
- sar -S showed %swpused climbing from 4% to 61% between 07:52 and 08:10; sar -W showed
  pswpout/s peaking at 340 around 08:05.
- journalctl -u systemd-oomd recorded a swap-pressure kill of <unit> at 08:06.
- docker logs for <container> show it restarting at 08:07 with no in-container OOM message,
  consistent with the host-level oomd kill rather than the container's own memory limit.
- backup-local-disks.service ran 07:45–08:12, overlapping the pressure window.

Inference: the overlapping backup run's page-cache pressure combined with <container>'s
working set to trigger systemd-oomd's swap-pressure kill.

Open questions / diagnostic gaps: atop is not installed, so there is no per-process history
for the window — only the current process list was available as a weaker signal.

No remediation applied. This is an investigation-and-log entry only.
```

Post it as a single comment:

```bash
export COMMENT_JSON=$(python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))' <<'TEXT'
<the composed comment text from above>
TEXT
)

parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -X POST -H "Content-Type: application/json" \
    "$YT_BASE/api/issues/FLDW-47/comments" \
    --data-binary "$COMMENT_JSON"
'
```

Building the JSON with `python3 -c` rather than hand-quoting keeps the alert's own punctuation,
quotes, and line breaks from breaking the payload.

### 7. Report back to Kevin

Tell Kevin, in bare text:

1. The tracker's full FQDN URL: `https://youtrack.kevininscoe.com/issue/FLDW-47`.
2. Whether the swap pressure was actually reproduced/confirmed in the evidence, or only
   reported.
3. The one-line investigation finding — what actually happened and the evidence for it.
4. Any diagnostic gap found (missing `sysstat`, missing `atop`, observability stack
   unreachable, etc.) and the one-line fix for it, offered as a follow-up, not applied.
5. That no remediation was performed — this skill only investigates and logs.

## Success Criteria

- FLDW-47 exists, was confirmed live (not assumed), and received exactly **one new comment**
  from this run.
- That comment contains the pasted alert **verbatim**, unedited, clearly separated from the
  investigation summary that follows it.
- The summary separates observed facts from inferences and names any diagnostic gap rather
  than glossing over it.
- `Status`, `Assignee`, and every other custom field on FLDW-47 are unchanged from before this
  run.
- No worktree, `CHECKPOINT.md`, or Ghostty tab rename was created for this work.
- No service was restarted, no process was killed, no configuration was changed, and no swap
  was cleared.
- Kevin has the full FQDN URL to FLDW-47, in bare text.

## Notes

- **Why FLDW-47 and not a new `PR` ticket.** `../youtrack-create-alert-ticket/` and
  `../youtrack-report-a-problem/` both file a fresh issue per alert. This skill deliberately
  does the opposite — swap events on the FLDW are logged as an accumulating history on one
  issue, so Kevin can see the pattern over time (frequency, whether the same container recurs,
  whether a diagnostic gap keeps recurring) rather than having each event start a cold trail.
- **This skill never closes, reassigns, or reprioritizes FLDW-47.** If Kevin ever wants those
  fields set or changed, that is a separate, explicit request — not something this skill infers
  from an investigation result.
- **Escalation path.** If an investigation surfaces something bigger than routine swap
  pressure — data loss, a user-visible outage, a failure monitoring itself missed — that also
  needs an incident report under `~/ai/directives/when-writing-an-incident-report.md`. Say so
  to Kevin, but still log the comment on FLDW-47 as usual; the two records coexist.
- **Related skills:** `../youtrack-create-alert-ticket/` for a one-off alert with no standing
  tracker, `../youtrack-report-a-problem/` for a live symptom Kevin wants corroborated and
  filed as its own issue.
