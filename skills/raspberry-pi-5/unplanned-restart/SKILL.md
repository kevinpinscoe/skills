---
name: unplanned-restart
description: Diagnose why a Raspberry Pi 5 (host "core"/rpi5) restarted unexpectedly and log the post-mortem.
---

# Raspberry Pi 5 — Unplanned Restart Analysis

> Diagnose why the `core` (rpi5) Raspberry Pi restarted unexpectedly, classify the
> root cause, and write a dated post-mortem into the config repo.

## Prerequisites

- Run on the host itself (`hostname` = `core`), or with `journalctl` access to its logs.
- `journalctl` (systemd-journald) with persistent logging enabled.
- `vcgencmd` (Raspberry Pi firmware tools) for throttle/undervoltage flags.
- Write access to `~/Projects/private/host-rpi5-core-config/` (the config repo).

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `EVENT_TS` | Folder name for the incident, `YYYY-MM-DD-HH-MM` (EDT) — use the **event** time (last log before the outage), not "now". | _(derive from analysis)_ |

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

3. **Read the RTC / clock signal at the start of the current boot — the decisive test.**
   ```bash
   journalctl -b 0 --no-pager | grep -iE "rpi_rtc|setting system clock|fake-hwclock|Initial clock synchronization|time.*advanced"
   ```
   - RTC **`setting system clock to 1970-01-01…`** (reset to epoch) → **real power loss.**
     The Pi 5's RTC only zeroes when the input rail is removed; a watchdog reset or a
     software hang would **not** wipe it. This is the strongest single signal.
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

7. **Classify** the root cause from the signals above:
   | Signals | Verdict |
   |---|---|
   | No shutdown seq + RTC reset to 1970 | **Power loss / cold boot** |
   | Shutdown seq present | **Software reboot** (planned or crash-handler) |
   | Storage resets/hangs before stop | **USB/SMR I/O stall** |
   | Undervoltage bits set / voltage msgs | **Undervoltage (PSU/cable)** |

8. **Write the post-mortem.** Create a dated folder and `README.md` in the config repo:
   ```bash
   mkdir -p ~/Projects/private/host-rpi5-core-config/unplanned-restarts/<EVENT_TS>
   # write <EVENT_TS>/README.md — mirror the structure of the newest existing entry:
   #   What this is · Timeline · Evidence (per class) · Conclusion · Follow-ups · Raw evidence
   ```
   Then **add a row** to `unplanned-restarts/README.md` (the incident index table).

9. **Commit and push** the config repo (Kevin prefers commit + immediate push):
   ```bash
   cd ~/Projects/private/host-rpi5-core-config
   git add unplanned-restarts/
   git commit -m "docs: log unplanned restart <EVENT_TS> and analysis"
   git push
   ```

10. **Report** to the user: the verdict (one line), the bracketed outage window, which
    root-cause classes were ruled in/out, and the path to the new folder.

## Success Criteria

- A verdict with a named root-cause class, backed by the RTC/shutdown/storage/voltage
  signals — not a guess.
- `unplanned-restarts/<EVENT_TS>/README.md` exists and the index table has its row.
- Config repo committed and pushed.

## Notes

- **Host identity:** `hostname` = `core` is definitive (aka rpi5). Home-category host.
- **Rootfs:** on a USB JMicron bridge (vid:pid `152d:9561`) to a WDC WD60EFAX **SMR** HDD;
  the `usb-storage.quirks=…:u` mitigation (UAS off) must stay in the kernel cmdline.
- **Timestamp choice:** name the folder for the **event** time (last log before the
  outage), so incidents sort chronologically by when they occurred.
- The RTC-reset-to-1970 test is the highest-signal, lowest-effort check — do not skip it.
- Related: host memories `project_rpi5_rootfs_smr_uas`, `project_rpi5_persistent_logging`.
