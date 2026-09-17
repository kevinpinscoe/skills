---
name: prescription-check-for-refills
category: prescription
description: Report which prescriptions are past due or coming due, from the Next due row of each sheet in the prescription inventory spreadsheet.
---

# Check For Refills

> Report which prescriptions are past due or coming due, from the `Next due` row of each sheet in the prescription inventory spreadsheet.

Each sheet in the prescription inventory tracks one prescription: a title row, a header row, one
row per pharmacy fill, and a final labelled row — `Next due`, `Next refill`, or `Next order` —
carrying the date that prescription next needs collecting. Those dates are typed by hand, not
calculated, so the spreadsheet is the authority and nothing in this skill infers a due date from
dosage or supply length.

Answering "what is coming due?" by hand means reading a hand-typed date out of the last row of
every sheet in a 700 KB flat-XML file and comparing fourteen of them against today. This skill
does that in one pass.

**This skill only reads.** It never edits the spreadsheet, never changes a `Next due` value, and
never marks a refill as collected. The spreadsheet is Kevin's record; correcting it is his.

## Prerequisites

- `python3` — runs `check-for-refills.py`; standard library only, no `pip install`
- Read access to `~/sheets/spreadsheet-files/medical/prescription-inventory.fods`. That repo is
  private and stores personal records — see its own `README.md`
- The file must be flat XML (`.fods`), not a zipped `.ods`. This one is, deliberately, so its
  history stays line-by-line diffable

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `DAYS` | Size of the upcoming window, in days (`--days`) | `7` |
| `FILE` | Spreadsheet to read (`--file`) | `~/sheets/spreadsheet-files/medical/prescription-inventory.fods` |
| `STALE_DAYS` | Days past due at which a sheet with no later fill row is reported as stale rather than overdue (`--stale-days`) | `60` |
| `ALL` | Also list prescriptions due beyond the window (`--all`) | off |

## Instructions

1. **Run the check** — from this skill's own directory:

   ```bash
   python3 check-for-refills.py
   ```

   Add `--days 30` when Kevin asks about a longer horizon, `--all` to include everything with a
   future date, and `--json` when the output is being consumed by something other than a human.
   Pass `--today YYYY-MM-DD` only for testing.

2. **Read the four buckets.** The script classifies every sheet into exactly one:

   | Bucket | Meaning |
   |---|---|
   | `PAST DUE` | The date has passed. Act on these first — they are the reason the skill reports overdue items alongside the window rather than the window alone. |
   | `DUE WITHIN <N> DAYS` | Falls inside the window. An empty bucket here is a real answer, not a failure. |
   | `POSSIBLY ABANDONED TRACKING` | More than `STALE_DAYS` past the recorded date with no later fill row, or carrying no date at all. The tracking lapsed; the prescription is probably not urgently overdue. |
   | `LATER` | Beyond the window. Shown only with `--all`. |

3. **Report to Kevin** — lead with the past-due items and their day counts, then say plainly
   whether anything falls inside the window. Name the stale sheets separately, as a suggestion to
   check the spreadsheet rather than the pharmacy. Do not present a 600-day-stale row as an
   urgent refill.

4. **Do not edit anything.** If a `Next due` date looks wrong, or a sheet's tracking has clearly
   lapsed, say so and let Kevin decide. Editing the file also requires the FODS normalization step
   in `~/CLAUDE.md`, which is outside this skill's scope.

## Success Criteria

- Output begins with `Prescription refills as of <today>` and exit code is `0`
- Every sheet in the spreadsheet appears in exactly one bucket — the bucket counts sum to the
  number of sheets (verify with `--days 30 --all`, which leaves nothing unreported)
- `PAST DUE` day counts agree with the dates shown beside them
- Exit code `2` with a message on `stderr` when the file is missing or `--today` is malformed

## Notes

- **The `Next due` dates are hand-entered.** The spreadsheet contains exactly one formula, and it
  is not one of these. A date that is wrong in the sheet is wrong in this report.
- **The spreadsheet is read from the working tree**, so an uncommitted edit to it is included.
  That is intended — the current state is what matters for a refill question.
- **One sheet tracks a wearable sensor with its own `Inserted` / `Due` columns.** Those are a
  separate clock from the pharmacy refill and are deliberately not read here; the sensor can be
  due for a change while the prescription is not due for collection.
- A sheet whose final row carries the label but no date lands in `POSSIBLY ABANDONED TRACKING`
  with `(no date)`, rather than being silently dropped.
- Dates embedded in longer cell text (`2024-04-15 (bottle 1)`) are read correctly; values outside
  1990–2100 are treated as typos and ignored, because the spreadsheet contains a few.
- **Related skills** — none. `~/Projects/private/spreadsheet-management` holds the tooling for
  editing and normalizing these files, which this skill deliberately does not do.
