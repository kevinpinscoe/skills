#!/usr/bin/env python3
"""Bundle a YouTrack project's still-open issues into one Markdown file.

Selects every issue in one project whose lifecycle Status (prototype 157-2) is
neither "Done" nor "Wont do", exports each one with the existing `yt-export`
tool, and assembles one bundle with `gather --non-interactive`:

    ~/tmp/gather-youtrack-project-<project name>.md

The bundle opens with an index and a dependency overview built only from the
exports' own Dependency Metadata blocks (POE-53), followed by every issue's
complete, unmodified export. Nothing is summarised in place of an export.

Read-only against YouTrack. API reads go through the curl config that
`parzival exec --as ai youtrack-claude-code` delivers in $YOUTRACK_CURL_CONFIG;
the token is never read, printed or written by this script. Python 3 stdlib only.

Exit codes: 0 bundle written; 1 nothing written (error); 2 usage error;
3 bundle written but incomplete (an export failed -- see its limitations section).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

STATUS_FIELD_ID = "157-2"
# Exact configured spellings; "Wont do" has no apostrophe. Checked against the
# live Status bundle at run time, never assumed.
TERMINAL_STATUSES = ("Done", "Wont do")
PUBLIC_BASE_URL = "https://youtrack.kevininscoe.com"
FLDW_HOSTNAME = "kevin"
FLDW_API_BASE = "http://127.0.0.1:9000"
PAGE_SIZE = 100
OUTPUT_DIR = Path.home() / "tmp"
OUTPUT_PREFIX = "gather-youtrack-project-"

ISSUE_LIST_FIELDS = (
    "idReadable,summary,project(shortName),"
    "customFields(name,value(name),projectCustomField(field(id)))"
)
ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9_]*-\d+\b")
BLOCKER_RE = re.compile(
    r"\b(blocked|blocker|blocking|blocks|depends on|dependent on|dependency|"
    r"waiting (?:on|for)|prerequisite|requires|gated|until .{0,40}(?:merge|lands|done))\b",
    re.IGNORECASE,
)
QUOTE_LIMIT = 240


class BundleError(RuntimeError):
    """An expected failure: nothing is written."""


# --------------------------------------------------------------------------- API


def default_api_base() -> str:
    if os.environ.get("YOUTRACK_API_BASE"):
        return os.environ["YOUTRACK_API_BASE"].rstrip("/")
    if socket.gethostname().split(".")[0] == FLDW_HOSTNAME:
        return FLDW_API_BASE
    return PUBLIC_BASE_URL


def curl_fetcher(api_base: str) -> Callable[[str, dict[str, Any] | None], Any]:
    """Return fetch(path, params) that reads through the brokered curl config."""
    config = os.environ.get("YOUTRACK_CURL_CONFIG", "")
    if not config or not os.path.isfile(config):
        raise BundleError(
            "YOUTRACK_CURL_CONFIG is not set. Run this script under "
            "`parzival exec --as ai youtrack-claude-code -- python3 bundle.py ...`."
        )

    def fetch(path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{api_base}/api/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        result = subprocess.run(
            ["curl", "-sS", "--fail-with-body", "-K", config,
             "-H", "Accept: application/json", url],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            detail = (result.stdout or result.stderr).strip()[:300]
            raise BundleError(f"YouTrack read failed for /api/{path}: {detail}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise BundleError(f"YouTrack returned non-JSON for /api/{path}") from exc

    return fetch


def get_all(fetch, path: str, fields: str, extra: dict[str, Any] | None = None) -> list[dict]:
    rows: list[dict] = []
    skip = 0
    while True:
        params = {"fields": fields, "$top": PAGE_SIZE, "$skip": skip, **(extra or {})}
        page = fetch(path, params)
        if not isinstance(page, list):
            raise BundleError(f"Unexpected response while reading /api/{path}")
        rows.extend(r for r in page if isinstance(r, dict))
        if len(page) < PAGE_SIZE:
            return rows
        skip += len(page)


def resolve_project(projects: list[dict], answer: str) -> dict:
    """Match a short name or a full name, case-insensitively; never guess."""
    wanted = answer.strip().casefold()
    if not wanted:
        raise BundleError("No project given.")
    for key in ("shortName", "name"):
        hits = [p for p in projects if str(p.get(key) or "").casefold() == wanted]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise BundleError(f"{answer!r} matches more than one project by {key}.")
    near = sorted(
        f"{p.get('shortName')} ({p.get('name')})" for p in projects
        if wanted in str(p.get("shortName") or "").casefold()
        or wanted in str(p.get("name") or "").casefold()
    )
    hint = f" Close matches: {', '.join(near)}." if near else ""
    raise BundleError(f"No YouTrack project matches {answer!r}.{hint}")


def status_values(fetch, project_id: str) -> list[dict]:
    attachments = fetch(
        f"admin/projects/{project_id}/customFields",
        {"fields": "id,field(id,name)", "$top": 200},
    )
    attachment = next(
        (a for a in attachments or [] if (a.get("field") or {}).get("id") == STATUS_FIELD_ID),
        None,
    )
    if not attachment:
        raise BundleError(f"Status ({STATUS_FIELD_ID}) is not attached to this project.")
    detail = fetch(
        f"admin/projects/{project_id}/customFields/{attachment['id']}",
        {"fields": "bundle(id,values(name,isResolved,archived))"},
    )
    return list((detail.get("bundle") or {}).get("values") or [])


def check_terminal_spellings(values: list[dict]) -> None:
    names = {v.get("name") for v in values}
    missing = [s for s in TERMINAL_STATUSES if s not in names]
    if missing:
        raise BundleError(
            "The Status bundle no longer has the exact value(s) "
            f"{', '.join(repr(m) for m in missing)}; configured values are "
            f"{sorted(n for n in names if n)}. Not guessing a replacement."
        )


def issue_status(issue: dict) -> str | None:
    for field in issue.get("customFields") or []:
        proto = ((field.get("projectCustomField") or {}).get("field") or {}).get("id")
        if proto == STATUS_FIELD_ID:
            value = field.get("value")
            return value.get("name") if isinstance(value, dict) else None
    return None


def issue_sort_key(issue_id: str) -> tuple[str, int]:
    match = re.fullmatch(r"(.+)-(\d+)", issue_id)
    return (match.group(1), int(match.group(2))) if match else (issue_id, 0)


def select_open(issues: list[dict], short_name: str) -> tuple[list[dict], dict[str, int], list[str]]:
    """Return (selected, counts by status, ids of rows from another project)."""
    counts: dict[str, int] = {}
    selected, foreign = [], []
    for issue in issues:
        if (issue.get("project") or {}).get("shortName") != short_name:
            foreign.append(str(issue.get("idReadable")))
            continue
        status = issue_status(issue)
        counts[status or "(no Status)"] = counts.get(status or "(no Status)", 0) + 1
        if status not in TERMINAL_STATUSES:
            selected.append(issue)
    selected.sort(key=lambda i: issue_sort_key(str(i.get("idReadable"))))
    return selected, counts, foreign


# ---------------------------------------------------------------------- exports


def safe_name(project_name: str, short_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", project_name)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-._")[:100].rstrip("-._")
    if not cleaned:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", short_name).strip("-._") or "project"
    return cleaned


def run_yt_export(issue_id: str, out_path: Path) -> tuple[bool, str]:
    env = {k: v for k, v in os.environ.items() if k != "YOUTRACK_CURL_CONFIG"}
    result = subprocess.run(
        ["yt-export", issue_id, "-o", str(out_path)],
        capture_output=True, text=True, env=env,
    )
    ok = result.returncode == 0 and out_path.is_file()
    return ok, (result.stderr or result.stdout).strip()


def parse_export(markdown: str) -> dict[str, Any]:
    """Pull the Dependency Metadata JSON and the free text out of one export."""
    match = re.search(r"^## Dependency Metadata\n\n(`{3,})json\n(.*?)\n\1$", markdown, re.S | re.M)
    metadata = json.loads(match.group(2)) if match else None

    def section(name: str, stop: str | None) -> str:
        start = markdown.find(f"\n## {name}\n")
        if start < 0:
            return ""
        end = markdown.find(f"\n## {stop}\n", start + 1) if stop else -1
        return markdown[start:end if end >= 0 else len(markdown)]

    return {
        "metadata": metadata,
        "description": section("Description", "Links"),
        "comments": section("Comments", None),
    }


# --------------------------------------------------------------------- analysis


def analyse(entries: list[dict]) -> dict[str, Any]:
    """Dependency facts from formal Depend links only, among the selected issues."""
    selected = {e["id"] for e in entries}
    meta = {e["id"]: e["parsed"]["metadata"] for e in entries if e["parsed"]["metadata"]}
    rows: dict[str, dict[str, Any]] = {}
    for issue_id, m in meta.items():
        deps = [r for r in m.get("relationships", []) if r.get("role") == "depends_on"]
        rows[issue_id] = {
            "in_set_open": sorted(
                (r["issue"] for r in deps if r["issue"] in selected), key=issue_sort_key),
            "outside_open": [r for r in deps if r["issue"] not in selected and r.get("terminal") is not True],
            "done": [r for r in deps if r.get("terminal") is True],
            "cross_project": [r for r in deps if r.get("same_project") is False],
            "incomplete": not m.get("relationships_complete", False),
            "inaccessible": m.get("inaccessible_links", []),
        }

    can_start = sorted(
        (i for i, r in rows.items()
         if not r["in_set_open"] and not r["outside_open"] and not r["incomplete"]),
        key=issue_sort_key)

    # Layered working order over in-set edges (Kahn), cycles left over.
    remaining = {i: set(r["in_set_open"]) for i, r in rows.items()}
    layers: list[list[str]] = []
    while True:
        ready = sorted((i for i, d in remaining.items() if not d), key=issue_sort_key)
        if not ready:
            break
        layers.append(ready)
        for i in ready:
            del remaining[i]
        for deps in remaining.values():
            deps.difference_update(ready)
    cycles = find_cycles({i: set(rows[i]["in_set_open"]) for i in remaining})

    relations: dict[str, list[tuple[str, str]]] = {"parent": [], "related": [], "duplicates": [], "other": []}
    for issue_id, m in meta.items():
        for r in m.get("relationships", []):
            role = r.get("role")
            if role in ("parent", "subtasks"):
                pair = (issue_id, r["issue"]) if role == "parent" else (r["issue"], issue_id)
                relations["parent"].append((pair[0], f"subtask of {pair[1]}"))
            elif role == "related":
                # Undirected: one line per pair, whichever end it was read from.
                a, b = sorted((issue_id, r["issue"]), key=issue_sort_key)
                relations["related"].append((a, b))
            elif role in ("duplicates", "duplicated_by"):
                relations["duplicates"].append((issue_id, f"{r.get('label')} {r['issue']}"))
            elif role == "other":
                relations["other"].append((issue_id, f"{r.get('label')} {r['issue']}"))
    for key in relations:
        relations[key] = sorted(set(relations[key]), key=lambda p: (issue_sort_key(p[0]), p[1]))

    return {"rows": rows, "can_start": can_start, "selected": selected, "layers": layers,
            "blocked_by_cycle": sorted(remaining, key=issue_sort_key),
            "cycles": cycles, "relations": relations,
            "no_metadata": sorted((e["id"] for e in entries if not e["parsed"]["metadata"]),
                                  key=issue_sort_key)}


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Strongly connected components with more than one node, or a self-loop."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []
    counter = [0]

    def visit(node: str) -> None:
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for nxt in sorted(graph.get(node, ())):
            if nxt not in graph:
                continue
            if nxt not in index:
                visit(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], index[nxt])
        if low[node] == index[node]:
            comp = []
            while True:
                item = stack.pop()
                on_stack.discard(item)
                comp.append(item)
                if item == node:
                    break
            if len(comp) > 1 or node in graph.get(node, ()):
                result.append(sorted(comp, key=issue_sort_key))

    for node in sorted(graph, key=issue_sort_key):
        if node not in index:
            visit(node)
    return sorted(result)


def text_candidates(entry: dict) -> dict[str, list[str]]:
    """Unconfirmed signals from the issue's own text -- never formal dependencies."""
    m = entry["parsed"]["metadata"] or {}
    linked = {r["issue"] for r in m.get("relationships", [])}
    text = entry["parsed"]["description"] + "\n" + entry["parsed"]["comments"]
    mentions = sorted(
        {k for k in ISSUE_KEY_RE.findall(text) if k != entry["id"] and k not in linked},
        key=issue_sort_key)
    phrases = []
    for line in text.splitlines():
        stripped = " ".join(line.split())
        if stripped.startswith("#") or not BLOCKER_RE.search(stripped):
            continue
        if len(stripped) > QUOTE_LIMIT:
            stripped = stripped[:QUOTE_LIMIT] + " […]"
        if stripped not in phrases:
            phrases.append(stripped)
    return {"mentions": mentions, "phrases": phrases}


# ---------------------------------------------------------------------- render


def md_cell(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def render_header(ctx: dict[str, Any]) -> str:
    project, analysis, entries = ctx["project"], ctx["analysis"], ctx["entries"]
    short = project["shortName"]
    L: list[str] = [
        f"# Open YouTrack issues — {project['name']} ({short})",
        "",
        f"- **Project:** {project['name']}",
        f"- **Short name:** {short}",
        f"- **Project ID:** {project.get('id')}",
        f"- **Project URL:** <{PUBLIC_BASE_URL}/projects/{short}>",
        f"- **Exported:** {ctx['timestamp']} on `{ctx['host']}`",
        "- **Selection:** every issue in this project whose `Status` (`157-2`) is neither "
        "`Done` nor `Wont do` (exact configured spellings, checked against the live Status "
        "bundle). Selection is by `Status`, not `#Unresolved`, so it does not depend on how "
        "the bundles mark resolved states.",
        f"- **Configured Status values:** {', '.join(ctx['status_names'])}",
        f"- **Issues in project:** {ctx['scanned']} — by Status: "
        + ", ".join(f"{k} {v}" for k, v in sorted(ctx["counts"].items())),
        f"- **Included issues:** {len(entries)}",
    ]
    if ctx["export_failures"]:
        L.append(f"- **INCOMPLETE:** {len(ctx['export_failures'])} selected issue(s) could not be "
                 "exported — see *Missing data and limitations*.")

    L += ["", "## Index", ""]
    if entries:
        L += ["| # | Issue | Title | Status | URL |", "|---|---|---|---|---|"]
        for n, e in enumerate(entries, 1):
            L.append(f"| {n} | {e['id']} | {md_cell(e['summary'])} | {md_cell(e['status'] or 'no Status')} "
                     f"| <{PUBLIC_BASE_URL}/issue/{e['id']}> |")
    else:
        L.append("_No open issues: every issue in this project is `Done` or `Wont do`._")

    rows = analysis["rows"]
    L += ["", "## Dependency overview", "",
          "> Built only from formal YouTrack `Depend` links in each export's Dependency Metadata.",
          "> This is a **dependency-based working order, not a critical path**: no issue carries a",
          "> duration estimate (`remaining_effort_minutes` is null), so no path length can be",
          "> calculated. Issues linked from outside this selection are context, not selected work.",
          "", "### Can start or continue now (no open formal dependency)", ""]
    L += [f"- {i}" for i in analysis["can_start"]] or ["_None._"]
    L += ["", "### Waiting on open work in this selection", ""]
    waiting = [(i, r) for i, r in sorted(rows.items(), key=lambda p: issue_sort_key(p[0])) if r["in_set_open"]]
    L += [f"- {i} depends on {', '.join(r['in_set_open'])}" for i, r in waiting] or ["_None._"]
    L += ["", "### Waiting on open work outside this selection", ""]
    outside = [(i, d) for i, r in sorted(rows.items(), key=lambda p: issue_sort_key(p[0])) for d in r["outside_open"]]
    L += [f"- {i} depends on {d['issue']} ({d.get('project')}, {d.get('status') or 'status unknown'})"
          for i, d in outside] or ["_None._"]
    L += ["", "### Blockers already completed", ""]
    done = [(i, d) for i, r in sorted(rows.items(), key=lambda p: issue_sort_key(p[0])) for d in r["done"]]
    L += [f"- {i}: {d['issue']} is {d.get('status')}" for i, d in done] or ["_None._"]
    L += ["", "### Cross-project dependencies", ""]
    cross = [(i, d) for i, r in sorted(rows.items(), key=lambda p: issue_sort_key(p[0])) for d in r["cross_project"]]
    L += [f"- {i} depends on {d['issue']} ({d.get('project')}, {d.get('status') or 'status unknown'})"
          for i, d in cross] or ["_None._"]
    L += ["", "### Working order by layer (issues in one layer can proceed in parallel)", "",
          "> Layers order this selection by its in-selection dependencies only. An issue in an",
          "> early layer may still wait on open work outside the selection (listed above)."]
    L += [""] + [f"{n}. {', '.join(layer)}" for n, layer in enumerate(analysis["layers"], 1)] \
        if analysis["layers"] else ["", "_No issues with readable dependency metadata._"]
    L += ["", "### Cycles", ""]
    if analysis["cycles"]:
        L += [f"- {' ↔ '.join(c)}" for c in analysis["cycles"]]
        L.append(f"- Not orderable while the cycle stands: {', '.join(analysis['blocked_by_cycle'])}")
    else:
        L.append("_None found among formal links in this selection._")
    L += ["", "### Informational relationships (not blocking)", ""]
    labels = {"parent": "Parent/subtask", "related": "Related", "duplicates": "Duplicate", "other": "Other link types"}
    any_rel = False
    def mark(text: str) -> str:
        return ISSUE_KEY_RE.sub(
            lambda m: m.group(0) if m.group(0) in analysis["selected"] else f"{m.group(0)} (outside selection)",
            text)

    for key, label in labels.items():
        for a, b in analysis["relations"][key]:
            L.append(f"- {label}: {mark(a)} — {mark(b)}")
            any_rel = True
    if not any_rel:
        L.append("_None._")

    L += ["", "## Text-only candidates (not formal dependencies)", "",
          "> Found by pattern in descriptions and comments. These are **unconfirmed**: a mention or",
          "> a phrase like \"blocked by\" may or may not be a real dependency. Confirm against the",
          "> export before treating one as a blocker. Quoted lines longer than "
          f"{QUOTE_LIMIT} characters are cut here only; the full text is in the export."]
    any_cand = False
    for e in entries:
        cand = ctx["candidates"].get(e["id"])
        if not cand or not (cand["mentions"] or cand["phrases"]):
            continue
        any_cand = True
        L += ["", f"### {e['id']}", ""]
        if cand["mentions"]:
            L.append(f"- Issue keys mentioned but not formally linked: {', '.join(cand['mentions'])}")
        for phrase in cand["phrases"]:
            L.append(f"- Candidate blocker text: “{phrase}”")
    if not any_cand:
        L += ["", "_None found._"]

    L += ["", "## Missing data and limitations", ""]
    for issue_id, err in ctx["export_failures"]:
        L.append(f"- **{issue_id} was not exported** (yt-export failed: {md_cell(err)[:300]}). "
                 "Its content is absent from this bundle.")
    for issue_id in analysis["no_metadata"]:
        L.append(f"- {issue_id}: export has no Dependency Metadata block; it is left out of the overview.")
    for issue_id, r in sorted(rows.items(), key=lambda p: issue_sort_key(p[0])):
        for hidden in r["inaccessible"]:
            L.append(f"- {issue_id}: {hidden.get('count')} linked issue(s) ({hidden.get('label')}) not "
                     "accessible — status unknown, not treated as complete; it is not counted as able to start now.")
    no_status = [e["id"] for e in entries if not e["status"]]
    if no_status:
        L.append(f"- No readable Status (included, since not terminal): {', '.join(no_status)}")
    if ctx["foreign"]:
        L.append(f"- The project query also returned {len(ctx['foreign'])} issue(s) from another project; "
                 f"they were left out: {', '.join(ctx['foreign'])}")
    L += [
        f"- Duration estimates: none of the {len(entries)} included issues has one, so no critical path.",
        "- Native links only: blockers written only in a description or comment are not formal "
        "dependencies; see *Text-only candidates*.",
        "- Linked issues outside this selection appear as references (key, title, project, Status) "
        "inside each export; their own content is not bundled.",
        "- No export is truncated or summarised. Each one follows below, unmodified, in a fenced "
        "block written by `gather`.",
        "",
        "## Exports",
        "",
        "Each following section is one included issue's complete `yt-export` output, in index order.",
    ]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------ main


def build(args, fetch, exporter=run_yt_export, gather_bin: str = "gather") -> tuple[Path, int]:
    projects = get_all(fetch, "admin/projects", "id,shortName,name,archived")
    project = resolve_project(projects, args.project)
    short = str(project["shortName"])
    values = status_values(fetch, str(project["id"]))
    check_terminal_spellings(values)

    issues = get_all(fetch, "issues", ISSUE_LIST_FIELDS, {"query": f"project: {{{short}}}"})
    selected, counts, foreign = select_open(issues, short)

    out_name = f"{OUTPUT_PREFIX}{safe_name(str(project['name']), short)}.md"
    out_path = OUTPUT_DIR / out_name
    if out_path.exists() and not args.overwrite:
        raise BundleError(f"{out_path} already exists. Re-run with --overwrite to replace it.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"{out_name[:-3]}-exports-", dir=OUTPUT_DIR))
    entries, failures, files = [], [], []
    for issue in selected:
        issue_id = str(issue["idReadable"])
        path = work / f"{issue_id}.md"
        ok, err = exporter(issue_id, path)
        if not ok:
            failures.append((issue_id, err or "no output"))
            continue
        entries.append({"id": issue_id, "summary": issue.get("summary"),
                        "status": issue_status(issue),
                        "parsed": parse_export(path.read_text(encoding="utf-8"))})
        files.append(path)

    ctx = {
        "project": project, "entries": entries, "counts": counts, "foreign": foreign,
        "scanned": sum(counts.values()), "export_failures": failures,
        "status_names": [str(v.get("name")) for v in values],
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": socket.gethostname(), "analysis": analyse(entries),
        "candidates": {e["id"]: text_candidates(e) for e in entries},
    }
    header = work / "00-index.md"
    header.write_text(render_header(ctx), encoding="utf-8")

    cmd = [gather_bin, "--non-interactive", "--dir", str(work), "--output", out_name,
           "--title", f"gather-youtrack-project: {project['name']} ({short})",
           "--file", header.name] + [arg for f in files for arg in ("--file", f.name)]
    if args.overwrite:
        cmd.append("--overwrite")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise BundleError(f"gather did not write the bundle (exit {result.returncode}): "
                          f"{result.stderr.strip()[:500]} — exports kept in {work}")
    written = Path(result.stdout.strip().splitlines()[-1]) if result.stdout.strip() else out_path
    if not args.keep_exports:
        shutil.rmtree(work, ignore_errors=True)
    print(f"Wrote {written.resolve()}")
    print(f"Project {project['name']} ({short}): {ctx['scanned']} issues, "
          f"{len(selected)} open selected, {len(entries)} exported, {len(failures)} failed")
    return written, (3 if failures else 0)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", help="Project short name or full name; prompted for if omitted")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace an existing bundle (otherwise an existing file stops the run)")
    parser.add_argument("--keep-exports", action="store_true",
                        help="Keep the per-issue export directory under ~/tmp")
    parser.add_argument("--api-base", default=None, help="YouTrack API base URL (default: by host)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        if not args.project:
            if not sys.stdin.isatty():
                raise BundleError("No --project given and stdin is not interactive.")
            args.project = input("YouTrack project (short name or full name): ").strip()
        for tool in ("yt-export", "gather", "curl"):
            if shutil.which(tool) is None:
                raise BundleError(f"'{tool}' is not on PATH.")
        _, code = build(args, curl_fetcher(args.api_base or default_api_base()))
        return code
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
