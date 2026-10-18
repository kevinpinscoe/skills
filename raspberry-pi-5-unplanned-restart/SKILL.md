---
name: raspberry-pi-5-unplanned-restart
category: raspberry-pi-5
description: Diagnose why a Raspberry Pi 5 (host "core"/rpi5) restarted unexpectedly and log the post-mortem.
disable-model-invocation: true
---

# Raspberry Pi 5 — Unplanned Restart Analysis

> Diagnose why the `core` (rpi5) Raspberry Pi restarted unexpectedly, classify the
> root cause, and write a dated post-mortem into the config repo.

## Prerequisites

- Run on the host itself (`hostname` = `core`), or with `journalctl` access to its logs.
- `journalctl` (systemd-journald) with persistent logging enabled.
- `vcgencmd` (Raspberry Pi firmware tools) for throttle/undervoltage flags.
- Write access to `~/Projects/private/host-rpi5-core-config/` (the config repo), a
  YouTrack issue for the work, and — to open the pull request — a working `tea`.

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `EVENT_TS` | Folder name for the incident, `YYYY-MM-DD-HH-MM` (EDT) — use the **event** time (the kernel fault if there is one, otherwise the last log before the outage), not "now". | _(derive from analysis)_ |

## Instructions

Work through the evidence chain **in order**. Each step both gathers a fact and rules a
root-cause class in or out. Do not stop at the first plausible cause — collect all the
signals, then classify.

1. **Establish the reboot happened & when.**
   ```bash
   uptime
   journalctl --list-boots | tail -15
   ```
   The current boot (`0`) starting far more recently than expected confirms a restart.
   Note the **end time of the previous boot (`-1`)** — that brackets the outage.

2. **Check for a clean shutdown at the end of the previous boot.**
   ```bash
   journalctl -b -1 -n 40 --no-pager
   journalctl -b -1 --no-pager | grep -iE "shutting down|reached target (shutdown|reboot|power)|systemd-shutdown|powering off|reboot:|kernel panic|watchdog|oops|BUG:" | tail -30
   ```
   - **Shutdown sequence present** (`Stopping…`, `Reached target Shutdown`, `reboot:`)
     → it was a **software-initiated reboot** (planned, a crash-handler, or a `reboot`).
   - **No sequence — log just stops mid-stream** → **unclean stop** (power loss or hard
     hang). Proceed to distinguish which in step 3.
   - **Search the whole previous boot for a kernel fault, not only its tail.** An Oops
     does not stop the kernel, so the journal can keep logging for hours after it:
     ```bash
     journalctl -b -1 -k --no-pager | grep -nE "Oops|Internal error|Unable to handle kernel|Call trace|BUG:|Kernel panic"
     ```
     A hit means the **event time is the fault, not the last log line**. Record the
     faulting process, the top of the call trace and the kernel version. Then check
     whether anything (a GUI session, a service) is known to have died after it.

3. **Read the RTC / clock signal at the start of the current boot — the decisive test.**
   ```bash
   journalctl -b 0 --no-pager | grep -iE "rpi_rtc|setting system clock|fake-hwclock|Initial clock synchronization|time.*advanced"
   ```
   - RTC **`setting system clock to 1970-01-01…`** (reset to epoch) → **real power loss.**
     The Pi 5's RTC keeps its time across software restarts (seen on this host) and loses it when power is removed; a watchdog reset or a
     software hang would **not** wipe it. This is the strongest single signal that power
     was removed — but it says nothing about **why**. A hung host that someone then
     power-cycles resets the RTC the same way, so combine it with step 2's kernel-fault
     search before concluding the cause was a power failure.
   - RTC restored a sane time and no epoch reset → lean toward a **hang/watchdog reset or
     software reboot** rather than power removal.
   - `Initial clock synchronization to …` gives the **real wall-clock** the machine came
     back (journal timestamps early in boot 0 are wrong until NTP resyncs).

4. **Rule out the USB/SMR I/O-stall class** (the 2026-07-08 failure mode — see host memory
   `project_rpi5_rootfs_smr_uas`).
   ```bash
   journalctl -b -1 -k --no-pager | grep -iE "uas|usb-storage|reset|ata|I/O error|task abort|scsi|EXT4-fs error|hung task|blocked for more than|timed out" | tail -40
   ```
   - Storage resets / task aborts / `blocked for more than 120s` **before** the stop →
     **I/O-stall class**, likely the SMR HDD on the JMicron USB↔SATA bridge.
   - Confirm the mitigation is active (expected):
     `usb-storage.quirks=152d:9561:u` on the kernel cmdline and
     `UAS is ignored for this device, using usb-storage instead` in the log.
   - No storage errors before the stop → **not** this class.

5. **Rule out undervoltage / thermal.**
   ```bash
   vcgencmd get_throttled          # 0x0 = clean since boot; 0x1 now, 0x10000 occurred
   journalctl -b 0 -k --no-pager | grep -iE "voltage|throttl|thermal|over-current" | head
   ```
   Note the caveat: `get_throttled` only reflects **since the current boot** — a power
   loss wipes the history bits, so `0x0` does **not** clear undervoltage as the cause.

6. **Note the pstore/ramoops status** (affects whether a panic *could* have been captured).
   ```bash
   journalctl -b 0 -k --no-pager | grep -iE "ramoops|pstore"
   ```
   `probe … failed` / *"firmware out-of-date"* means **no kernel crash dump survives a
   reboot** — absence of a recorded panic is then inconclusive, not exonerating.

   Also record the **reservation size** (`ramoops: using 0x10000@…` is only 64 KiB, the
   stock overlay default) and any `pstore: backend (ramoops) writing error (-28)` line.
   `-28` (`-ENOSPC`) most likely means the dump was larger than one record, so only its
   first part was stored. Ramoops survives a **warm** reset only: a kernel Oops that does
   not panic never resets the host, and a later power cycle erases the RAM. Check whether
   `kernel.panic_on_oops` and `kernel.panic` are set before treating a missing dump as
   unexplained.

7. **Classify** the root cause from the signals above:
   | Signals | Verdict |
   |---|---|
   | No shutdown seq + RTC reset to 1970 | **Power loss / cold boot** |
   | Shutdown seq present | **Software reboot** (planned or crash-handler) |
   | Storage resets/hangs before stop | **USB/SMR I/O stall** |
   | Undervoltage bits set / voltage msgs | **Undervoltage (PSU/cable)** |
   | Kernel Oops / BUG in the previous boot (any time before the stop), then an unclean stop | **Kernel / display-stack Oops.** An RTC reset to 1970 here reflects the recovery power cycle, not the cause. Name the faulting process and call-trace path (for example Xorg → DRM PRIME import) |

   Where more than one row matches, the **earliest causal event** wins: an Oops hours
   before a power cycle is the cause, and the power cycle is how the host recovered.

8. **Write the post-mortem on a feature branch, in a worktree — never on `main`.** The
   work needs a YouTrack issue (ask Kevin for it if there is none). Follow
   `~/ai/directives/when-working-in-a-git-tracked-repo.md`: first check the repo's
   `CHECKPOINT.md`, then create the worktree and branch from the issue key, and record it
   on the issue:
   ```bash
   cd ~/Projects/private/host-rpi5-core-config
   git fetch origin
   git worktree add ai-wt/<ISSUE-ID> -b <ISSUE-ID> origin/main
   cd ai-wt/<ISSUE-ID>
   ```
   Then create a dated folder and `README.md` inside that worktree:
   ```bash
   mkdir -p unplanned-restarts/<EVENT_TS>
   # write <EVENT_TS>/README.md — mirror the structure of the newest existing entry:
   #   What this is · Timeline · Evidence (per class) · Conclusion · Follow-ups · Raw evidence
   ```
   This is a specialized incident-report README, not a repo front door — per
   `~/ai/directives/when-creating-a-readme.md`'s "Not all repos are code repos" guidance, mirror
   the established incident structure above rather than the generic sections in
   `~/ai/directives/readme-template.md`.
   Then **add a row** to `unplanned-restarts/README.md` (the incident index table).

9. **Commit, push the branch, and open a pull request — Kevin reviews and merges it.**
   Run `mdlint-fix` on the new README and the index first.
   ```bash
   # inside ~/Projects/private/host-rpi5-core-config/ai-wt/<ISSUE-ID>
   git add unplanned-restarts/
   git commit -m "docs: log unplanned restart <EVENT_TS> and analysis (<ISSUE-ID>)"
   git push -u origin <ISSUE-ID>
   tea pulls create --base main --head <ISSUE-ID> --title "<ISSUE-ID>: ..."
   ```
   - **Never push to `main` and never merge the pull request yourself.** Kevin merges it.
   - Record each commit and the pull request on the YouTrack issue.
   - Hand back the pull request's **full URL** as bare text.
   - If `tea` cannot authenticate (for example the `parzival` `tea` profile is missing on
     the host), **stop and report it.** Do not create or copy a credential to get around it.
     Push the branch and give Kevin the compare URL,
     `https://git.kevininscoe.com/kinscoe/host-rpi5-core-config/compare/main...<ISSUE-ID>`.

10. **Report** to the user: the verdict (one line), the bracketed outage window, which
    root-cause classes were ruled in/out, and the path to the new folder.

## Success Criteria

- A verdict with a named root-cause class, backed by the RTC/shutdown/storage/voltage
  signals — not a guess.
- `unplanned-restarts/<EVENT_TS>/README.md` exists and the index table has its row.
- The post-mortem is committed on a feature branch and pushed, with a pull request open
  (or the compare URL handed to Kevin). Nothing is pushed to `main` or merged by the agent.

## Notes

- **Host identity:** `hostname` = `core` is definitive (aka rpi5). Home-category host.
- **Rootfs:** on a USB JMicron bridge (vid:pid `152d:9561`) to a WDC WD60EFAX **SMR** HDD;
  the `usb-storage.quirks=…:u` mitigation (UAS off) must stay in the kernel cmdline.
- **Timestamp choice:** name the folder for the **event** time, so incidents sort
  chronologically by when they occurred. For a power loss or hang that is the last log
  line before the outage. For a kernel Oops it is the Oops itself, which can be hours
  before the log ends (2026-10-18: Oops 07:29, log ended 11:27).
- The RTC-reset-to-1970 test is the highest-signal, lowest-effort check — do not skip it.
- Related: host memories `project_rpi5_rootfs_smr_uas`, `project_rpi5_persistent_logging`.
