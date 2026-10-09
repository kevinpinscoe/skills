#!/usr/bin/env python3
"""Helper for the youtrack-move-a-youtrack-ticket skill.

Deterministic pieces of the move workflow, so the agent running the skill does
not improvise API payloads or comparison logic.

Offline subcommands (no credentials, run with plain python3):
  check-id ISSUE                 validate an issue ID, print it normalised
  check-export FILE ISSUE        validate a human-run yt-export Markdown file
  risk BEFORE                    pre-move textual-risk report from a snapshot
  compare BEFORE AFTER [--json OUT]
                                 structural + textual preservation check
  followup-text OLD NEW [--report R]
                                 print the POE follow-up description

API subcommands (run through ./yt-move, which wraps them in
`parzival exec --as ai youtrack-claude-code`):
  resolve-issue ISSUE            entity id, readable id and project of an issue
                                 (ISSUE may be a readable ID or an entity id)
  resolve-project PROJECT [--for-issue ID]
                                 project by short name, id or project URL;
                                 with --for-issue, also apply the move refusals
  snapshot ISSUE OUT [--scan ID] [--references-from BEFORE]
                                 full structured snapshot of an issue to JSON;
                                 --scan records other issues mentioning ID,
                                 --references-from re-reads the ones BEFORE found
  move ENTITY_ID PROJECT_ID      POST /api/issues/{id} {"project": ...}, then re-resolve
  create-followup OLD NEW [--report R]
                                 file the POE follow-up issue

Why the textual half exists: on a move YouTrack rewrites the bare old readable
ID to the new one inside issue text -- this issue's comments and description,
and other issues' text too. It leaves `/issue/OLD` URLs, inline code and custom
string fields alone. Observed on KSA-81 -> GLASS-2 (2026-10-04): 234 mentions
rewritten across 67 comments, including literal branch names, `ai-wt/` paths
and commit subjects whose real names never changed. So comment text is not
expected to be identical after a move; it is expected to differ only by
OLD -> NEW substitutions, and each one is classified.

The token never passes through this script: API calls shell out to curl with
-K "$YOUTRACK_CURL_CONFIG", the RAM-backed config parzival renders for its
child process (when-creating-a-youtrack-ticket.md section 14).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

BASE_URL = os.environ.get("YOUTRACK_API_URL", "http://127.0.0.1:9000")
PUBLIC_URL = "https://youtrack.kevininscoe.com"

ISSUE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$")
ENTITY_ID_RE = re.compile(r"^[0-9]+-[0-9]+$")
PROJECT_ID_RE = re.compile(r"^0-[0-9]+$")

PAGE_SIZE = 100  # the server may cap $top; never infer the end from a short page

FOLLOWUP_PROJECT = "POE"
FOLLOWUP_ASSIGNEE = "Claude_Code"
PROTO_STATUS = "157-2"
PROTO_PRIORITY = "157-0"
PROTO_TYPE = "157-1"
PROTO_ASSIGNEE = "157-3"
PROTO_DATE_ENTERED = "157-15"
PROTO_REPO_URL = "157-17"

# The follow-up's code change -- the rewrite utility its Part A creates -- lands
# in this repository, so it owns the ticket's repository metadata
# (when-creating-a-youtrack-ticket.md section 3): a "Repository:" comment with
# the ~/ path, and the forge URL in Repo URL. The URL is derived from the repo's
# origin at run time, never hardcoded. Obsidian note: none, so that comment is
# omitted (section 4). Affected host stays unset: the work is about files and
# YouTrack text, not one host's state (section 6).
FOLLOWUP_REPO = "~/private-tools"
# The shared rewrite utility Part A uses. Which follow-up creates it is decided
# from repository state (Part A, A3), never by ticket number or creation order.
UTILITY_NAME = "yt-rewrite-moved-issue-id.py"
UTILITY_PATH = f"{FOLLOWUP_REPO}/{UTILITY_NAME}"

# Where the move evidence (exports, snapshots, comparison) is kept for a later
# audit. Not ~/tmp, which is a scratchpad and gets cleared.
EVIDENCE_DIR = "~/archives/youtrack/ticket-moves"

# Directories Part A's human-run rg inventory leaves out: scratch space, downloads,
# and the evidence directory the inventory itself is written to. Anchored with a
# leading "/", so they match only directly under ~ (the inventory runs after `cd ~`).
# The system /tmp is outside the search root and is never reached.
INVENTORY_EXCLUDE_DIRS = ("tmp", "Downloads", EVIDENCE_DIR.removeprefix("~/"))
INVENTORY_EXCLUDES = " ".join(f"--glob '!/{d}/**'" for d in INVENTORY_EXCLUDE_DIRS)


def inventory_path(old):
    """Where Part A's rg inventory is written and kept for audit."""
    return f"{EVIDENCE_DIR}/{old}-home-markdown-references.txt"

# String custom fields whose values name real objects (branches, tabs, URLs).
# YouTrack did not rewrite these on KSA-81 -> GLASS-2; if one ever changes by an
# OLD -> NEW substitution it is a historical-artifact rewrite, not a reference.
ARTIFACT_FIELDS = {"Working branch", "Base branch", "Ghostty tab name",
                   "Last reported commit", "Pull request URL", "Repo URL",
                   "Artifact URL", "Tracking file URL", "TODO file URL"}

ISSUE_FIELDS = (
    "id,idReadable,numberInProject,summary,description,created,updated,resolved,"
    "votes,reporter(login),project(id,shortName,name),tags(id,name),"
    "customFields(name,$type,projectCustomField(field(id)),"
    "value(id,name,login,presentation,minutes,text))"
)
COMMENT_FIELDS = "id,text,created,updated,deleted,author(login),attachments(id,name)"
ATTACHMENT_FIELDS = "id,name,size,mimeType,created,removed,author(login),comment(id)"
LINK_FIELDS = "direction,linkType(name),issues(id,idReadable)"
WORKITEM_FIELDS = "id,date,duration(minutes),author(login),text"
REF_ISSUE_FIELDS = "id,idReadable,summary,description,project(shortName)"

# The only coverage claim the cross-issue scan may make. Claude_Code sees only
# the projects whose teams it is on, so this is never "all issues in YouTrack".
SCAN_CLAIM = "searched all issues visible to the Claude_Code identity to exhaustion"

WARNING = ("YouTrack may rewrite the old readable issue ID inside descriptions/comments "
           "when the issue moves. References should change, but literal branch names, "
           "worktree paths, commit subjects, commands, filenames or quoted logs may "
           "become historically inaccurate.")


class Fail(Exception):
    """A refusal or error to report and exit non-zero on."""


# --------------------------------------------------------------- validation

def normalise_issue_id(raw):
    """Accept KTA-19 or an issue URL; return the upper-case readable ID."""
    value = raw.strip()
    if "/issue/" in value:
        value = value.split("/issue/", 1)[1].split("/")[0].split("?")[0]
    value = value.upper()
    if not ISSUE_ID_RE.match(value):
        raise Fail(f"not a YouTrack issue ID: {raw!r}")
    return value


def issue_ref(raw):
    """An immutable entity id (3-2509) as given, otherwise a readable ID."""
    value = raw.strip()
    return value if ENTITY_ID_RE.match(value) else normalise_issue_id(value)


def boundary_pattern(issue_id):
    """The filesystem match contract: the ID, never the start of a longer key."""
    return r"(?<![A-Za-z0-9-])" + re.escape(issue_id) + r"(?![0-9])"


def check_export(path, issue_id, project_name=None):
    """Return a list of problems with a yt-export file; empty means valid."""
    problems = []
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return [f"file does not exist: {path}"]
    if os.path.getsize(path) == 0:
        return [f"file is empty: {path}"]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    if not first.startswith(f"# {issue_id} — "):
        problems.append(f"first heading is not '# {issue_id} — …': {first[:80]!r}")
    if f"/issue/{issue_id}>" not in text:
        problems.append(f"no '/issue/{issue_id}' URL line")
    if project_name is not None:
        if f"- **Project:** {project_name}" not in text:
            problems.append(f"project line does not name {project_name!r}")
    if "## Custom fields" not in text:
        problems.append("no '## Custom fields' section (not a yt-export file?)")
    return problems


# ------------------------------------------------------- text-rewrite analysis

def find_occurrences(text, old):
    """Start offsets of `old` in text, never as the start of a longer number."""
    out, i = [], text.find(old)
    while i != -1:
        nxt = text[i + len(old):i + len(old) + 1]
        if not nxt.isdigit():
            out.append(i)
        i = text.find(old, i + 1)
    return out


def rewrite_walk(before, after, old, new):
    """Explain `after` as `before` with some occurrences of old turned into new.

    Returns a list of (offset_in_before, rewritten) pairs, or None when `after`
    differs from `before` in any other way (an unexplained change). Greedy is
    exact here: the text between occurrences is literal, and old and new come
    from different projects, so neither can be a prefix of the other.
    """
    result, pos, prev = [], 0, 0
    for i in find_occurrences(before, old):
        seg = before[prev:i]
        if not after.startswith(seg, pos):
            return None
        pos += len(seg)
        if after.startswith(old, pos):
            result.append((i, False)); pos += len(old)
        elif after.startswith(new, pos):
            result.append((i, True)); pos += len(new)
        else:
            return None
        prev = i + len(old)
    return result if after[pos:] == before[prev:] else None


_COMMIT_RE = re.compile(
    r"\b(feat|fix|docs|chore|refactor|test|ci|build|perf|style|revert)(\([^)]*\))?!?:\s")
_CMD_BEFORE_RE = re.compile(
    r"(?i)\b(branch(es)?|worktrees?|checkout|switch|git\s+log|git\s+push|git\s+branch|"
    r"rebase|merge[ds]?|tag(ged)?|base|stacked\s+on|onto|into|local|remote|upstream)"
    r"\b[\s:`'\"(]*$")
_GIT_AFTER_RE = re.compile(
    r"(?i)[`'\"]?\s*(=\s*[0-9a-f]{7}|\s(branch(es)?|worktrees?|tip|fast-forward\w*|"
    r"at\s+[0-9a-f]{7})\b)")


def classify(text, i, old):
    """Classify one occurrence: ('reference'|'artifact', reason).

    Heuristic by design: it warns and sorts evidence, it does not decide alone.
    """
    ls = text.rfind("\n", 0, i) + 1
    le = text.find("\n", i)
    le = len(text) if le == -1 else le
    pre, post = text[ls:i], text[i + len(old):le]
    fenced = sum(1 for ln in text[:ls].splitlines() if ln.lstrip().startswith("```")) % 2
    if re.search(r"/issue/$", pre) or re.search(r"https?://\S*$", pre):
        return "reference", "url"
    if fenced:
        return "artifact", "code block"
    if pre.count("`") % 2:
        return "artifact", "inline code"
    if pre.endswith("/") or re.search(r"\.\.$", pre):
        return "artifact", "path or ref range"
    if re.match(r"[-_/][A-Za-z0-9]", post) or re.match(r"\.(md|txt|json|sh|py|log|ya?ml|go)\b", post):
        return "artifact", "suffixed name or filename"
    if _CMD_BEFORE_RE.search(pre[-40:]):
        return "artifact", "branch, worktree or command"
    if _GIT_AFTER_RE.match(post):
        return "artifact", "branch or worktree"
    if _COMMIT_RE.search(pre):
        return "artifact", "commit subject"
    return "reference", "issue reference"


def likely_rewritten(text, i, old):
    """Predict whether YouTrack will rewrite this occurrence (KSA-81 behaviour)."""
    ls = text.rfind("\n", 0, i) + 1
    pre = text[ls:i]
    nxt = text[i + len(old):i + len(old) + 1]
    if re.search(r"/issue/$", pre) or re.search(r"https?://\S*$", pre):
        return False
    # Observed on KSA-81: a code span holding exactly the key was left alone, but
    # code spans with more in them (`git log main..KSA-81`, `KSA-81-uat`) were not.
    if pre.endswith("`") and text[i + len(old):i + len(old) + 1] == "`":
        return False
    if nxt and (nxt.isalnum() or nxt == "_"):
        return False
    return True


def snippet(text, i, width=40):
    s = text[max(0, i - width):i + width].replace("\n", " ")
    return s.strip()


def text_units(snap, artifact_fields=ARTIFACT_FIELDS):
    """Every textual location of an issue snapshot: label -> (text, field_is_artifact)."""
    units = {"summary": (snap.get("summary") or "", False),
             "description": (snap.get("description") or "", False)}
    for c in snap.get("comments") or []:
        units[f"comment {c['id']}"] = (c.get("text") or "", False)
    for a in snap.get("attachments") or []:
        units[f"attachment {a['id']} name"] = (a.get("name") or "", True)
    if isinstance(snap.get("workItems"), list):
        for w in snap["workItems"]:
            units[f"work item {w['id']}"] = (w.get("text") or "", False)
    for f in snap.get("customFields") or []:
        v = f.get("value")
        if isinstance(v, dict) and isinstance(v.get("text"), str):
            v = v["text"]
        if isinstance(v, str):
            units[f"field {f['name']}"] = (v, f["name"] in artifact_fields)
    return units


def analyse_units(issue_label, before_units, after_units, old, new, tally):
    """Compare matching text units; add counts and locations to `tally`."""
    for label, (btext, is_artifact_field) in before_units.items():
        if label not in after_units:
            continue  # structural code reports missing comments/attachments
        atext = after_units[label][0]
        if btext == atext:
            tally["left_as_written"] += len(find_occurrences(btext, old))
            continue
        walk = rewrite_walk(btext, atext, old, new)
        if walk is None:
            tally["unexplained"].append({"issue": issue_label, "where": label,
                                         "before": btext[:300], "after": atext[:300]})
            continue
        for i, rewritten in walk:
            if not rewritten:
                tally["left_as_written"] += 1
                continue
            kind, reason = ("artifact", "artifact field") if is_artifact_field \
                else classify(btext, i, old)
            if kind == "reference":
                tally["reference_rewrites"] += 1
            else:
                tally["artifact_rewrites"].append({
                    "issue": issue_label, "where": label, "reason": reason,
                    "before": snippet(btext, i)})


# ---------------------------------------------------------------- API layer

def api(method, path, params=None, body=None):
    cfg = os.environ.get("YOUTRACK_CURL_CONFIG")
    if not cfg:
        raise Fail("YOUTRACK_CURL_CONFIG is not set: run API subcommands through ./yt-move")
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="(),$")
    cmd = ["curl", "-sS", "-K", cfg, "-H", "Accept: application/json",
           "-X", method, "-w", "\n%{http_code}", url]
    data = None
    if body is not None:
        cmd[1:1] = ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        data = json.dumps(body)
    proc = subprocess.run(cmd, input=data, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Fail(f"curl failed ({proc.returncode}): {proc.stderr.strip()}")
    payload, _, status = proc.stdout.rpartition("\n")
    if not status.isdigit() or int(status) >= 300:
        raise Fail(f"{method} {path} -> HTTP {status}: {payload[:400]}")
    return json.loads(payload) if payload.strip() else None


def paginate(fetch):
    """Call fetch(skip, top) until an empty page. Never stops on a short page,
    because the server may cap $top; refuses to loop on a pager that stalls."""
    out, skip, seen_first = [], 0, set()
    while True:
        batch = fetch(skip, PAGE_SIZE)
        if not batch:
            return out
        first = json.dumps(batch[0], sort_keys=True)
        if first in seen_first:
            raise Fail(f"pager stalled at offset {skip}: the same page came back twice")
        seen_first.add(first)
        out.extend(batch)
        skip += len(batch)


def api_list(path, fields, extra=None):
    def fetch(skip, top):
        params = {"fields": fields, "$top": top, "$skip": skip}
        params.update(extra or {})
        return api("GET", path, params)
    return paginate(fetch)


def resolve_issue(issue):
    return api("GET", f"/api/issues/{issue}",
               {"fields": "id,idReadable,summary,project(id,shortName,name)"})


def has_searchable_issue(short_name):
    """True when a search finds at least one issue in the project.

    Template projects are excluded from YouTrack's search index, so their issues
    are never found (when-creating-a-youtrack-ticket.md section 1). An ordinary
    project with issues always returns one.
    """
    try:
        found = api("GET", "/api/issues", {"query": f"project: {short_name}",
                                           "$top": 1, "fields": "idReadable"})
    except Fail:
        return False
    return bool(found)


def resolve_project(raw):
    value = raw.strip()
    if "/projects/" in value:
        value = value.split("/projects/", 1)[1].split("/")[0].split("?")[0]
    projects = api_list("/api/admin/projects", "id,shortName,name,archived,template")
    for p in projects:
        if p["id"] == value or p["shortName"].upper() == value.upper():
            # The Claude_Code token is not shown `template` or `archived` (measured
            # 2026-10-04: absent even for TMPL), so a missing key means unknown,
            # never false. refuse_destination() does not rely on them alone.
            p["searchable_issue"] = has_searchable_issue(p["shortName"])
            return p
    raise Fail(f"no YouTrack project matches {raw!r} (visible to Claude_Code)")


def refuse_destination(issue, project):
    """Raise if moving `issue` into `project` must not happen. Fails closed."""
    name = project["shortName"]
    if (project.get("template") is True or name.upper() == "TMPL"
            or "template" in project.get("name", "").lower()):
        raise Fail(f"{name} is a template project: an issue moved there cannot be "
                   "edited, found or removed again")
    if not project.get("searchable_issue"):
        raise Fail(f"no issue in {name} is findable by search. Template projects are "
                   f"excluded from search, so {name} cannot be told apart from one. If it "
                   "is a new ordinary project, file one issue there first, then retry")
    if project.get("archived") is True:
        raise Fail(f"{name} is archived")
    if issue["project"]["id"] == project["id"]:
        raise Fail(f"{issue['idReadable']} is already in {name}")


def fetch_ref_issue(entity_id, keep_comment=None):
    """One other issue's text: summary, description, and comments (filtered)."""
    data = api("GET", f"/api/issues/{entity_id}", {"fields": REF_ISSUE_FIELDS})
    comments = api_list(f"/api/issues/{entity_id}/comments", COMMENT_FIELDS)
    data["comments"] = [c for c in comments if keep_comment is None or keep_comment(c)]
    return data


def scan_references(issue_id, exclude_entity):
    """Every other issue whose text mentions issue_id, by exhaustive paging."""
    queries = [issue_id, f'"{issue_id}"', f'"issue/{issue_id}"']
    found = {}
    for q in queries:
        for hit in api_list("/api/issues", "id,idReadable", {"query": q}):
            if hit["id"] != exclude_entity:
                found[hit["id"]] = hit["idReadable"]
    refs = []
    for eid in sorted(found):
        data = fetch_ref_issue(eid, lambda c: find_occurrences(c.get("text") or "", issue_id))
        text = (data.get("summary") or "") + "\n" + (data.get("description") or "")
        if find_occurrences(text, issue_id) or data["comments"]:
            refs.append(data)
    return {"queries": queries, "hits": len(found), "complete": True,
            "coverage": SCAN_CLAIM}, refs


def snapshot(issue, scan=None, references_from=None):
    data = api("GET", f"/api/issues/{issue}", {"fields": ISSUE_FIELDS})
    eid = data["id"]
    data["comments"] = api_list(f"/api/issues/{eid}/comments", COMMENT_FIELDS)
    data["attachments"] = api_list(f"/api/issues/{eid}/attachments", ATTACHMENT_FIELDS)
    data["links"] = api("GET", f"/api/issues/{eid}/links", {"fields": LINK_FIELDS})
    try:
        data["workItems"] = api_list(f"/api/issues/{eid}/timeTracking/workItems",
                                     WORKITEM_FIELDS)
    except Fail as exc:  # time tracking off, or not visible to this token
        data["workItems"] = {"unavailable": str(exc)[:200]}
    if references_from:
        before = _load(references_from)
        ids = {c["id"] for r in before.get("referencing_issues", []) for c in r["comments"]}
        data["referencing_issues"] = []
        for r in before.get("referencing_issues", []):
            try:
                data["referencing_issues"].append(
                    fetch_ref_issue(r["id"], lambda c, ids=ids: c["id"] in ids))
            except Fail as exc:  # recorded, and compare() treats it as unverifiable
                data["referencing_issues"].append(
                    {"id": r["id"], "idReadable": r["idReadable"], "unreadable": str(exc)[:200]})
    if scan:
        meta, refs = scan_references(scan, eid)
        if references_from:
            known = {r["id"] for r in data["referencing_issues"]}
            data["unclassified_referencing_issues"] = [
                {"id": r["id"], "idReadable": r["idReadable"]}
                for r in refs if r["id"] not in known]
        else:
            data["referencing_issues"] = refs
        data["_scan"] = meta
    data["_snapshot"] = {"taken": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                         "requested": issue}
    return data


def move(entity_id, project_id):
    if not ENTITY_ID_RE.match(entity_id):
        raise Fail(f"not an issue entity id: {entity_id!r} (expected e.g. 3-2509)")
    if not PROJECT_ID_RE.match(project_id):
        raise Fail(f"not a project database id: {project_id!r} (expected e.g. 0-50)")
    refuse_destination(resolve_issue(entity_id), resolve_project(project_id))
    # Move by updating the issue's project attribute. JetBrains also documents
    # POST /api/issues/{id}/project with {"id": ...}, but on this instance
    # (YouTrack 2026.2, build 17765) that returned 200 and moved nothing:
    # KSA-117 -> GLASS, 2026-10-04. The re-read below is what caught it, and it
    # stays: a write that reports success is only proven by the read.
    api("POST", f"/api/issues/{entity_id}",
        {"fields": "id,idReadable,project(id,shortName)"}, {"project": {"id": project_id}})
    after = resolve_issue(entity_id)
    if after["project"]["id"] != project_id:
        raise Fail(f"move reported success but issue is in {after['project']['shortName']}")
    return after


# ------------------------------------------------------------ risk analysis

def risk(before, old):
    """Pre-move textual-risk report over the issue and the issues referencing it."""
    rows = []

    def scan(issue_label, units):
        for label, (text, is_field) in units.items():
            for i in find_occurrences(text, old):
                kind, reason = ("artifact", "artifact field") if is_field \
                    else classify(text, i, old)
                rows.append({"issue": issue_label, "where": label, "kind": kind,
                             "reason": reason, "likely_rewritten":
                             (not is_field) and likely_rewritten(text, i, old),
                             "text": snippet(text, i)})

    scan(before["idReadable"], text_units(before))
    for r in before.get("referencing_issues") or []:
        scan(r["idReadable"], text_units(r, artifact_fields=set()))
    return rows


# --------------------------------------------------------------- comparison

def _norm_value(v):
    if isinstance(v, list):
        return sorted((_norm_value(x) for x in v), key=json.dumps)
    if isinstance(v, dict):
        for key in ("login", "name", "text", "minutes", "presentation"):
            if v.get(key) is not None:
                return {key: v[key]}
        return None  # e.g. an empty PeriodValue {"$type": "PeriodValue"}
    return v


def _empty(v):
    return v is None or v == [] or v == ""


def _login(x):
    return (x or {}).get("login")


def _is_text(v):
    return isinstance(v, str) or (isinstance(v, dict) and "text" in v)


def compare(before, after):
    """Return a report dict: structural problems, text-rewrite tally, notes."""
    old, new = before["idReadable"], after["idReadable"]
    rep = {"old": old, "new": new, "immutable_id": "PASS", "structural": [],
           "scan": "run" if before.get("_scan") else "not run",
           "notes": [], "reference_rewrites": 0, "artifact_rewrites": [],
           "unexplained": [], "left_as_written": 0, "other_issues": 0,
           "unverifiable_other_issues": [],
           "unclassified_other_issues": after.get("unclassified_referencing_issues", [])}
    prob, note = rep["structural"].append, rep["notes"].append

    if before.get("id") != after.get("id"):
        rep["immutable_id"] = "FAIL"
        prob(f"entity id differs ({before.get('id')} vs {after.get('id')}): not the same issue")
        return rep
    if before["project"].get("id") and before["project"].get("id") == after["project"].get("id"):
        prob("project did not change")
    note(f"project: {before['project'].get('shortName')} -> {after['project'].get('shortName')}")

    for key in ("created", "resolved", "votes"):
        if key in before and before.get(key) != after.get(key):
            prob(f"{key} changed: {before.get(key)} -> {after.get(key)}")
    if _login(before.get("reporter")) != _login(after.get("reporter")):
        prob("reporter changed")
    if sorted(t["name"] for t in before.get("tags", [])) != \
            sorted(t["name"] for t in after.get("tags", [])):
        prob("tags changed")

    # Custom fields: non-text values must be identical; text values are judged
    # by the text analysis below (text_units() includes them).
    bf = {f["name"]: _norm_value(f.get("value")) for f in before.get("customFields", [])}
    af = {f["name"]: _norm_value(f.get("value")) for f in after.get("customFields", [])}
    for name, b in bf.items():
        if _empty(b):
            continue
        if name not in af:
            prob(f"custom field {name!r} lost (was {json.dumps(b)})")
        elif af[name] != b and not (_is_text(b) and _is_text(af[name])):
            prob(f"custom field {name!r} changed: {json.dumps(b)} -> {json.dumps(af[name])}")
    for name, a in af.items():
        if not _empty(a) and _empty(bf.get(name)):
            prob(f"custom field {name!r} gained a value: {json.dumps(a)}")

    # Comments: same ids, authors, creation times, deletion state, attachments.
    bc = {c["id"]: c for c in before.get("comments", [])}
    ac = {c["id"]: c for c in after.get("comments", [])}
    if set(bc) - set(ac):
        prob(f"comments missing after the move: {sorted(set(bc) - set(ac))}")
    if set(ac) - set(bc):
        prob(f"comments that did not exist before: {sorted(set(ac) - set(bc))}")
    for cid in sorted(set(bc) & set(ac)):
        b, a = bc[cid], ac[cid]
        for key in ("created", "deleted"):
            if key in b and key in a and b[key] != a[key]:
                prob(f"comment {cid} {key} changed")
        if _login(b.get("author")) != _login(a.get("author")):
            prob(f"comment {cid} author changed")
        if "attachments" in b and "attachments" in a and \
                sorted(x["id"] for x in b["attachments"] or []) != \
                sorted(x["id"] for x in a["attachments"] or []):
            prob(f"comment {cid} attachments changed")
        if "updated" in b and "updated" in a and b["updated"] != a["updated"]:
            if b.get("text") == a.get("text"):
                prob(f"comment {cid} updated time changed with no text change")
            else:
                note(f"comment {cid} updated time changed along with its text")
    note(f"comments: {len(bc)} before, {len(ac)} after")

    def att_key(x):
        return (x["id"], x.get("size"), x.get("mimeType"), x.get("created"), x.get("removed"))
    if sorted(map(att_key, before.get("attachments", []))) != \
            sorted(map(att_key, after.get("attachments", []))):
        prob("attachments differ (identity, size, type, creation or removal)")

    # Key linked issues by entity id when both snapshots carry it; an older
    # snapshot may hold only readable ids, which a move of *this* issue leaves alone.
    def all_have_id(snap):
        return all("id" in i for l in snap.get("links") or [] for i in l.get("issues") or [])
    key = "id" if all_have_id(before) and all_have_id(after) else "idReadable"

    def link_set(snap):
        return sorted((l.get("direction"), (l.get("linkType") or {}).get("name"), i.get(key))
                      for l in snap.get("links") or [] for i in l.get("issues") or [])
    if link_set(before) != link_set(after):
        prob("links differ")

    bw, aw = before.get("workItems"), after.get("workItems")
    if isinstance(bw, list) and isinstance(aw, list):
        def wi(w):
            return (w["id"], w.get("date"), (w.get("duration") or {}).get("minutes"),
                    _login(w.get("author")))
        if sorted(map(wi, bw)) != sorted(map(wi, aw)):
            prob("work items differ")
    elif isinstance(bw, list) and bw:
        prob(f"{len(bw)} work items before, but none readable after")

    analyse_units(new, text_units(before), text_units(after), old, new, rep)

    # Other issues whose text mentioned OLD before the move.
    after_refs = {r["id"]: r for r in after.get("referencing_issues", [])}
    for r in before.get("referencing_issues", []):
        rep["other_issues"] += 1
        a = after_refs.get(r["id"])
        if a is None or a.get("unreadable"):
            # Fails toward review, never toward clean: the promised check of this
            # issue's side effects could not be made.
            rep["unverifiable_other_issues"].append({
                "issue": r["idReadable"], "where": "whole issue",
                "reason": (a or {}).get("unreadable") or "not re-read after the move"})
            continue
        missing = {c["id"] for c in r["comments"]} - {c["id"] for c in a["comments"]}
        for cid in sorted(missing):
            rep["unverifiable_other_issues"].append({
                "issue": r["idReadable"], "where": f"comment {cid}",
                "reason": "captured before the move, not readable after it"})
        analyse_units(r["idReadable"], text_units(r, set()), text_units(a, set()),
                      old, new, rep)
    return rep


def verdicts(rep):
    """(structural, text, exit code): 0 clean, 3 needs remediation, 1 fail."""
    structural = "PASS" if not rep["structural"] else "FAIL"
    if rep["immutable_id"] == "FAIL" or rep["structural"] or rep["unexplained"]:
        text, code = "FAIL", 1
    elif (rep["artifact_rewrites"] or rep["unclassified_other_issues"]
          or rep.get("unverifiable_other_issues")):
        text, code = "NEEDS REMEDIATION", 3
    else:
        text, code = "CLEAN", 0
    return structural, text, code


def render(rep):
    structural, text, _ = verdicts(rep)
    lines = [f"note: {n}" for n in rep["notes"]]
    lines += [f"STRUCTURAL: {p}" for p in rep["structural"]]
    lines += [f"UNEXPLAINED: {u['issue']} {u['where']}" for u in rep["unexplained"]]
    lines += [f"ARTIFACT: {a['issue']} {a['where']} ({a['reason']}): …{a['before']}…"
              for a in rep["artifact_rewrites"]]
    lines += [f"UNCLASSIFIED: {u['idReadable']} mentions {rep['new']} but was not in the "
              "pre-move evidence" for u in rep["unclassified_other_issues"]]
    lines += [f"UNVERIFIABLE: {u['issue']} {u['where']}: {u['reason']}"
              for u in rep.get("unverifiable_other_issues", [])]
    lines += [
        f"Moved: {rep['old']} -> {rep['new']}",
        f"Immutable issue ID preserved: {rep['immutable_id']}",
        f"Structural preservation: {structural}",
        f"Expected YouTrack text rewrites: {rep['reference_rewrites']}",
        f"Historical-artifact rewrites: {len(rep['artifact_rewrites'])}",
        f"Unexplained changes: {len(rep['unexplained'])}",
        f"Old-ID mentions left as written (URLs, inline code, fields): {rep['left_as_written']}",
        f"Other issues compared: {rep['other_issues']}; mentioning {rep['new']} with no "
        f"pre-move evidence: {len(rep['unclassified_other_issues'])}; could not be "
        f"re-checked: {len(rep.get('unverifiable_other_issues', []))}",
        "Cross-issue scan: " + (SCAN_CLAIM if rep.get("scan") == "run" else "not run"),
        f"Text preservation: {text}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- follow-up

def _remediation_needed(report):
    return bool(report and (report["artifact_rewrites"] or report["unclassified_other_issues"]
                            or report.get("unverifiable_other_issues")))


def followup_summary(old, new, report=None):
    if _remediation_needed(report):
        return f"Update Markdown references and restore historical text after {old} moved to {new}"
    return f"Update Markdown references after {old} moved to {new}"


def evidence_paths(old, new):
    """The move's evidence files, as (description, full ~/ path) pairs.

    The follow-up ticket lists every one of these by full path, and
    create_followup() refuses to file it unless each exists and reads back.
    """
    d = EVIDENCE_DIR
    return [
        ("pre-move yt-export (human-run)", f"{d}/{old}-before-project-move.md"),
        ("post-move yt-export (human-run)", f"{d}/{new}-after-project-move.md"),
        ("pre-move API snapshot", f"{d}/{old}-before-project-move.api.json"),
        ("post-move API snapshot", f"{d}/{new}-after-project-move.api.json"),
        ("comparison report (text)", f"{d}/{old}-to-{new}-preservation-check.txt"),
        ("comparison report (JSON)", f"{d}/{old}-to-{new}-preservation-check.json"),
    ]


def missing_evidence(old, new):
    """Return the evidence paths that are absent or empty on this host."""
    missing = []
    for _, path in evidence_paths(old, new):
        full = os.path.expanduser(path)
        if not os.path.isfile(full) or os.path.getsize(full) == 0:
            missing.append(path)
    return missing


def followup_text(old, new, report=None, report_path=None, max_locations=60):
    pat = boundary_pattern(old)
    inv = inventory_path(old)
    evidence = "\n".join(f"- {path} — {what}" for what, path in evidence_paths(old, new))
    canonical = {os.path.expanduser(p) for _, p in evidence_paths(old, new)}
    if report_path and os.path.expanduser(report_path) not in canonical:
        evidence += f"\n- {report_path} — comparison report as passed to this helper"
    head = f"""Old issue ID: {old}
New issue ID: {new}

{old} was moved to another project with the native YouTrack API move and is now {new}: {PUBLIC_URL}/issue/{new}
Cross-issue scan coverage: {SCAN_CLAIM}. Issues in projects that identity cannot see were not scanned.
The old key {old}, and every URL {PUBLIC_URL}/issue/{old}, still resolve to the same issue.

Move evidence, by full path (kept for audit, never rewritten or deleted by this work):
{evidence}
"""
    part_a = f"""
# Part A — home-directory Markdown references

YouTrack's own rewrite never touches the filesystem: Git repositories, Markdown files, RUNBOOKs and `CHECKPOINT.md` files still say {old}.

## A1 — the inventory is HUMAN-generated

AI agents are forbidden from running recursive `rg`, `ripgrep` or `ugrep` searches. The installed wrapper (`~/tools/rg` -> `human-only-search-guard`) refuses non-interactive callers on purpose. Do not bypass, replace or evade it, and never invoke the underlying binary directly.

Ask Kevin to run this from his own interactive terminal, answering the wrapper's "Are you human?" prompt himself. Hand it to him as a `~/tmp` script plus a single `bash ~/tmp/<name>.sh` line, per `root-directive.md`, because it is too long to paste safely:

```bash
mkdir -p {EVIDENCE_DIR}
cd ~
rg -n -P --glob '*.md' \\
  {INVENTORY_EXCLUDES} \\
  '{pat}' ~ > {inv}
```

Kevin then reports the path of the generated file. **Do not rerun `rg`**, and do not go looking for files the inventory does not list. (By default `rg` skips hidden and gitignored files. That is accepted; the inventory is the scope.)

The `cd ~` is required. A `--glob` that starts with `/` is anchored to the current directory, so with it each exclusion names exactly one directory under the home directory: `~/tmp`, `~/Downloads` and `{EVIDENCE_DIR}`. A `tmp/` directory inside some repository is still searched. The system `/tmp` lies outside the search root, and `rg` does not follow symlinks without `-L`, so it is never searched either.

The inventory is written to `{inv}`, beside the move evidence, and is **kept for audit**. Never delete, move or rewrite it. Like the evidence above, it is not a rewrite target.

## A2 — the matching contract

{old} is matched only when the character before it is not an ASCII letter, digit or hyphen, and the character after it is not a digit. The pattern is `{pat}`. The inventory and the rewrite utility share this one contract, so the inventory says exactly what the utility will change.

| Text | Rewrite? |
|---|---|
| `{old}`, `({old})`, `{old}.`, `{old},`, `.../issue/{old}` | yes |
| `{old}0`, `{old}1`, `X{old}`, `ABC-{old}` | no |

## A3 — Ensure the rewrite utility exists (bootstrap or reuse)

The rewrites in A6 use one shared utility, `{UTILITY_PATH}`, owned by the repository `~/private-tools`. Before rewriting anything, decide from **repository state** which of three cases applies. Every check below names explicit refs, files or pull requests; none of them is a recursive filesystem search.

> **An open POE ticket is not a lock. A planned implementation is not a lock.** Only concrete implementation state — a tracked utility on main, an implementation PR, or an active recorded branch/worktree with committed implementation — establishes ownership. If no such state exists, the current follow-up is allowed to bootstrap the utility.

**File presence is not ownership.** These establish concrete, *active* ownership:

- a currently open `private-tools` pull request adding or modifying the canonical utility;
- an active recorded ticket, lane or worktree with committed implementation, where that ticket or lane explicitly identifies the branch or worktree as owning the utility;
- a pushed branch with committed implementation **plus** current recorded ownership tying it to an active ticket or lane.

These do **not** establish ownership by themselves: another open POE ticket merely mentioning or planning the utility; an untracked local file; a remote branch containing the file with no current owning ticket, lane or pull request; an old merged branch; an abandoned or stale branch.

How to read the state:

- On main: `git -C ~/private-tools fetch origin`, then `git -C ~/private-tools ls-tree --name-only origin/main -- {UTILITY_NAME}`. Output means it is tracked on main; an untracked local file does not count.
- Open pull requests against `private-tools` (Gitea, `kinscoe/private-tools`) whose changed files include `{UTILITY_NAME}`.
- Pushed branches: for each `origin/*` ref, `git -C ~/private-tools ls-tree --name-only <ref> -- {UTILITY_NAME}`. A hit is evidence to investigate, not a lock: file existence on a remote branch is not sufficient. Confirm that the branch is actively owned by a current implementation ticket/lane or open PR. Otherwise report the stale/unowned branch and continue determining whether the current ticket should bootstrap the utility. If an apparently stale branch leaves real doubt, ask Kevin rather than assuming it owns the implementation.
- Worktrees and lanes: `git -C ~/private-tools worktree list`, and the `## Lane` sections of `~/private-tools/CHECKPOINT.md`. Only a worktree or branch with **committed** implementation of this file, recorded as owning it, counts.

### Case 1 — the utility already exists on `private-tools` main

1. Confirm it is tracked by git on `main`, not an untracked or local-only file.
2. Inspect it and its tests.
3. Confirm it implements the contract in A4.
4. Run its tests.
5. If the tests and the contract pass, reuse it.
6. Do not create another implementation.

If it exists but does not meet the A4 contract, STOP and report the mismatch. Do not modify a shared utility as part of this Markdown work without Kevin's approval.

### Case 2 — absent from main, but a concrete implementation is in progress

Another open POE issue is not, by itself, proof that someone else owns the implementation, and neither is a branch that merely contains the file. This case applies only when **active ownership**, as defined above, exists: an open `private-tools` pull request for the utility, or committed implementation on a branch or worktree that a current ticket or lane explicitly records as owning it. If it does:

1. Identify the owning ticket, branch and pull request.
2. Record the dependency in a comment on this POE issue.
3. STOP before performing any rewrite.
4. Tell Kevin exactly which pull request or implementation must land.
5. Once it is merged, update `~/private-tools` main, verify the utility and its tests from main (Case 1), then resume this same POE ticket.

Never write a competing copy. If two genuinely active concrete implementations exist at the same time, STOP both paths and ask Kevin which one owns the canonical utility; do not race or merge them.

### Case 3 — absent, and no concrete implementation exists

**This POE ticket becomes the bootstrap owner.** Another open ticket that only says it plans to create the utility does not block this case, and neither does a stale or unowned branch that contains the file (report it). Only active ownership, as defined above, sends you to Case 2.

1. Create this ticket's normal `private-tools` worktree and branch (`~/private-tools/ai-wt/<this issue>`, branch named after this issue), recorded on this issue per the directives.
2. Implement the canonical utility there, to the A4 contract.
3. Add the tests listed in A5.
4. Run the tests.
5. Open a `private-tools` pull request containing the utility and its tests.
6. STOP before using the utility for any cross-repository rewrite.
7. Ask Kevin to merge that prerequisite utility pull request.
8. After Kevin merges it: fast-forward `~/private-tools` main, verify the utility is present and tracked on main, rerun its tests from main, then continue with A6 in this same ticket.

## A4 — the utility contract

`yt-rewrite-moved-issue-id.py OLD_ID NEW_ID FILE`. The utility must:

1. Operate on exactly one explicitly named file.
2. Never recursively search or discover files.
3. Accept only a regular `.md` file.
4. Refuse symlinks and non-regular files, rather than replacing a symlink itself.
5. Validate both issue IDs with the readable-ID rule the move tooling uses: `^[A-Z][A-Z0-9_]*-[1-9][0-9]*$`.
6. Refuse when OLD_ID equals NEW_ID.
7. Escape OLD_ID before building the regex.
8. Use exactly this boundary contract: `(?<![A-Za-z0-9-])OLD_ID(?![0-9])`.
9. Never use unrestricted `str.replace()`.
10. Refuse, leaving the file unmodified, when there are zero boundary-aware matches.
11. Calculate and report the exact number of substitutions.
12. Preserve every byte other than the approved substitutions: no line-ending normalisation, no Markdown reformatting. The IDs and the boundary alphabet are ASCII, so work on bytes (a `bytes` regex) rather than decoding and re-encoding.
13. Preserve the file's permission mode.
14. Write safely, in exactly this order:
    1. Read the original bytes.
    2. Compute the expected output entirely in memory.
    3. Create a temporary file in the same directory.
    4. Write the complete expected bytes to it.
    5. Flush and `fsync` the temporary file.
    6. Re-read the temporary file and verify it equals the expected bytes.
    7. Give the temporary file the original's permission mode.
    8. Only then atomically replace the original (`os.replace`).
    9. Re-read the final pathname and verify it equals the expected bytes.
    10. On any failure, remove the temporary file if it still exists.
15. A failure at any step before the replacement leaves the original untouched, byte for byte. The utility keeps no backup, so a failure detected after the replacement (step 9) is reported with a non-zero exit, but it does not restore the old content.
16. Exit non-zero on a validation, read, write or verification failure.
17. Verify both the temporary file before the replacement and the final file after it (steps 6 and 9), each against the exact expected regex-substitution result.
18. Print a concise result naming the file and the replacement count; never print unrelated file contents.

## A5 — required tests for the utility

Temporary fixtures only: the tests never search the real home directory and never touch real repository files. At least:

- Replaced: `KTA-19`, `(KTA-19)`, `KTA-19.`, `KTA-19,`, `https://youtrack.kevininscoe.com/issue/KTA-19`.
- Not replaced: `KTA-190`, `KTA-191`, `XKTA-19`, `ABC-KTA-19`.
- Several approved matches in one file, with the correct count reported.
- Zero matches: refused, file unchanged.
- An invalid old ID; an invalid new ID; identical old and new IDs.
- A non-`.md` file, a directory, and a symlink: each refused.
- Permission mode preserved.
- CRLF input stays CRLF, and a file with no final newline keeps none.
- A failed atomic write leaves the original intact and no temporary file behind.
- A simulated pre-replacement verification failure (step 6 reads back different bytes) leaves the original byte-for-byte unchanged, exits non-zero, and leaves no temporary file.
- A second invocation after a successful rewrite refuses, because no OLD_ID matches remain, rather than silently succeeding.

## A6 — rewriting the Markdown files

Only once A3 has established a tested utility on `private-tools` main:

1. Read the human-generated inventory and parse its `path:line:text` lines.
2. Deduplicate the Markdown file paths. Use only paths explicitly present in the inventory.
3. Attach the original inventory to this issue through the YouTrack API (`POST /api/issues/<this issue>/attachments`, multipart `upload=@<file>`), as retained evidence.
4. **Required:** before changing a Markdown hit that looks like a branch name, worktree path, commit subject, command, filename or other literal historical artifact, show it to Kevin rather than rewriting it, and let him decide. Those names still exist under {old}; rewriting them blindly repeats the damage Part B exists to repair.
5. **Map each approved inventory path to its worktree copy.** The inventory path is the authority for *which* file may change; the corresponding worktree path is *where* it is changed. **Never modify the original inventory pathname in the main checkout**, even though that exact path appears in the inventory. For each approved path:
   1. Determine whether it belongs to a Git repository (`git -C <its directory> rev-parse --show-toplevel`).
   2. Confirm that checkout is the repository's normal (main) working tree, not an `ai-wt/` or other linked worktree: its top level must equal the parent of `git rev-parse --path-format=absolute --git-common-dir`.
   3. Derive the path relative to the repository root. It must be relative and contain no `..` component.
   4. Confirm that relative path is tracked by Git on the base the POE worktree is made from (`git -C <repo-root> ls-tree --name-only <base> -- <relative path>` prints it).
   5. Create or use this POE ticket's worktree for that repository, per the normal directives (`<repo-root>/ai-wt/<this issue>`).
   6. Build the candidate target inside the POE worktree from that same relative path, preserving nested directories exactly.
   7. Check containment both ways. **Both lexical and resolved containment are required. A symlinked directory must not allow the rewrite target to escape the POE worktree.**
      - Lexical: the normalised candidate path lies beneath the worktree root.
      - Resolved: resolve the worktree root canonically (`Path.resolve()` / `realpath`) and resolve the existing target canonically (`Path.resolve(strict=True)`). The resolved target must lie beneath the resolved root, tested path-aware (`Path.is_relative_to`, or `os.path.commonpath`), never by string-prefix comparison. Reject a target that escapes through any symlinked component.
      - The target itself must be a regular file and not a symlink (`os.lstat`).
      No file outside the worktree may be substituted as a target.
   8. Only then run `{UTILITY_NAME}` against the **worktree copy**, with `{old}` and `{new}`.
   9. Review the worktree diff.
   10. Commit, push and open that repository's pull request, per the normal directives.

   Example: the inventory reports `~/Projects/private/host-frodo-config/README.md`. The repository root is `~/Projects/private/host-frodo-config`, the POE worktree is `~/Projects/private/host-frodo-config/ai-wt/<this issue>`, and the relative path is `README.md`. So the rewrite target is `~/Projects/private/host-frodo-config/ai-wt/<this issue>/README.md`.

   **Unmanaged or unmappable approved paths fail closed.** If an approved inventory path is outside any Git repository, is untracked, belongs to another worktree rather than the normal checkout, or otherwise has no corresponding tracked file in the new POE worktree, STOP for that file. Report it to Kevin as an unmanaged/unmappable approved path and ask how it should be handled: separately, added to a repository, or left unchanged. Never fall back to editing the original inventory pathname, and never silently drop it from the approved set.
6. Skip the move evidence files listed above and the inventory itself, and say that you did.
7. Review each resulting diff file by file, using explicit-file commands only (`git diff -- <file>` in the worktree, or `diff` against a copy). Never use recursive `rg` to verify.
8. Keep repository boundaries: each repository gets its own worktree, branch and pull request under this issue, as the normal directives require.
"""
    part_b = ""
    if _remediation_needed(report):
        arts = report["artifact_rewrites"]
        shown = arts[:max_locations]
        loc_lines = "\n".join(
            f"- {a['issue']} {a['where']} ({a['reason']}): was `…{a['before'].replace('`', '')}…`"
            for a in shown) or "- (none)"
        more = (f"\n- … and {len(arts) - len(shown)} more; the full list is in the comparison report."
                if len(arts) > len(shown) else "")
        uncl = "\n".join(f"- {u['idReadable']}" for u in report["unclassified_other_issues"])
        uncl_block = (f"\nIssues that mention {new} but were not in the pre-move evidence, "
                      f"so their text could not be classified:\n{uncl}\n") if uncl else ""
        unver = "\n".join(f"- {u['issue']} {u['where']}: {u['reason']}"
                           for u in report.get("unverifiable_other_issues", []))
        if unver:
            uncl_block += (f"\nCould not be re-checked after the move (captured in the pre-move "
                           f"evidence, unreadable afterwards). Check these by hand against "
                           f"`{EVIDENCE_DIR}/{old}-before-project-move.api.json`:\n{unver}\n")
        part_b = f"""
# Part B — historical text YouTrack rewrote

On the move YouTrack replaced the bare token {old} with {new} in issue text. For issue references that is correct. For literal names of real objects (branches, `ai-wt/` worktree paths, commit subjects, commands, filenames, quoted logs) it is not: those still exist under {old}. The comparison classified {len(arts)} rewrite(s) as historical artifacts. The classification is deliberately conservative: a false positive costs one human check, while a missed one would leave a real branch, path or commit name wrong. Confirm each one against the pre-move evidence.

Locations (issue, place, reason, pre-move text):
{loc_lines}{more}
{uncl_block}
## B1 — what the agent working this ticket does

1. Attach the comparison report and the pre-move snapshot (`{EVIDENCE_DIR}/{old}-before-project-move.api.json`) to this issue as retained evidence.
2. For each location, read the pre-move text from the snapshot and the current text from the API. Restore {old} **only** where the occurrence is a verified literal historical artifact. Keep genuine issue references as {new}.
3. **Never mass-replace {new} back to {old}**, in a comment or anywhere else. That would revert legitimate references.
4. Show Kevin the proposed restorations, location by location, and get his approval before writing anything.
5. Write through the API: a comment with `POST /api/issues/<issue>/comments/<commentId>` and `{{"text": ...}}`, a description with `POST /api/issues/<issue>` and `{{"description": ...}}`. Comments authored by someone else may be refused for `Claude_Code`; list those for Kevin instead.
6. Re-read each edited text and confirm that only the intended tokens changed.
"""
    return head + part_a + part_b


def forge_url(remote):
    """Browser URL of a git remote on k-fed's forges; None when unrecognised."""
    m = (re.match(r"^ssh://git@git\.kevininscoe\.com(?::\d+)?/(.+?)(?:\.git)?$", remote)
         or re.match(r"^git@github\.com:(.+?)(?:\.git)?$", remote)
         or re.match(r"^https://(?:git\.kevininscoe\.com|github\.com)/(.+?)(?:\.git)?$", remote))
    if not m:
        return None
    host = "github.com" if "github.com" in remote else "git.kevininscoe.com"
    return f"https://{host}/{m.group(1)}"


def followup_repo_url():
    """Forge URL of FOLLOWUP_REPO, read from its origin. Refuses rather than guesses."""
    path = os.path.expanduser(FOLLOWUP_REPO)
    proc = subprocess.run(["git", "-C", path, "remote", "get-url", "origin"],
                          capture_output=True, text=True)
    url = forge_url(proc.stdout.strip()) if proc.returncode == 0 else None
    if not url:
        raise Fail(f"cannot derive the forge URL of {FOLLOWUP_REPO} from its origin "
                   f"({proc.stdout.strip() or proc.stderr.strip()!r}); not inventing one")
    return url


def followup_read_back_problems(check, repo_url, evidence=()):
    """Compare a read-back follow-up issue with what create_followup() set.

    Returns (wrong, expect): wrong maps each mismatching prototype (or
    "Repository comment", or "Evidence paths") to the value read back; empty
    means it matches. evidence is the full paths the description must carry.
    """
    got = {}
    for f in check["customFields"]:
        v = f.get("value")
        # A user value carries both login and display name ("Claude_Code" /
        # "Claude Code"); compare logins. Enum and state values carry only a name.
        # Reading name first made POE-27's correct Assignee read back as wrong.
        if isinstance(v, dict):
            v = v["login"] if v.get("login") else v.get("name")
        got[f["projectCustomField"]["field"]["id"]] = v
    expect = {PROTO_STATUS: "Not yet started", PROTO_PRIORITY: "Normal", PROTO_TYPE: "Task",
              PROTO_ASSIGNEE: FOLLOWUP_ASSIGNEE, PROTO_REPO_URL: repo_url}
    wrong = {p: got.get(p) for p, v in expect.items() if got.get(p) != v}
    if not isinstance(got.get(PROTO_DATE_ENTERED), int):
        wrong[PROTO_DATE_ENTERED] = got.get(PROTO_DATE_ENTERED)
    if not any(c.get("text") == f"Repository: {FOLLOWUP_REPO}" for c in check.get("comments") or []):
        wrong["Repository comment"] = None
    absent = [p for p in evidence if p not in (check.get("description") or "")]
    if absent:
        wrong["Evidence paths"] = absent
    return wrong, expect


def create_followup(old, new, report=None, report_path=None):
    repo_url = followup_repo_url()
    # The ticket names every evidence file by full path; refuse, before any API
    # call, to point it at evidence that is not actually there.
    missing = missing_evidence(old, new)
    if missing:
        raise Fail("evidence missing or empty, so the follow-up was not filed: "
                   + ", ".join(missing))
    project = resolve_project(FOLLOWUP_PROJECT)
    sample = api("GET", "/api/issues", {
        "query": f"project: {FOLLOWUP_PROJECT}", "$top": 1,
        "fields": "customFields(name,$type,projectCustomField(field(id)))"})
    if not sample:
        raise Fail(f"no issue in {FOLLOWUP_PROJECT} to read the field schema from")
    by_proto = {f["projectCustomField"]["field"]["id"]: f for f in sample[0]["customFields"]}
    wanted = {
        PROTO_STATUS: {"name": "Not yet started"},
        PROTO_PRIORITY: {"name": "Normal"},
        PROTO_TYPE: {"name": "Task"},
        PROTO_ASSIGNEE: {"login": FOLLOWUP_ASSIGNEE},
        PROTO_DATE_ENTERED: int(time.time() * 1000),
        PROTO_REPO_URL: repo_url,
    }
    fields = []
    for proto, value in wanted.items():
        if proto not in by_proto:
            raise Fail(f"{FOLLOWUP_PROJECT} has no field with prototype {proto}")
        f = by_proto[proto]
        fields.append({"name": f["name"], "$type": f["$type"], "value": value})
    body = {"project": {"id": project["id"]},
            "summary": followup_summary(old, new, report),
            "description": followup_text(old, new, report, report_path),
            "customFields": fields}
    created = api("POST", "/api/issues", {"fields": "id,idReadable"}, body)
    api("POST", f"/api/issues/{created['id']}/comments", {"fields": "id"},
        {"text": f"Repository: {FOLLOWUP_REPO}"})

    # Read back: a write that reported success is only proven by the read.
    check = api("GET", f"/api/issues/{created['id']}", {"fields":
                "idReadable,description,customFields(name,projectCustomField(field(id)),value(name,login)),"
                "comments(text)"})
    evidence = [p for _, p in evidence_paths(old, new)]
    wrong, expect = followup_read_back_problems(check, repo_url, evidence)
    if wrong:
        raise Fail(f"{check['idReadable']} was created but reads back wrong: {wrong}")
    return {"idReadable": check["idReadable"], "id": created["id"],
            "url": f"{PUBLIC_URL}/issue/{check['idReadable']}",
            "remediation_section": _remediation_needed(report),
            "repo_url": repo_url, "verified": sorted(expect) + [PROTO_DATE_ENTERED],
            "evidence_paths": evidence}


# ---------------------------------------------------------------------- CLI

def _load(path):
    with open(os.path.expanduser(path), encoding="utf-8") as fh:
        return json.load(fh)


def print_risk(before):
    rows = risk(before, before["idReadable"])
    likely = [r for r in rows if r["likely_rewritten"]]
    arts = [r for r in likely if r["kind"] == "artifact"]
    others = {r["issue"] for r in rows} - {before["idReadable"]}
    for r in arts[:25]:
        print(f"likely artifact: {r['issue']} {r['where']} ({r['reason']}): …{r['text']}…")
    if len(arts) > 25:
        print(f"… and {len(arts) - 25} more likely artifacts")
    scan = before.get("_scan")
    print(f"Occurrences of {before['idReadable']} in issue text: {len(rows)} "
          f"(this issue and {len(others)} other issue(s))")
    print(f"Likely rewritten by YouTrack: {len(likely)} "
          f"({len(likely) - len(arts)} references, {len(arts)} literal historical artifacts)")
    print(f"Likely left as written (URLs, inline code, suffixed tokens, fields): "
          f"{len(rows) - len(likely)}")
    print("Cross-issue scan: " + (f"{SCAN_CLAIM} ({scan['hits']} search hits); issues in "
          "projects Claude_Code cannot see were not scanned" if scan else "not run"))
    print(f"WARNING: {WARNING}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-id").add_argument("issue")
    p = sub.add_parser("check-export")
    p.add_argument("file"); p.add_argument("issue")
    p.add_argument("--project-name")
    sub.add_parser("risk").add_argument("before")
    p = sub.add_parser("compare")
    p.add_argument("before"); p.add_argument("after")
    p.add_argument("--json", help="also write the full report here")
    p = sub.add_parser("followup-text")
    p.add_argument("old"); p.add_argument("new"); p.add_argument("--report")
    sub.add_parser("resolve-issue").add_argument("issue")
    p = sub.add_parser("resolve-project")
    p.add_argument("project")
    p.add_argument("--for-issue", help="also refuse if this issue may not move there")
    p = sub.add_parser("snapshot")
    p.add_argument("issue"); p.add_argument("out")
    p.add_argument("--scan", help="record other issues whose text mentions this ID")
    p.add_argument("--references-from", help="re-read the issues this snapshot found")
    p = sub.add_parser("move")
    p.add_argument("entity_id"); p.add_argument("project_id")
    p = sub.add_parser("create-followup")
    p.add_argument("old"); p.add_argument("new"); p.add_argument("--report")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "check-id":
            print(normalise_issue_id(args.issue))
        elif args.cmd == "check-export":
            issue = normalise_issue_id(args.issue)
            problems = check_export(args.file, issue, args.project_name)
            for prob in problems:
                print(f"FAIL: {prob}")
            if problems:
                return 1
            print(f"OK: {os.path.expanduser(args.file)} is a yt-export of {issue}")
        elif args.cmd == "risk":
            print_risk(_load(args.before))
        elif args.cmd == "compare":
            rep = compare(_load(args.before), _load(args.after))
            print(render(rep))
            if args.json:
                with open(os.path.expanduser(args.json), "w", encoding="utf-8") as fh:
                    json.dump(rep, fh, indent=2)
            return verdicts(rep)[2]
        elif args.cmd == "followup-text":
            old, new = normalise_issue_id(args.old), normalise_issue_id(args.new)
            report = _load(args.report) if args.report else None
            print(followup_summary(old, new, report)); print()
            print(followup_text(old, new, report, args.report))
        elif args.cmd == "resolve-issue":
            print(json.dumps(resolve_issue(issue_ref(args.issue)), indent=2))
        elif args.cmd == "resolve-project":
            project = resolve_project(args.project)
            print(json.dumps(project, indent=2))
            if args.for_issue:
                refuse_destination(resolve_issue(issue_ref(args.for_issue)), project)
                print(f"OK: {args.for_issue} may move to {project['shortName']} ({project['id']})")
        elif args.cmd == "snapshot":
            scan = normalise_issue_id(args.scan) if args.scan else None
            data = snapshot(issue_ref(args.issue), scan, args.references_from)
            out = os.path.expanduser(args.out)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
            print(f"Wrote {out} ({data['idReadable']}, entity {data['id']}, "
                  f"{len(data['comments'])} comments, {len(data['attachments'])} attachments, "
                  f"{len(data.get('referencing_issues', []))} referencing issues)")
        elif args.cmd == "move":
            print(json.dumps(move(args.entity_id, args.project_id), indent=2))
        elif args.cmd == "create-followup":
            old, new = normalise_issue_id(args.old), normalise_issue_id(args.new)
            report = _load(args.report) if args.report else None
            print(json.dumps(create_followup(old, new, report, args.report), indent=2))
    except Fail as exc:
        sys.stdout.flush()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
