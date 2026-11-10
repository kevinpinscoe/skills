---
name: youtrack-report-a-fldw-dns-issue-and-investigate
category: youtrack
description: Capture a pasted alert or symptom about a FLDW DNS lookup failure or resolver timeout, investigate it with systemd-resolved, resolvectl, dockerd resolver logs and other FLDW diagnostics, and log the evidence plus findings as one comment on the standing tracker issue FLDW-117.
disable-model-invocation: true
---

# Report a FLDW DNS Issue and Investigate

> Take a pasted Telegram alert, failed-job output, or described symptom about a FLDW DNS lookup
> failure or resolver timeout, investigate it with the `systemd-resolved` journal,
> `resolvectl`, dockerd's embedded-resolver log, and system messages for that time window, then
> log the verbatim input and a summary of what was found as one comment on the standing tracker
> issue [FLDW-117](https://youtrack.kevininscoe.com/issue/FLDW-117). Investigation and logging
> only — this skill never applies a fix.

## Scope — read this before anything else

**FLDW-117 is a long-running tracker, not an ordinary issue.** It collects one comment per DNS
event so the pattern can be seen over time: the failure rate, the names affected, and whether
failures line up with DNSSEC failures or resolver cache flushes. Its title ("Investigate DNS
lookup failures and upstream timeouts left after FLDW-115") and its current `Status` are expected,
not a mismatch to flag. Closing it is Kevin's decision, never this skill's. This skill therefore:

- **Never** changes `Status`, `Assignee`, `Priority`, or any other field on FLDW-117.
- **Never** creates a worktree or a `CHECKPOINT.md`. Those are for units of implementation work,
  not for adding a diagnostic comment to a standing log. The Ghostty tab **is** renamed while the
  investigation runs (step 1 and step 7). That is a live-status label, not the ticket-key
  convention in `~/ai/directives/when-creating-a-youtrack-ticket.md` §8, which does not apply
  because this skill never moves FLDW-117 to `In Progress` or `Done`.
- **Never** counts against Kevin's one-ticket-at-a-time policy
  (`~/ai/directives/when-creating-a-youtrack-ticket.md` §11). Commenting on an existing issue is
  not starting work on it.
- **Investigates before summarizing**, but never proposes or applies a remediation. It does not
  change the DNSSEC mode, upstream servers, `/etc/hosts`, Docker's DNS settings, or any job's
  retry logic. FLDW-117 says plainly that no fix is approved yet, and any fix needs Kevin's
  approval first.

The target issue is fixed and never asked for: every DNS event this skill logs goes to
**FLDW-117**, and only FLDW-117, for as long as it stays open. Once Kevin closes it, this skill
needs a new target, and that is his choice (see step 5).

## Prerequisites

- **Runs on the FLDW** (`hostname` = `kevin`). The resolver setup (`systemd-resolved` with
  DNS-over-TLS upstreams from FLDW-115, and Docker's embedded resolver forwarding to
  `127.0.0.53`) is specific to that host. Stop and say so if run elsewhere.
- **Kevin is present.** This skill is interactive: it asks for the alert or symptom and, when the
  text gives no time, for the window to investigate. It must never run unattended.
- **YouTrack reachable**, with the `Claude_Code` credential brokered by **parzival** (identity
  `ai`, profile `youtrack-claude-code`). Never a direct `bao kv get`, and never `parzival get`.
  - On the FLDW, API calls use `http://127.0.0.1:9000`. Any link handed to Kevin uses
    `https://youtrack.kevininscoe.com`.
- `journalctl`, `resolvectl`, and `docker` available. `dig` (from `bind-utils`) is optional;
  step 4f says what to do without it.
- Read access to the systemd journal and to Docker logs.

## Parameters

| Name | Description | Default |
| ---- | ----------- | ------- |
| `ISSUE_KEY` | The standing tracker issue — fixed, never asked | `FLDW-117` |
| `YT_BASE` | YouTrack base URL for API calls | `http://127.0.0.1:9000` on the FLDW |
| `YT_WEB_BASE` | YouTrack base URL for any link handed to Kevin | `https://youtrack.kevininscoe.com` |

## Instructions

### 1. Confirm this is the FLDW

```bash
hostname
```

If it does not read `kevin`, stop.

Then mark the tab as investigating:

```bash
set-ghostty-tab-name DNS
```

This is a live-status label only. It stays `DNS` for the rest of the run and becomes `DNSc` in
step 7 once the comment is posted, whether or not anything actionable was found.

### 2. Capture the alert or symptom, verbatim

Ask Kevin to paste what prompted this run, then type a line containing only `END` and press Enter
to finish (`Ctrl-D` also works). Any of these is valid input:

- a Telegram alert (for example a health check that got no response, like
  `check-apple-health-receiver` during a resolver burst);
- the failing output of a job or command (`Could not resolve host: …`,
  `Temporary failure in name resolution`, `i/o timeout`);
- a short description of the symptom in Kevin's own words, with a time if he has one.

Keep it exactly as pasted: punctuation, line breaks, and any typo the alert itself carries.
**Do not correct or tidy machine-generated text.** It is evidence, not prose. Refuse an empty
paste and ask again.

### 3. Establish the investigation window

Use a timestamp in the pasted text as the window's centre. If there is none, ask Kevin what
window to investigate ("the last hour", "overnight", "since 03:00").

When nothing more specific is given, default to **15 minutes before to 15 minutes after** the
event. Resolver timeout bursts on the FLDW have lasted from one minute to about four (FLDW-117's
PR-112 evidence), so a wide window mostly adds noise. Widen it if the evidence shows the burst
started earlier or ran on.

Compute the bounds once and reuse them for every command below:

```bash
WIN_START="<YYYY-MM-DD HH:MM:SS>"
WIN_END="<YYYY-MM-DD HH:MM:SS>"
```

### 4. Investigate — work through each diagnostic, as relevant

This is a **read-only** pass. Do not restart `systemd-resolved`, flush caches
(`resolvectl flush-caches`), edit resolver configuration, restart containers, or re-run failed
jobs. Each of those changes the evidence, and each needs Kevin's explicit approval.

Keep separate notes of **observed facts**, **inferences**, and **open questions**. The summary in
step 6 depends on that separation.

#### 4a. Failed lookups in the window — who failed, and for which names

```bash
journalctl --since "$WIN_START" --until "$WIN_END" --no-pager -o short-iso \
  | grep -iE 'Temporary failure in name resolution|Name or service not known|no such host|i/o timeout.*:53|could not resolve host|could not resolve hostname|EAI_AGAIN|getaddrinfo'
```

For each hit, note the time, the unit or job, and the name that failed. Then answer FLDW-117's
question 3: are the failed names all `kevininscoe.com` names (Linode authoritative DNS), or are
other domains affected too?

#### 4b. dockerd's embedded resolver — timeout bursts

Containers resolve through dockerd's embedded resolver, which forwards to the stub at
`127.0.0.53`. Its timeouts are the clearest record of a burst:

```bash
journalctl -u docker --since "$WIN_START" --until "$WIN_END" --no-pager -o short-iso \
  | grep 'failed to query external DNS server'
```

Count them per minute, the same way FLDW-117's PR-112 comment does, so the entries can be
compared with each other:

```bash
journalctl -u docker --since "$WIN_START" --until "$WIN_END" --no-pager \
  | grep 'failed to query external DNS server' \
  | awk '{print $1, $2, substr($3,1,5)}' | uniq -c
```

Note the names in the `question=` part of those lines.

#### 4c. `systemd-resolved` — DNSSEC failures, cache flushes, upstream changes

```bash
journalctl -u systemd-resolved --since "$WIN_START" --until "$WIN_END" --no-pager -o short-iso
```

Look for three things in particular:

- **DNSSEC validation failures** (`DNSSEC validation failed for question … failed-auxiliary` or
  `no-signature`). FLDW-117 runs `DNSSEC=allow-downgrade` and asks whether failures line up with
  these (question 2). Note whether a failed name from 4a was preceded by a DNSSEC failure for the
  same name.
- **Cache flushes** (`Flushed all caches.`). These happen every time a Docker container starts or
  stops, roughly 40–60 times a day, and each one sends more lookups upstream. Note whether a
  flush came just before the burst.
- **Upstream server changes or degraded feature sets** (`Switching to DNS server …`,
  `Using degraded feature set …`). These point at a problem with a particular upstream.

To see whether the window's DNSSEC failure count is unusual, compare it with the day as a whole:

```bash
journalctl -u systemd-resolved --since "<window's date> 00:00" --until "<window's date> 23:59:59" \
  --no-pager | grep -c 'DNSSEC validation failed'
```

#### 4d. Resolver counters and current upstream

```bash
systemctl show -p ActiveEnterTimestamp systemd-resolved
resolvectl statistics
resolvectl status
```

`resolvectl statistics` counts from the last `systemd-resolved` restart, so record the restart
time with it. Work out the timeout rate per hour since then. If the previous FLDW-117 comment
recorded the counters, compare with it to get the rate between the two readings. These are
**current** figures, not history for the window. Label them that way.

Also record the configured upstreams and DNSSEC/DoT mode, so a later configuration change is
visible in the tracker's history:

```bash
cat /etc/systemd/resolved.conf.d/*.conf
```

#### 4e. Network and container correlates

- **Container churn**, which drives the cache flushes in 4c:

  ```bash
  journalctl -u docker --since "$WIN_START" --until "$WIN_END" --no-pager \
    | grep -iE 'container (start|stop|die)|ShouldRestart|exited'
  ```

  The journal is the record here: `docker events` keeps only a short history.
- **Network link or route changes** that would make every upstream unreachable at once:

  ```bash
  journalctl -u NetworkManager --since "$WIN_START" --until "$WIN_END" --no-pager
  ```

- **Tailscale**, when the failed name is a tailnet host (`*.network.kevininscoe.com`). The name
  itself is served by Linode DNS, so a failure there is still a resolver problem, but note
  whether `tailscaled` logged anything in the window:

  ```bash
  journalctl -u tailscaled --since "$WIN_START" --until "$WIN_END" --no-pager | tail -50
  ```

- **Jobs with known lookup failures.** FLDW-117 names `archive-openbao-audit-from-web1-to-local.sh`
  and `backup-pim-records-from-web1-to-local.sh`. Note whether either ran in the window.

#### 4f. Does the name resolve now?

A live check of each failed name, clearly labelled as current, not historical:

```bash
resolvectl query <name>
```

If `dig` is installed, compare with the upstreams directly to see whether the problem is the stub
or upstream:

```bash
dig +short <name> @1.1.1.1
dig +short <name> @8.8.8.8
```

If `dig` is missing, say so and use `resolvectl query` alone. Do not install anything during the
investigation.

Stop investigating once the evidence can say plainly what happened in the window: which names
failed and for which jobs or containers, how big the burst was, and whether it lined up with
DNSSEC failures, cache flushes, a network change, or none of these. If something is still
unknown, say so in the summary rather than guessing.

### 5. Confirm FLDW-117 is reachable and open

```bash
export YT_BASE=http://127.0.0.1:9000

parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -H "Accept: application/json" \
    "$YT_BASE/api/issues/FLDW-117?fields=idReadable,summary,resolved"
'
```

If this returns 404, or the issue is resolved (`resolved` is set, or `Status` is `Done` or
`Wont do`), run `set-ghostty-tab-name DNSc` before stopping, then tell Kevin. A closed FLDW-117
means the tracker has run its course: ask Kevin which issue should receive DNS events from now
on, and offer to update this skill to point at it. Do not reopen FLDW-117, and do not quietly log
to a different issue.

### 6. Compose and post one comment — input plus investigation summary

Read the clock at the moment of posting, per
`~/ai/directives/when-creating-a-youtrack-ticket.md` §9, never a time noted earlier:

```bash
date '+%Y-%m-%d %H:%M'
```

Build **one** comment in this shape, with the verbatim input first and the summary second:

```text
DNS event logged 2026-11-10 09:20

    <the pasted alert, job output or symptom, exactly as received, indented, unedited>

Investigation window: 2026-11-10 03:00–03:30

Observed:
- dockerd logged 290 "failed to query external DNS server" timeouts between 03:12 and 03:14
  (16, 180, 94 per minute) for john.network.kevininscoe.com and galaxy.kevininscoe.com.
- check-apple-health-receiver got curl 000 from https://health.kevininscoe.com/healthz at 03:13.
- systemd-resolved logged 2 DNSSEC failed-auxiliary failures in the window, neither for a
  failed name. "Flushed all caches." at 03:11, after a container restart.
- No NetworkManager or tailscaled events in the window.
- resolvectl statistics (current, since the 2026-11-05 18:43 restart): <n> timeouts, about
  <n>/hour; <n>/hour since the previous FLDW-117 reading.
- Upstream at reading: Current DNS Server 1.0.0.1#cloudflare-dns.com; DNSSEC=allow-downgrade.

Inference: the burst followed a cache flush and hit kevininscoe.com names only; it does not line
up with DNSSEC failures.

Open questions / diagnostic gaps: dig is not installed, so the upstreams could not be queried
directly.

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
    "$YT_BASE/api/issues/FLDW-117/comments?fields=id,created" \
    --data-binary "$COMMENT_JSON"
'
```

Building the JSON with `python3` rather than hand-quoting keeps the input's own punctuation,
quotes, and line breaks from breaking the payload. Confirm the response carries a comment `id`
before going on.

### 7. Turn the tab back and report to Kevin

Once the comment has posted, mark the investigation finished:

```bash
set-ghostty-tab-name DNSc
```

Do this even if nothing actionable was found. `DNSc` means this run is finished, not that a
problem was confirmed.

Then tell Kevin, in bare text:

1. The tracker's full URL: `https://youtrack.kevininscoe.com/issue/FLDW-117`.
2. Whether the failure was confirmed in the evidence, or only reported.
3. The one-line finding: what happened and the evidence for it.
4. Any diagnostic gap (missing `dig`, journal already rotated past the window, and so on) and
   the one-line fix for it, offered as a follow-up, not applied.
5. That no remediation was performed.

## Success Criteria

- FLDW-117 was confirmed live and open (not assumed), and received exactly **one new comment**
  from this run.
- That comment contains the pasted input **verbatim**, clearly separated from the summary after
  it.
- The summary separates observed facts from inferences, labels current-state readings as
  current, and names any diagnostic gap.
- `Status`, `Assignee`, and every other field on FLDW-117 are unchanged.
- No worktree or `CHECKPOINT.md` was created.
- The Ghostty tab read `DNS` during the investigation and `DNSc` after the comment posted.
- No service was restarted, no cache was flushed, no configuration was changed, and nothing was
  installed.
- Kevin has the full URL to FLDW-117, in bare text.

## Notes

- **Why FLDW-117 and not a new ticket.** As with swap events on FLDW-47, DNS events are logged as
  an accumulating history on one issue, so the frequency, the names affected, and any correlation
  with DNSSEC failures or cache flushes can be seen over time. Each comment is evidence toward
  FLDW-117's own questions and acceptance criteria.
- **This skill never closes, reassigns, or reprioritizes FLDW-117.** Any change to those fields
  is a separate, explicit request from Kevin.
- **Escalation path.** If an investigation finds something bigger than routine resolver trouble
  (a user-visible outage, data loss, or a failure monitoring missed), that also needs an incident
  report under `~/ai/directives/when-writing-an-incident-report.md`. Say so to Kevin, and still
  log the comment on FLDW-117; the two records coexist.
- **Related skills:** `../youtrack-report-a-fldw-swap-issue-and-investigate/` (the swap
  counterpart this skill is modelled on), `../youtrack-create-alert-ticket/` for a one-off alert
  with no standing tracker, and `../youtrack-report-a-problem/` for a live symptom Kevin wants
  filed as its own issue.
- Created under AI-121 (`https://youtrack.kevininscoe.com/issue/AI-121`).
