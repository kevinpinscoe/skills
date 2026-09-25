---
name: youtrack-create-a-security-triage-investigation
category: youtrack
description: Open a KSI YouTrack ticket for suspicious or unusual behavior and guide an evidence-first, read-only security triage investigation to a documented disposition, without declaring an incident or breach the evidence does not establish.
---

# Create a Security Triage Investigation

> Open a KSI YouTrack ticket for suspicious or unusual behavior and guide an evidence-first,
> read-only security triage investigation to a documented disposition, without declaring an
> incident or breach the evidence does not establish.

## Scope — read this before anything else

**Opening an investigation is not declaring an incident.** A human saw something that looked
wrong. This skill records that observation, investigates it, and reaches a disposition based on
the evidence. The fact that an investigation was opened says nothing about whether a compromise
happened.

| This skill does | This skill never does |
| --- | --- |
| Take down the observation that caused concern, redacted | Classify the observation as a confirmed incident, compromise, or breach because the ticket exists |
| Open one KSI ticket framed as a **Security Triage Investigation / Suspected Security Event** | Title or type the ticket as a breach, intrusion, compromise, or incident without evidence that establishes it |
| Investigate read-only first, and preserve volatile evidence | Reboot, kill, delete, quarantine, block, rotate, reconfigure, restart, or patch just to find something out |
| Log every significant command, source, time, and finding on the ticket | Keep findings only in the chat, where the next investigator cannot see them |
| Keep facts, hypotheses, and ruled-out explanations separate | Promote a plausible explanation to a finding without evidence |
| Reach one of five dispositions, and hand over to the incident directive only when a security or access-control failure is **established** | Invent an incident-report format, or start the formal incident process because something was merely reported |

The formal incident process is defined by `~/ai/directives/when-writing-an-incident-report.md`.
That directive lists "a security or access-control failure occurred" as a trigger. **An
unexplained observation is not that trigger.** Only the fifth disposition in step 12 crosses
into it.

## Prerequisites

- **Home-category host.** Resolve the host against `~/ai/directives/kevins-federated-unix-universe.md`.
  KSI is `KFED - Security investigations`: it covers k-fed. If the affected asset belongs to the
  employer, or the host is a Work host, stop. The employer's security process governs there, not
  this skill.
- **Kevin is present.** This skill is interactive. It asks Kevin for the observation, a priority,
  and approval before any action that changes state. It must never run unattended.
- **YouTrack reachable, credential through parzival.** The token is at OpenBao mount `app`,
  secret `YouTrack-Claude-Code`, field `token`. **Never fetch it with `bao kv get`, and never
  capture it into a shell variable.** The `youtrack-claude-code` parzival profile renders it into
  a RAM-backed curl config whose path is `$YOUTRACK_CURL_CONFIG`. Every YouTrack call in this
  skill uses this shape:

  ```bash
  # Each Bash call is a fresh non-interactive shell: source and export in the SAME call.
  source ~/.environment/openbao/openbao-env.sh
  export YT_BASE=http://127.0.0.1:9000   # FLDW; elsewhere https://youtrack.kevininscoe.com

  parzival exec --as ai youtrack-claude-code -- sh -c '
    curl -s -K "$YOUTRACK_CURL_CONFIG" -H "Accept: application/json" \
      "$YT_BASE/api/admin/projects/0-63?fields=id,name,shortName"
  '
  ```

  The inner `sh -c` is required. `$YOUTRACK_CURL_CONFIG` exists only in the child that parzival
  spawns. The same prerequisite note in `../youtrack-report-a-problem/SKILL.md` explains this in
  more detail.
- **Read access to the evidence.** This includes the systemd journal, container logs, and
  whatever cloud or cluster CLIs the affected asset needs (`aws`, `az`, `kubectl`). Credentials
  for those come through OpenBao or parzival per `~/ai/directives/storing-secrets.md`. Never ask
  Kevin to paste them.
- `curl`, `python3`, `parzival`, and `set-ghostty-tab-name` (from `~/tools`, optional; see step 5).

## Parameters

| Name | Description | Default |
| ------ | ------------- | --------- |
| `YT_BASE` | YouTrack base URL **for API calls only** | `http://127.0.0.1:9000` on the FLDW, otherwise `https://youtrack.kevininscoe.com` |
| `YT_WEB_BASE` | YouTrack base URL **for any link handed to Kevin**, on every host | `https://youtrack.kevininscoe.com` |
| `YT_PROJECT_ID` | Target project, `KFED - Security investigations` (`KSI`) | `0-63` |
| `OBSERVATION` | What Kevin saw: alert, log excerpt, behavior | _(required — ask Kevin, step 2)_ |
| `PRIORITY` | Ticket priority | _(required — ask Kevin, step 3)_ |

Never build a link from `YT_BASE`. On the FLDW that gives `http://127.0.0.1:9000/issue/…`,
which does not work on any other device.

## Instructions

### 1. Check host and session

1. Confirm this is a Home host (see Prerequisites). If it is not, stop.
2. **One ticket per session** (`~/ai/directives/when-creating-a-youtrack-ticket.md` §11). If
   _this conversation_ has already worked a YouTrack issue that is not `Done` or `Wont do`, tell
   Kevin once, giving that issue's full URL and status, and then do what he says. Issues other
   sessions have `In Progress` never block this one. Do not run a board-wide query as a gate.
3. Invoking this skill is Kevin's explicit direction to file an issue, and it names the project
   (`KSI`). That is what `when-creating-a-youtrack-ticket.md` §1 requires.

### 2. Intake — ask for the observation

**Warn Kevin first, before he pastes anything:**

```text
Before you paste: do not include passwords, tokens, API keys, private keys, session
cookies or other credentials. If a log line contains one, replace the value with
<REDACTED> first. I will also redact anything I spot before it goes into YouTrack.
```

Then ask for whatever he has. **None of it is required, and incomplete is fine:**

- The alert or monitoring message
- A log entry or relevant excerpt
- Unusual network traffic
- An unexpected process, connection, authentication, file, service, or system behavior
- The affected host, application, account, service, container, cluster, or other asset
- The approximate date and time it was observed, and in which time zone
- Why it looks unusual or suspicious
- Whether it appears to still be happening

Ask him to paste the material, then type a line containing only `END` (or press `Ctrl-D`).

**Keep the raw text.** Machine-generated text (alerts, log lines, command output) is evidence.
Reproduce it exactly, including any typo, as an indented block. Correct the spelling and grammar
of Kevin's own prose only, and keep his meaning.

**Redact before anything leaves the session.** Scan the paste for credential-shaped values:
`password=`, `token`, `Authorization:`, `Bearer`, `-----BEGIN`, AWS `AKIA…` keys, long base64
or hex strings in auth context, session or cookie values, and customer data. Replace each value
with `<REDACTED:type>`, and tell Kevin what was redacted and why. If a secret was actually
exposed, **that exposure is itself a finding**. Record the fact (for example, "a bearer token
for service X appeared in the pasted log") and never the value.

**If the behavior appears to still be happening and could be an active compromise, say so
plainly now.** Say it before step 3. Ask whether Kevin wants to take containment action himself
or authorize it before triage continues. This skill never performs containment on its own
initiative (see Guardrails).

### 3. Ask for the priority

YouTrack's `Priority` field cannot be empty. Present the values and let Kevin choose. **Never
choose a priority for him, and never fall back to a default.**

```text
Which priority?
  1. Show-stopper
  2. Critical
  3. Major
  4. Normal
  5. Minor
```

This token cannot read project field schemas: `GET /api/admin/projects/<id>/customFields` returns
`[]`. So the values above cannot be validated before the create. Step 4 reads the fields back
instead. If the create rejects a value, stop and show Kevin the error. Never substitute a
near-miss value.

### 4. Create the KSI ticket

**Title.** Use `Investigate suspicious <behavior> on <asset>`, or another short neutral
description of what was _observed_:

- `Investigate suspicious outbound connections from web1 to 203.0.113.50:4444`
- `Investigate unexpected sudo session for backup user on core`
- `Investigate repeated SSH auth failures against obs from an unfamiliar range`

**Never** use _breach_, _compromise_, _compromised_, _intrusion_, _attack_, _hacked_, or
_incident_ in the title unless evidence has already established it.

**Description.** Use this exact shape. The sections below the ruler are filled in as the
investigation proceeds (step 11). **For security scope, write `Unknown` rather than guessing.**
An explicit unknown is a finding here, not a placeholder. Leave out a line that does not apply at
all, such as a repository that does not exist. Never write `N/A`.

```text
Security Triage Investigation / Suspected Security Event
This ticket records an investigation, not a confirmed incident. No compromise, breach,
or security incident has been established unless the Disposition section says so.

Reported at 2026-09-25 08:40

## Reported observation
(Reported by Kevin. Not yet verified by the investigation.)
Kevin reports that <his account, spelling corrected, meaning unchanged>.

    <pasted alert / log excerpt, verbatim, redacted, indented>

- What was observed: …
- Where: …
- When: … (time zone: …)
- Generated by: <the monitor, alert rule, log source, or person who noticed it>
- Why it appears unusual: …
- Still occurring: Yes / No / Unknown
- Other context: …

## Affected or potentially affected assets
- Hosts: …            - Applications/services: …   - Containers: …
- Kubernetes: …       - User/service accounts: …   - Cloud accounts: …
- IP addresses: …     - Network segments: …        - Databases/storage: …
- External services: …
Scope beyond the above: Unknown

## Initial time window
- Earliest known suspicious activity: …
- Alert/observation time: …
- Most recent known suspicious activity: …
- Time zone: America/New_York unless stated
- System clocks synchronized: Unknown (checked in step 6)

---
## Evidence sources examined
## Timeline
## Scope assessment
## Indicators
## Hypotheses (observed facts / working hypotheses / ruled out)
## Remaining unknowns and telemetry gaps
## Disposition
## Follow-up work
```

**Create it.** Compute the time once, and build the payload in a file so it never passes through
the inner shell's quoting:

```bash
source ~/.environment/openbao/openbao-env.sh
export YT_BASE=http://127.0.0.1:9000
NOW_MS=$(date +%s%3N)
export PAYLOAD=$(mktemp)
trap 'rm -f "$PAYLOAD"' EXIT

python3 - "$PAYLOAD" "$NOW_MS" <<'PY'
import json, sys
path, now_ms = sys.argv[1], int(sys.argv[2])
summary = "<title>"
description = open("<description file>").read()
priority = "<Kevin's choice>"
json.dump({
  "project": {"id": "0-63"},
  "summary": summary,
  "description": description,
  "customFields": [
    {"name": "Status",            "$type": "StateIssueCustomField",      "value": {"name": "In Progress"}},
    {"name": "Priority",          "$type": "SingleEnumIssueCustomField", "value": {"name": priority}},
    {"name": "Issue domain",      "$type": "SingleEnumIssueCustomField", "value": {"name": "Personal"}},
    {"name": "Assignee",          "$type": "SingleUserIssueCustomField", "value": {"login": "Claude_Code"}},
    {"name": "Date time entered", "$type": "SimpleIssueCustomField",     "value": now_ms},
  ],
}, open(path, "w"))
PY

parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -X POST \
    -H "Content-Type: application/json" -H "Accept: application/json" \
    "$YT_BASE/api/issues?fields=id,idReadable" --data-binary @"$PAYLOAD"
'
```

Write the description to a scratch file first, so its quotes and line breaks never need
escaping.

Field notes:

- **`Status` is `In Progress` at creation.** Triage starts the moment the ticket exists, so
  creation and "work started" are the same event (Kevin's decision, AI-49).
- **`Type` is not set.** No `Type` value means "suspected security event", and `Incident` would
  assert exactly what this skill must not assert. If Kevin later adds a suitable value to the
  bundle, use it. Until then, the description's first line carries the classification.
- **`Issue domain` is `Personal`.** KSI covers k-fed only, and step 1 already stopped for
  employer assets.
- **`Affected host`**: set it only when the asset maps exactly to an existing value (`FLDW`,
  `core`, `web1`, `mail1`, `obs`, and so on). If the create or a follow-up field write rejects
  the value, leave the field empty and say so.
- **Read the issue back** and confirm every field took. Do not trust the create response alone:

  ```bash
  parzival exec --as ai youtrack-claude-code -- sh -c '
    curl -s -K "$YOUTRACK_CURL_CONFIG" -H "Accept: application/json" \
      "$YT_BASE/api/issues/<KSI-n>?fields=idReadable,summary,customFields(name,value(name,login,presentation))"
  '
  ```

Hand Kevin the URL now, as bare text: `https://youtrack.kevininscoe.com/issue/<KSI-n>`.

### 5. Start the work session on the ticket

Everything here follows `~/ai/directives/when-creating-a-youtrack-ticket.md` §7–§9. Do it in one
action, right after the create:

1. **Tab:** `set-ghostty-tab-name <KSI-n>`, if the command exists and this session is inside
   tmux. Otherwise skip it silently.
2. **`Ghostty tab name` field:** write `<KSI-n>`. If step 1 was skipped, leave the field empty.
   An empty field is the record that the host skipped the rule.
3. **Start comment.** Read the clock in the same action as the post:

   ```text
   Work started 2026-09-25 08:41
   Session: <session UUID from this session's scratchpad path>
   ```

4. **Checkpoint.** An investigation usually runs long. It is not inside a git repository, so
   **do not create a `CHECKPOINT.md` yourself**. Ask Kevin whether he wants one, and where: the
   current directory, a directory under `~/Projects`, `$HOME`, or none (see
   `~/ai/directives/root-directive.md`). If he names a location, write a lane section there,
   with `Ticket: <KSI-n> — https://youtrack.kevininscoe.com/issue/<KSI-n>`, using the serialized
   write protocol in `project-planning-with-ai.md`.

Post comments with the JSON built by Python, never by hand:

```bash
export COMMENT_JSON=$(python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))' <<'TEXT'
<comment text>
TEXT
)
parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -X POST -H "Content-Type: application/json" \
    "$YT_BASE/api/issues/<KSI-n>/comments" --data-binary "$COMMENT_JSON"
'
```

### 6. Investigate — evidence first, read-only first

**Ground rules for the whole of this step:**

- **Read-only observation first.** Do **not** reboot, terminate processes, delete, quarantine,
  block addresses, rotate credentials, change firewall rules, change configuration, restart
  services, or patch, **merely to investigate**. Do any of those only when Kevin explicitly
  authorizes it, or an already-applicable incident-response directive requires it.
- **Preserve volatile state before anything that could destroy it.** Capture it first: process
  list with command lines, open sockets, conntrack table, logged-in sessions, and the relevant
  container state. Save the output to a timestamped file under the session scratchpad and record
  its path and SHA-256 on the ticket. Redact before posting any of its content.
- **Log as you go.** Each significant command, query, evidence source, time, and finding goes on
  the ticket as a findings-log comment (step 7). Another investigator must be able to reproduce
  or continue the work from the ticket alone.
- **Only what is relevant.** Work through the areas below as the reported behavior warrants.
  Do not run every check mechanically. Record the areas you skipped and why.
- **Clocks.** Compare `timedatectl` (and `chronyc tracking` where present) on every host whose
  logs you correlate. Record whether the clocks are synchronized. Unsynchronized clocks
  invalidate a timeline.

The example commands assume a Linux host. Adapt them to the asset. Keep searches scoped per
`~/ai/directives/unscoped-recursive-searches.md`. Scope any `auditctl` rule per
`unscoped-auditctl-and-tracing-commands.md`.

1. **Validate the original signal.** Is the alert or log entry genuine? Which component emitted
   it, and under what condition? Are similar entries normal? Could maintenance, automation,
   monitoring, deployment, backup, or scanning explain it? Is the timestamp and source
   trustworthy? **Retrieve the surrounding events, not one isolated line**, for example
   `journalctl --since … --until … -o short-iso-precise` around the event.
2. **Build an event timeline.** Correlate before, during, and after the event across system,
   application, authentication, network, firewall, reverse-proxy, cloud-audit, Kubernetes, and
   monitoring sources. Record the significant events in chronological order with absolute
   timestamps and time zone.
3. **Authentication and identity.** Check successful and failed logins, SSH and sudo activity
   (`journalctl -u sshd`, `_COMM=sudo`, `last`, `lastb`), new users and service accounts, group
   and role changes, new `authorized_keys` entries, token and credential use, MFA events, IAM
   changes, unusual sources or hours, and unexpected service-account use. **Never print a
   credential value.**
4. **Processes and system activity.** Check running processes with parent/child relationships,
   command lines, owners, and start times (`ps -eo pid,ppid,user,lstart,cmd --forest`). Look for
   unexpected binaries or interpreters, listening services (`ss -tulpn`), recently changed units,
   and resource anomalies. Focus on anything that does not fit the system's expected role.
5. **Network activity.** Establish source and destination addresses and ports, protocol,
   direction, start and duration, and the responsible process or workload (`ss -tunap`,
   `conntrack -L`). Establish the associated DNS lookups, whether the destination is expected,
   whether it recurs normally, and whether other hosts show it. Sources: sockets, conntrack,
   firewall, router, reverse proxy, DNS, Tailscale, cloud flow logs. Take packet captures only
   when justified, and only with Kevin's agreement. **An unfamiliar IP address or domain is not
   evidence of malice.** Establish its context.
6. **Persistence** (when host compromise is plausible). Check systemd services and timers
   (`systemctl list-unit-files --state=enabled`, `list-timers --all`), cron, user startup files,
   `authorized_keys`, login scripts, container restart policies, Kubernetes workloads, and other
   startup configuration. Record what is **expected** as well as what looks anomalous.
7. **Recent legitimate changes.** Check deployments, `dnf history`, configuration and git
   history, releases, infrastructure (OpenTofu/Ansible) changes, firewall and IAM changes, image
   changes, scheduled maintenance, automated jobs, admin activity, and
   `~/ai/fedora/CHANGELOG.md` on the FLDW. **Temporal correlation alone is not proof of cause.**
8. **File and executable integrity.** Look for recently created or modified files (scoped
   `find -newermt`), unexpected executables or scripts, and changes to sensitive or
   authentication configuration, ownership, or permissions. Check package provenance
   (`rpm -Va`, `rpm -qf`, `dpkg -V`), hashes, and known-good versions in repository history.
   **Preserve suspicious files; never delete them during triage.** Copy with
   `cp --preserve=all` and a hash, and leave the original in place.
9. **Beyond the host.** Only for platforms relevant to the affected asset:
   - **AWS:** CloudTrail, IAM activity, VPC Flow Logs, Security Group changes, and EC2, RDS, or
     EKS control-plane activity.
   - **Azure:** Activity Log, Entra sign-in and audit logs, NSG flow data, and resource changes.
   - **Kubernetes / k3s:** events, audit logs where enabled, pods and containers, service
     accounts, auditable secrets access, Deployments, DaemonSets, Jobs, CronJobs, and recent
     image or manifest changes.
   - **Containers:** processes (`docker top`), image identity (digest), mounts, runtime and
     environment configuration **with secret values masked**, and creation and restart history
     (`docker inspect`, `docker events --since`).
10. **Related indicators.** When a meaningful indicator appears (IP, domain, hostname, user,
    account, process, path, hash, command, user agent, image, or Kubernetes identity), search
    the relevant telemetry for it elsewhere. Decide whether the behavior is isolated or
    widespread. **Do not call it an IOC until the investigation supports that classification.**
11. **Scope.** Answer what the evidence allows: which asset showed it first, which accounts were
    involved, which other systems show it, when it began, when it stopped, and whether it is
    ongoing. Also answer whether privileged access was involved, whether sensitive data may have
    been accessed or transferred externally, whether persistence was established, and whether
    credentials were exposed. **Write `Unknown`, with the reason, for anything the evidence
    cannot answer.**
12. **Competing hypotheses.** Keep three lists all the way through:
    - **Observed facts:** directly supported by logs, system state, or other sources.
    - **Working hypotheses:** possible explanations not yet shown.
    - **Ruled out:** hypotheses the evidence contradicts, with that evidence.

    Never convert a hypothesis into a finding without supporting evidence. **Never drop evidence
    that contradicts the leading hypothesis.** Record it.

**If at any point the evidence suggests an active compromise may still be in progress, stop and
tell Kevin immediately.** Say it before any further step that could be destructive or tip off an
attacker. Wait for his decision unless an existing incident-response directive explicitly
authorizes the action.

### 7. Keep the findings log on the ticket

Post one comment per significant finding, as it happens and in chronological order. Take the
time from the clock in the same action as the post.

```text
Finding 2026-09-25 09:12
Source: journalctl -u sshd on core, 2026-09-25 06:00–08:00 EDT
Command: journalctl -u sshd --since "2026-09-25 06:00" --until "2026-09-25 08:00" -o short-iso
Observation: 214 failed password attempts for user "admin" from 198.51.100.0/24 between
  06:14 and 06:31; zero successes; PasswordAuthentication is "no" in sshd_config.
Interpretation: consistent with an internet-wide password spray; the configuration
  rejects password auth outright.
Supports / rules out: rules out "successful login from that range"; supports "expected
  background noise" pending a check that the address range touched no other host.
Next step: search obs and web1 sshd logs for the same range.
```

Keep **Observation** (fact) and **Interpretation** visibly separate. An interpretation is never
required, and leaving it out is better than guessing.

### 8. Maintain the description

At natural checkpoints, update the sections below the ruler in the ticket description. Always
update them before the disposition. Cover: evidence sources examined (including the ones found
to be unavailable), the timeline, the scope assessment, indicators (not labelled IOCs unless
supported), the three hypothesis lists, and remaining unknowns and telemetry gaps. The comment
stream stays the chronological record. The description is the current synthesis.

```bash
parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -X POST -H "Content-Type: application/json" \
    "$YT_BASE/api/issues/<KSI-n>?fields=idReadable" --data-binary @"$PAYLOAD"
'   # $PAYLOAD = {"description": "<full updated description>"}, built with python3 json.dump
```

### 9. Choose the disposition

When triage has gone as far as the evidence allows, propose **one** disposition to Kevin, with
the evidence behind it. **Kevin confirms the disposition.** Then record it in the Disposition
section and as a comment.

| Disposition | Meaning | Must document |
| --- | --- | --- |
| **Expected or benign activity** | Explained by legitimate system, application, administrative, monitoring, or user behavior | The evidence for that explanation |
| **False positive** | The detection fired, but the condition it looks for was not present | Why, plus any monitoring or detection correction worth making |
| **Unexplained / insufficient evidence** | Cannot be explained yet, but nothing establishes a security failure or compromise | What was checked, what remains unknown, what evidence was unavailable, what monitoring or follow-up is needed. **This is not an incident because it is unexplained.** |
| **Security-relevant event requiring remediation** | A weakness, policy problem, or exposed attack surface was found, but nothing establishes a compromise | The weakness and evidence, plus linked corrective YouTrack work |
| **Confirmed security or access-control failure** | Evidence establishes that an actual security or access-control failure occurred | Go to step 10 |

**Follow-up work.** A monitoring gap, a hardening change, or a corrective action each becomes its
own YouTrack issue, **but an AI never files an issue on its own initiative.** Propose each one,
ask Kevin which project it belongs in, and create it only when he names one. Then link it to the
KSI ticket (`relates to`) and list it under Follow-up work. A monitoring gap also routes into
`~/ai/directives/when-establishing-monitoring-for-a-job-or-service.md`.

### 10. Only for a confirmed failure — hand over to the formal incident process

If and only if the disposition is **Confirmed security or access-control failure**:

1. Tell Kevin plainly that the investigation has crossed into the formal incident process, and
   stop treating it only as triage.
2. Read `~/ai/directives/when-writing-an-incident-report.md` from disk, and follow it exactly.
   Use its template (`~/Projects/private/incidents/templates/incident-report-template.md`), its
   filing location, its `incident_id` sequence, and its corrective-action tracking. **Do not
   create an incident-report format inside this skill or on the KSI ticket.**
3. The report lives in a git repository. Writing it is a separate unit of work under that
   repository's own workflow (`when-working-in-a-git-tracked-repo.md`). If it needs a different
   YouTrack issue, give the one-ticket reminder from step 1 before starting it.
4. **The KSI ticket stays the investigative evidence trail.** Cross-link both ways: put the
   report's path and incident id in a KSI comment, and put the KSI ticket URL in the report's
   related-links section. Link every corrective-action ticket to both.

### 11. Stop, report, and ask about closing

Every time work on the ticket stops, finished or not
(`when-creating-a-youtrack-ticket.md` §5 and §9):

1. **Stop comment and `Spent time` in the same action.** Read the clock with
   `date '+%Y-%m-%d %H:%M'`. Post the comment:

   ```text
   Work stopped 2026-09-25 10:05 — triage complete, disposition: <disposition>
   Spent time 84m — elapsed span, not yet reconciled to effort
   ```

   Then **add** the elapsed span to `Spent time`, in minutes (`<N>m`). Read the current value
   first and add to it; never overwrite an earlier session's time:

   ```bash
   export F='{"customFields":[{"name":"Spent time","$type":"PeriodIssueCustomField","value":{"presentation":"<total>m"}}]}'
   ```

   If the session is being shut down (for a storm, a power outage, or a reboot), write the stop
   comment **first**, before anything else.
2. **Report to Kevin** (see "Report format" below).
3. **Ask whether to close the ticket.** Never close it on your own judgement. Once he approves,
   set `Status` to `Done`. If the investigation is abandoned, set it to `Wont do` with the same
   approval. Then rename the tab to `<KSI-n>c` and set `Ghostty tab name` to match. Until he
   answers, the ticket stays `In Progress`, carrying its stop comment. That is the normal
   "done, waiting on closure" state.
4. If Kevin set up a checkpoint in step 5, remove this lane's section once its tasks are done.

**Report format**, in this order: what happened and why it matters (1–3 sentences), the ticket
URL as bare text, the disposition and its key evidence, what is still unknown, any follow-up
tickets as full URLs, whether anything was changed on any system (normally: nothing), and a
`Main takeaway`.

## Guardrails — evidence handling

**Always:**

- Preserve original evidence where practical; work on copies.
- Record each evidence source and its timestamp.
- Use absolute timestamps with the time zone.
- Redact credentials, tokens, keys, session identifiers, customer data, and other sensitive
  material **before** it reaches YouTrack.
- Prefer reproducible queries and commands, recorded verbatim.
- Name the gaps in available telemetry.
- State uncertainty explicitly.
- Keep evidence and interpretation distinguishable.

**Never:**

- Declare a breach solely from an alert.
- Declare an IP address, process, file, account, or domain malicious because it is unfamiliar.
- Attribute activity to an attacker, person, or group without evidence.
- Destroy evidence to find out whether it was malicious.
- Make disruptive production changes as part of triage without authorization.
- Paste secrets into YouTrack.
- Hide evidence that contradicts the current hypothesis.
- Close an investigation as "nothing found" without documenting what was actually examined.
- Run `bao-breakglass`, or reach for any authority parzival does not grant. Name the policy change
  and ask Kevin, or print the command and stop.

## Success Criteria

The KSI ticket, and not the chat, contains:

- [ ] The original reported observation, with Kevin's words and verbatim (redacted) evidence
- [ ] Affected or potentially affected assets, with unknown scope written as `Unknown`
- [ ] The investigation time window, with time zone and clock-sync status
- [ ] The evidence sources examined, including unavailable ones
- [ ] Significant findings as timestamped findings-log comments
- [ ] A timeline
- [ ] A scope assessment
- [ ] Relevant indicators, not labelled IOCs without support
- [ ] Remaining unknowns and telemetry gaps
- [ ] A final disposition that Kevin confirmed, with the evidence supporting it
- [ ] Links to any follow-up work

Also:

- The title and fields never assert an incident, breach, or compromise the evidence did not
  establish. `Type` is not `Incident`.
- `Status` was `In Progress` from creation. `Date time entered`, `Priority` (Kevin's choice),
  `Issue domain`, and `Assignee` read back correctly.
- Start and stop comments exist, with clock-read times. `Spent time` holds at least this
  session's elapsed span.
- No state-changing action was taken without Kevin's explicit authorization, and any that was
  taken is recorded on the ticket.
- For a confirmed failure, an incident report exists under the incident directive, and it and the
  KSI ticket link to each other.
- Kevin has the ticket's full URL, `https://youtrack.kevininscoe.com/issue/<KSI-n>`, as bare
  text.

## Notes

- **Why KSI and not `PR`.** `../youtrack-report-a-problem/` investigates a known malfunction.
  This skill investigates a _suspicion_, where the most likely outcome is "benign". It needs a
  record that can conclude that without an incident label ever having been attached.
- **Why no `Type`.** A field value is read as a classification. Leaving `Type` empty is more
  honest than `Incident`, and more honest than a misleading `Task`.
- **Schema cannot be pre-validated.** The `Claude_Code` token gets `[]` from the project
  custom-field endpoint (seen 2026-09-25 for both KSI and PR). Validation happens by reading the
  fields back. Any field KSI lacks shows up as a create error: stop and report it.
- **Escalation from other skills.** If `../youtrack-report-a-problem/` or
  `../youtrack-report-a-fldw-swap-issue-and-investigate/` surfaces something security-shaped but
  unproven, this skill is the next step, not the incident directive.
- **Related directives:** `when-creating-a-youtrack-ticket.md` (ticket lifecycle),
  `when-writing-an-incident-report.md` (confirmed failures only), `storing-secrets.md` and
  `parzival.md` (credentials), and `when-establishing-monitoring-for-a-job-or-service.md`
  (detection gaps).
