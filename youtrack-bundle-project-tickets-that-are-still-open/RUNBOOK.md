# RUNBOOK.md — youtrack-bundle-project-tickets-that-are-still-open

## Metadata

| Field | Value |
| --- | --- |
| **Owner** | Kevin P. Inscoe |
| **Last Updated** | 2026-10-17 (created, AI-94) |
| **Last Tested** | 2026-10-17 — 20 offline tests; live read-only bundles of `POE` and `AI` on the FLDW |
| **Expected Duration** | About one second per open issue, plus a few seconds of setup |
| **Risk Level** | Low (read-only against YouTrack; writes one file under `~/tmp`) |
| **Repo** | `git@github.com:kevinpinscoe/skills.git` (published on GitHub) |

---

## Purpose

This skill writes one Markdown bundle, `~/tmp/gather-youtrack-project-<project name>.md`. It
holds every issue in one YouTrack project whose `Status` is neither `Done` nor `Wont do`. Each
issue appears as its complete `yt-export` output, after an index and a dependency overview. The
bundle is the input to a later backlog-refinement or working-order session, and it preserves
evidence rather than analysing it.

---

## When to Use This Runbook

- **Use when:** running the skill outside the chooser, checking a bundle's numbers, or
  diagnosing a failed run.
- **Do NOT use when:** changing issues, links or priorities. The skill is read-only, and that
  work belongs to other skills.

---

## Prerequisites

- [ ] The FLDW or `core`, where `parzival exec --as ai youtrack-claude-code` works:
      `parzival policy what-if --as ai --mode exec --ref 'bao:app/YouTrack-Claude-Code#token'`
      prints `ALLOW`
- [ ] `yt-export`, `gather` (1.2.0 or later), `curl` and `python3` on `PATH`:
      `command -v yt-export gather curl python3`
- [ ] The exporter has the POE-53 *Dependency Metadata* section:
      `yt-export AI-61 -o - | grep -c '^## Dependency Metadata'` prints `1`. Run this inside an
      AI session, or in Kevin's terminal with his own credential.

---

## Stack

| Component | Details |
| --- | --- |
| **Language / Runtime** | Python 3, standard library only (`bundle.py`) |
| **External Services** | YouTrack REST API: `/api/admin/projects` (list and Status bundle) and `/api/issues` (reads only) |
| **Databases / File Stores** | Output in `~/tmp`; per-issue exports in a temporary `~/tmp/…-exports-*` directory |
| **Credentials / Secrets** | None of its own. The parzival profile `youtrack-claude-code` supplies a curl config (`$YOUTRACK_CURL_CONFIG`), and `yt-export` brokers its own |

---

## Step-by-Step Procedure

### Step 1 — Run it

**Why:** this is the same command the skill's Step 3 runs.

```bash
parzival exec --as ai youtrack-claude-code -- \
  python3 ~/.claude/skills/youtrack-bundle-project-tickets-that-are-still-open/bundle.py \
  --project POE
```

The project can be given by short name or full name. Add `--overwrite` to replace an existing
bundle, and `--keep-exports` to keep the per-issue files.

**Expected output:**

```text
Wrote /home/kinscoe/tmp/gather-youtrack-project-PCT-or-POE-Tooling.md
Project PCT or POE Tooling (POE): 52 issues, 13 open selected, 13 exported, 0 failed
```

**If this fails:** see Troubleshooting. Exit `1` means nothing was written. Exit `3` means the
bundle was written but is marked `INCOMPLETE`.

---

## Verification

```bash
B=~/tmp/gather-youtrack-project-PCT-or-POE-Tooling.md
grep -m1 'Included issues' "$B"
grep -c '^## /' "$B"          # index file + one per exported issue
```

Cross-check the selection with YouTrack's own query engine, through the same read path:

```bash
parzival exec --as ai youtrack-claude-code -- sh -c '
  curl -s -K "$YOUTRACK_CURL_CONFIG" -G "http://127.0.0.1:9000/api/issues" \
    --data-urlencode "query=project: POE Status: -Done -{Wont do}" \
    --data-urlencode "fields=idReadable" --data-urlencode "\$top=1000"' |
  python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
```

**Expected output:** the same number as *Included issues* (13 for `POE` on 2026-10-17), and
`## /` sections equal to that number plus one.

**Success criteria:** the counts agree, and the header shows no `INCOMPLETE` line, or the
missing issues are named in *Missing data and limitations*.

---

## Rollback Procedure

1. Nothing in YouTrack changes, so there is nothing to roll back there.
2. Delete an unwanted bundle: `rm ~/tmp/gather-youtrack-project-<name>.md`.
3. A run that failed in `gather` keeps its exports and names the directory in the error.
   Remove that directory once it has been inspected.

---

## Related Runbooks

- [`RUNBOOK.md`](../RUNBOOK.md) — the skills repository's root runbook
- `~/private-tools/RUNBOOK.md` → *yt-export*, and the exporter's own section in
  `~/Projects/private/youtrack.kevininscoe.com/RUNBOOK.md`, which covers the output format and
  its limits
- `~/private-tools/RUNBOOK.md` → *gather*

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
| ------- | ------------ | ---------- |
| `YOUTRACK_CURL_CONFIG is not set` | Run without the `parzival exec` wrapper | Use the Step 1 command exactly |
| `YouTrack read failed for /api/…` with a policy or `401` message | The brokered identity/profile pair is wrong, or the token was refused | Check `parzival policy what-if` (Prerequisites). Never fall back to another credential |
| `No YouTrack project matches '…'. Close matches: …` | A typo, or a partial name | Re-run with the exact short name shown |
| `The Status bundle no longer has the exact value(s) 'Wont do'` | The Status values were renamed | Stop. Selection is defined by those exact names, so decide the new rule before changing `TERMINAL_STATUSES` |
| `… already exists. Re-run with --overwrite` | A bundle of that name is already in `~/tmp` | Confirm it may be replaced, then add `--overwrite` |
| Exit 3, `INCOMPLETE` in the header | `yt-export` failed for some issues; the error text is quoted in the bundle | Check `yt-export <ID> -o -` for one of them. A `403`/`404` usually means `Claude_Code` lacks access to that project |
| `gather did not write the bundle` | `gather` older than 1.2.0, or the file changed while it ran | `gather --version`; the per-issue exports are kept, and the directory is named in the error |
| A line under *Text-only candidates* is not a real blocker | The candidates are a pattern match and are labelled unconfirmed | Expected. Confirm each one against the export before treating it as a dependency |

---

## Logs

The helper writes to stdout and stderr only, with no log file. The bundle header records the
export time, the host, the counts, and every failure.

---

## Monitoring

Not applicable. This is an on-demand, human-started skill, not a scheduled job or a service.

---

## Maintenance Notes

- Selection is by exact `Status` names. Never `#Unresolved`: on 2026-10-17 `POE` gave 13 by
  `Status` and 16 by `#Unresolved`, because `Done` issues with a `Category` set stay
  unresolved.
- The dependency overview reads only the exports' `Dependency Metadata` JSON (schema
  `yt-export.dependency-metadata/1`). If the exporter's schema changes, update `parse_export`
  and `analyse` together, and rerun `python3 test_bundle.py`.
- Tests: `python3 test_bundle.py` from this directory. They are offline, and the API, the
  exporter and `gather` are faked.
