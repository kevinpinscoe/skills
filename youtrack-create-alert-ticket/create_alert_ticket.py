#!/usr/bin/env python3
"""Create a YouTrack alert-response ticket.

Prompts for a pasted alert (or block of alerts), lets Kevin pick the target
project from the live project list, then files an issue with:
  - Type = Problem              (157-1)
  - Status = To do              (157-2)
  - Assignee = Claude_Code      (157-3)
  - Date time entered = now     (157-15)
  - Description = "Resolve and prevent re-occurence of alert(s): " followed
    by the pasted alert text

Filing only -- Status is left at "To do", never moved to "In Progress". Per
~/ai/directives/when-creating-a-youtrack-ticket.md SS11, filing an issue is
not working it: no worktree, no CHECKPOINT.md, no tab rename, no one-ticket
lock check.

Required env vars:
  YOUTRACK_TOKEN    - YouTrack API token for the Claude_Code account
  YOUTRACK_BASE_URL - Base URL (default: https://youtrack.kevininscoe.com)
"""

import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAGE_SIZE = 100
PROJECT_FIELDS = "id,shortName,name,archived"
DESCRIPTION_PREFIX = "Resolve and prevent re-occurence of alert(s): "
ASSIGNEE_LOGIN = "Claude_Code"
TERMINATOR = "END"

PROTOTYPE_TYPE = "157-1"
PROTOTYPE_STATUS = "157-2"
PROTOTYPE_ASSIGNEE = "157-3"
PROTOTYPE_DATE_ENTERED = "157-15"

# Fallback field name/$type for each prototype, used only when a project has
# no existing issue to sample the live schema from (see
# resolve_project_fields). All four are stock fields YouTrack attaches to
# every project, so the name is safe to assume -- confirmed against
# reference/custom-fields.md's "Stock and pre-existing fields" table.
STOCK_FIELD_FALLBACK = {
    PROTOTYPE_TYPE: {"name": "Type", "type": "SingleEnumIssueCustomField"},
    PROTOTYPE_STATUS: {"name": "Status", "type": "StateIssueCustomField"},
    PROTOTYPE_ASSIGNEE: {"name": "Assignee", "type": "SingleUserIssueCustomField"},
    PROTOTYPE_DATE_ENTERED: {"name": "Date time entered", "type": "SimpleIssueCustomField"},
}


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def api_get(base_url, path, params, token):
    qs = urllib.parse.urlencode(params)
    url = f"{base_url.rstrip('/')}/{path}?{qs}"
    req = urllib.request.Request(url, headers=headers(token))
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        die(f"GET {url} -> {exc.code}: {body}")


def api_post(base_url, path, body, token):
    url = f"{base_url.rstrip('/')}/{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers(token), method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        if exc.code == 404:
            die(
                f"POST {url} -> 404: {body_text}\n"
                "Claude_Code may not be on this project's team yet -- ask Kevin to add it."
            )
        die(f"POST {url} -> {exc.code}: {body_text}")


def ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        die("input closed unexpectedly")


def read_alert_block():
    print("Paste the alert(s) below, as one block.")
    print(f"When finished, type a line containing only {TERMINATOR} and press Enter.\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == TERMINATOR:
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        die("no alert text was entered")
    return text


def iter_projects(base_url, token):
    skip = 0
    while True:
        page = api_get(base_url, "api/admin/projects", {
            "fields": PROJECT_FIELDS,
            "$top": str(PAGE_SIZE),
            "$skip": str(skip),
        }, token)
        if not page:
            break
        yield from page
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE


def choose_project(base_url, token):
    projects = sorted(iter_projects(base_url, token), key=lambda p: p.get("shortName", ""))
    if not projects:
        die("no projects found on the live instance")

    print(f"\n{len(projects)} project(s)\n")
    width = max(len(p.get("shortName") or "") for p in projects)
    for project in projects:
        short = project.get("shortName") or "?"
        name = html.unescape(project.get("name") or "")
        archived = "  [archived]" if project.get("archived") else ""
        print(f"  {short:<{width}}  {name}{archived}")

    while True:
        choice = ask("\nProject short name: ").strip()
        match = next(
            (p for p in projects if (p.get("shortName") or "").lower() == choice.lower()),
            None,
        )
        if not match:
            print(f"  No project with short name {choice!r}. Try again.")
            continue
        if match.get("archived"):
            print(f"  {match['shortName']} is archived -- pick an active project.")
            continue
        return match


def resolve_project_fields(base_url, token, project_short_name, prototype_ids):
    # GET /api/admin/projects/{id}/customFields silently returns [] for the
    # Claude_Code token -- 200 OK, no error, but a permissions truncation
    # rather than a real "no fields attached" answer (measured 2026-09-02).
    # Read the live schema off an existing issue instead, per
    # reference/custom-fields.md's "$type trap" section -- issue-level reads
    # work fine for a token that only has project-team access, not admin
    # access. Fall back to the known stock name/$type when the project has
    # no issue yet to sample.
    issues = api_get(base_url, "api/issues", {
        "query": f"project: {project_short_name}",
        "fields": "customFields(name,$type,projectCustomField(field(id)))",
        "$top": "1",
    }, token)

    by_proto = {}
    if issues:
        for cf in issues[0].get("customFields", []):
            proto_id = ((cf.get("projectCustomField") or {}).get("field") or {}).get("id")
            if proto_id:
                by_proto[proto_id] = {"name": cf.get("name"), "type": cf.get("$type")}

    resolved = {}
    missing = []
    for proto_id in prototype_ids:
        entry = by_proto.get(proto_id) or STOCK_FIELD_FALLBACK.get(proto_id)
        if not entry:
            missing.append(proto_id)
            continue
        resolved[proto_id] = entry

    if missing:
        die(
            "could not resolve required custom field(s) (prototype id): "
            f"{', '.join(missing)} on project {project_short_name!r}"
        )
    return resolved


def resolve_claude_code_id(base_url, token):
    users = api_get(base_url, "api/users", {
        "fields": "id,login,fullName",
        "$top": "1000",
    }, token)
    matches = [u for u in users if u.get("login") == ASSIGNEE_LOGIN]
    if not matches:
        die(f"YouTrack user {ASSIGNEE_LOGIN!r} not found")
    return matches[0]["id"]


def derive_summary(alert_text):
    first_line = next(
        (l.strip() for l in alert_text.splitlines() if l.strip()),
        alert_text.strip(),
    )
    summary = f"Alert(s): {first_line}"
    if len(summary) > 120:
        summary = summary[:117] + "..."
    return summary


def create_issue(base_url, token, project_id, summary, description, field_map, claude_code_id):
    now_ms = int(time.time() * 1000)
    type_f = field_map[PROTOTYPE_TYPE]
    status_f = field_map[PROTOTYPE_STATUS]
    assignee_f = field_map[PROTOTYPE_ASSIGNEE]
    entered_f = field_map[PROTOTYPE_DATE_ENTERED]

    body = {
        "project": {"id": project_id},
        "summary": summary,
        "description": description,
        "customFields": [
            {"name": type_f["name"], "$type": type_f["type"], "value": {"name": "Problem"}},
            {"name": status_f["name"], "$type": status_f["type"], "value": {"name": "To do"}},
            {"name": assignee_f["name"], "$type": assignee_f["type"],
             "value": {"id": claude_code_id, "$type": "User"}},
            {"name": entered_f["name"], "$type": entered_f["type"], "value": now_ms},
        ],
    }
    return api_post(base_url, "api/issues?fields=id,idReadable", body, token)


def main():
    token = os.environ.get("YOUTRACK_TOKEN")
    if not token:
        die("YOUTRACK_TOKEN is not set. Run via run.sh or export it manually.")
    base_url = os.environ.get("YOUTRACK_BASE_URL", "https://youtrack.kevininscoe.com")

    alert_text = read_alert_block()
    project = choose_project(base_url, token)

    print(f"\n>>> Resolving fields on {project['shortName']}...")
    field_map = resolve_project_fields(
        base_url, token, project["shortName"],
        [PROTOTYPE_TYPE, PROTOTYPE_STATUS, PROTOTYPE_ASSIGNEE, PROTOTYPE_DATE_ENTERED],
    )

    print(">>> Resolving Claude_Code user id...")
    claude_code_id = resolve_claude_code_id(base_url, token)

    summary = derive_summary(alert_text)
    description = f"{DESCRIPTION_PREFIX}\n\n{alert_text}"

    print(f">>> Creating issue in {project['shortName']}...")
    issue = create_issue(
        base_url, token, project["id"], summary, description, field_map, claude_code_id,
    )

    idr = issue.get("idReadable") or issue.get("id")
    url = f"{base_url.rstrip('/')}/issue/{idr}"
    print(f"CREATED: {idr} in {project['shortName']}")
    print(f"URL: {url}")


if __name__ == "__main__":
    main()
