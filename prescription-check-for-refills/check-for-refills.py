#!/usr/bin/env python3
"""Report prescription refills that are overdue or coming due.

Reads a flat-XML OpenDocument spreadsheet (`.fods`) in which each sheet tracks one
prescription, and each sheet's final labelled row records when that prescription is next
due. Emits a grouped report, or JSON with `--json`.

The spreadsheet is the only source of prescription names — none are hardcoded here.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

TABLE = "{%s}" % NS["table"]
OFFICE = "{%s}" % NS["office"]

DEFAULT_SHEET = "~/sheets/spreadsheet-files/medical/prescription-inventory.fods"

# "Next due", "Next refill", "Next order" — the label in the last row of each sheet.
NEXT_DUE_LABEL = re.compile(r"^next\s+(due|refill|order)\b", re.IGNORECASE)

# A date anywhere in a cell, so "2024-04-15 (bottle 1)" still yields a date.
DATE_IN_TEXT = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# Dates outside this range are typos, not dates. The sheet contains a few.
MIN_YEAR, MAX_YEAR = 1990, 2100

# A row repeated more times than this is trailing empty filler, not data.
MAX_ROW_REPEAT = 50

# A pharmacy prescription number as this store records them: 6 to 8 digits, nothing else.
RX_NUMBER = re.compile(r"\d{6,8}")


def parse_date(raw: str) -> dt.date | None:
    """Pull a plausible ISO date out of a cell value, or return None."""
    if not raw:
        return None
    for match in DATE_IN_TEXT.finditer(raw):
        year, month, day = (int(g) for g in match.groups())
        if not MIN_YEAR <= year <= MAX_YEAR:
            continue
        try:
            return dt.date(year, month, day)
        except ValueError:
            continue
    return None


def cell_text(cell: ET.Element) -> str:
    """The value of one cell: its typed value if it has one, else its text."""
    for attr in ("date-value", "value", "time-value"):
        value = cell.get(OFFICE + attr)
        if value:
            return value
    return " ".join("".join(p.itertext()) for p in cell.findall("text:p", NS)).strip()


def sheet_rows(table: ET.Element) -> list[list[str]]:
    """Every row of one sheet, as lists of cell strings with trailing blanks dropped."""
    rows: list[list[str]] = []
    for row in table.findall("table:table-row", NS):
        repeat = int(row.get(TABLE + "number-rows-repeated", "1"))
        cells: list[str] = []
        for cell in row.findall("table:table-cell", NS):
            span = int(cell.get(TABLE + "number-columns-repeated", "1"))
            text = cell_text(cell)
            cells.extend([text] * min(span, MAX_ROW_REPEAT))
        while cells and not cells[-1]:
            cells.pop()
        for _ in range(1 if repeat > MAX_ROW_REPEAT else repeat):
            rows.append(cells)
    while rows and not rows[-1]:
        rows.pop()
    return rows


def read_sheet(table: ET.Element) -> dict:
    """Reduce one sheet to a name, its next-due date, and its most recent fill date."""
    name = table.get(TABLE + "name") or "(unnamed)"
    rows = sheet_rows(table)

    next_due = None
    label = None
    fill_rows = []

    for cells in rows:
        if not cells:
            continue
        first = cells[0].strip()
        if NEXT_DUE_LABEL.match(first):
            # Last such row wins, in case a sheet carries an older one above it.
            label = first
            next_due = parse_date(cells[1]) if len(cells) > 1 else None
            continue
        fill_rows.append(cells)

    fills = [d for d in (parse_date(c[0]) for c in fill_rows if c) if d]

    return {
        "prescription": name,
        "label": label,
        "next_due": next_due,
        "last_fill": max(fills) if fills else None,
        "fill_count": len(fills),
        "rx_numbers": rx_numbers(fill_rows),
    }


def rx_numbers(rows: list[list[str]]) -> list[str]:
    """Every prescription number in the column that predominantly holds them.

    Found by weight of evidence rather than by header text, because the header is spelled
    differently from sheet to sheet and one sheet has no header row at all.
    """
    counts: dict[int, list[str]] = {}
    for cells in rows:
        for i, value in enumerate(cells):
            if RX_NUMBER.fullmatch(value.strip()):
                counts.setdefault(i, []).append(value.strip())
    if not counts:
        return []
    column = max(counts, key=lambda i: len(counts[i]))
    return counts[column]


def rx_outliers(numbers: list[str]) -> list[tuple[str, str]]:
    """Prescription numbers that differ from a more common one by a single digit.

    A one-character typo in a prescription number is invisible on the page and survives
    every other check: it is the right length, it is all digits, and it sorts next to its
    neighbours. What gives it away is that the sheet already contains the number it should
    have been. Returns (suspect, likely_intended) pairs.

    **The suspect must appear exactly once.** That is what separates a typo from a real
    prescription that happens to be one digit from another, and it follows from how the
    sheet is written: a multi-container fill occupies several rows carrying the same number,
    so a genuinely separate prescription shows up as many times as it has rows. A number
    typed once is a number typed once.

    Measured on 2026-09-17: relaxing this to "rarer than its neighbour" produced a false
    positive on a sensor prescription appearing 3 times beside a 16-time neighbour — a
    normal three-sensor fill, not a typo — while the one real defect in the workbook was a
    single occurrence beside a 5-time neighbour.
    """
    tally = collections.Counter(numbers)
    out = []
    for suspect, seen in tally.items():
        if seen != 1:
            continue
        for other, other_seen in tally.items():
            if other == suspect or other_seen < 2 or len(other) != len(suspect):
                continue
            if sum(a != b for a, b in zip(suspect, other)) == 1:
                out.append((suspect, other))
                break
    return out


def classify(entry: dict, today: dt.date, window_days: int, stale_days: int) -> str:
    """Bucket one sheet: no_date, stale, overdue, due_soon, or later."""
    due = entry["next_due"]
    if due is None:
        return "no_date"

    days = (due - today).days
    if days >= 0:
        return "due_soon" if days <= window_days else "later"

    last_fill = entry["last_fill"]
    no_newer_fill = last_fill is None or last_fill < due
    if -days > stale_days and no_newer_fill:
        return "stale"
    return "overdue"


def domain_findings(entries: list[dict]) -> list[str]:
    """Defects that need to know what this workbook *means*, not just how it is shaped.

    The generic structural rules live in `sheetlint.py` in the spreadsheet-management repo,
    which is public tooling holding no spreadsheets — so "a sheet should have a next-due row"
    and "a prescription number should look like its neighbours" cannot live there. They live
    here, where the prescription semantics already do.
    """
    out: list[str] = []

    for entry in entries:
        name = entry["prescription"]
        if entry["label"] is None:
            out.append(f"{name}: no next-due row at all. This sheet cannot be reported on "
                       "until one is added.")
        elif entry["next_due"] is None:
            out.append(f"{name}: the {entry['label']!r} row carries no readable date.")

        for suspect, intended in rx_outliers(entry["rx_numbers"]):
            out.append(f"{name}: prescription number {suspect} appears once and differs from "
                       f"{intended} by a single digit — likely a typo for {intended}.")

    labels = collections.Counter(e["label"] for e in entries if e["label"])
    if len(labels) > 1:
        spelled = ", ".join(f"{label!r} ({count})" for label, count in labels.most_common())
        out.append("next-due rows are labelled inconsistently across sheets: " + spelled +
                   ". All are read correctly; the inconsistency is cosmetic.")

    return out


def load(path: str) -> list[dict]:
    tree = ET.parse(path)
    return [read_sheet(t) for t in tree.getroot().iter(TABLE + "table")]


def iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


def report(buckets: dict[str, list[dict]], today: dt.date, window_days: int,
           stale_days: int, show_later: bool) -> str:
    out: list[str] = []
    add = out.append

    def rows(entries: list[dict], describe) -> None:
        for entry in sorted(entries, key=lambda e: (e["next_due"] or dt.date.max,
                                                    e["prescription"])):
            add("  %-28s %-10s  %s" % (entry["prescription"],
                                       iso(entry["next_due"]) or "(no date)",
                                       describe(entry)))

    add("Prescription refills as of %s" % today.isoformat())
    add("")

    if buckets["overdue"]:
        add("PAST DUE (%d)" % len(buckets["overdue"]))
        rows(buckets["overdue"],
             lambda e: "%d day%s overdue" % (abs((e["next_due"] - today).days),
                                             "" if abs((e["next_due"] - today).days) == 1 else "s"))
        add("")

    add("DUE WITHIN %d %s (%d)" % (window_days, "DAY" if window_days == 1 else "DAYS",
                                   len(buckets["due_soon"])))
    if buckets["due_soon"]:
        rows(buckets["due_soon"],
             lambda e: "in %d day%s" % ((e["next_due"] - today).days,
                                        "" if (e["next_due"] - today).days == 1 else "s"))
    else:
        add("  none")
    add("")

    if buckets["stale"] or buckets["no_date"]:
        add("POSSIBLY ABANDONED TRACKING (%d)"
            % (len(buckets["stale"]) + len(buckets["no_date"])))
        add("  More than %d days past the recorded date with no later fill row, or no date at"
            % stale_days)
        add("  all. Check the sheet rather than the pharmacy.")
        rows(buckets["stale"],
             lambda e: "%d days past; last fill %s" % (abs((e["next_due"] - today).days),
                                                       iso(e["last_fill"]) or "none recorded"))
        rows(buckets["no_date"],
             lambda e: "no next-due date; last fill %s" % (iso(e["last_fill"])
                                                           or "none recorded"))
        add("")

    if show_later and buckets["later"]:
        add("LATER (%d)" % len(buckets["later"]))
        rows(buckets["later"], lambda e: "in %d days" % (e["next_due"] - today).days)
        add("")

    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", default=DEFAULT_SHEET,
                        help="spreadsheet to read (default: %(default)s)")
    parser.add_argument("--days", type=int, default=7,
                        help="size of the upcoming window, in days (default: %(default)s)")
    parser.add_argument("--stale-days", type=int, default=60,
                        help="days past due at which a sheet with no later fill row is "
                             "reported as stale instead of overdue (default: %(default)s)")
    parser.add_argument("--today", help="override today's date, as YYYY-MM-DD, for testing")
    parser.add_argument("--all", action="store_true",
                        help="also list prescriptions due beyond the window")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    parser.add_argument("--no-lint", action="store_true",
                        help="skip the spreadsheet checks and report refills only")
    args = parser.parse_args(argv)

    path = os.path.expanduser(args.file)
    if not os.path.isfile(path):
        print("error: no such file: %s" % path, file=sys.stderr)
        return 2

    if args.today:
        today = parse_date(args.today)
        if today is None:
            print("error: --today must be YYYY-MM-DD, got %r" % args.today, file=sys.stderr)
            return 2
    else:
        today = dt.date.today()

    try:
        entries = load(path)
    except ET.ParseError as exc:
        print("error: %s is not parseable as flat-XML ODF: %s" % (path, exc), file=sys.stderr)
        return 1

    if not entries:
        print("error: no sheets found in %s" % path, file=sys.stderr)
        return 1

    buckets: dict[str, list[dict]] = {k: [] for k in
                                      ("overdue", "due_soon", "stale", "later", "no_date")}
    for entry in entries:
        entry["bucket"] = classify(entry, today, args.days, args.stale_days)
        buckets[entry["bucket"]].append(entry)

    lint = [] if args.no_lint else domain_findings(entries)

    if args.json:
        json.dump({
            "file": path,
            "today": today.isoformat(),
            "window_days": args.days,
            "stale_days": args.stale_days,
            "spreadsheet_findings": lint,
            "prescriptions": [{
                "prescription": e["prescription"],
                "next_due": iso(e["next_due"]),
                "next_due_label": e["label"],
                "last_fill": iso(e["last_fill"]),
                "fill_count": e["fill_count"],
                "days_until_due": (e["next_due"] - today).days if e["next_due"] else None,
                "bucket": e["bucket"],
            } for e in entries],
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if lint:
            # Above the report, never instead of it: a spreadsheet nit must not suppress
            # "5 refills past due". Same warn-never-block rule the linter itself follows.
            print("SPREADSHEET CHECKS (%d)" % len(lint))
            for finding in lint:
                print("  %s" % finding)
            print()
        sys.stdout.write(report(buckets, today, args.days, args.stale_days, args.all))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
