#!/usr/bin/env python3
"""Collect and parse every CHECKPOINT.md reported by `check-git-repos --checkpoint`.

Extracts the facts a resuming agent needs — which YouTrack issue the checkpoint tracks,
which directory to work from, whether the issue's worktree still exists, how far the task
list got, and what is blocking it — and emits them as JSON (default) or a plain-text
summary.

This script only reads. It never writes to a CHECKPOINT.md; those belong to other
sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

# `check-git-repos --checkpoint` prints one line per repo: "<path> is CHECKPOINT",
# where <path> is written in ~/ form for anything under $HOME.
REPO_LINE = re.compile(r"^(?P<path>.+?)\s+is\s+CHECKPOINT\s*$")

# A YouTrack issue key: uppercase project short name, hyphen, number. The project roster
# changes without this script being told, so the shape is matched rather than a fixed list.
ISSUE_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,15}-\d+)\b")
ISSUE_URL = re.compile(r"https?://[^\s)]*?/issue/([A-Z][A-Z0-9]{1,15}-\d+)")

# Forge pull request URLs — GitHub uses /pull/<n>, Gitea uses /pulls/<n>.
PR_URL = re.compile(r"https?://[^\s)\]]+/pulls?/\d+")

TASK_DONE = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(.*)$")
TASK_OPEN = re.compile(r"^\s*[-*]\s*\[\s\]\s*(.*)$")

# Words that mean "this is not simply waiting its turn".
BLOCKER_WORDS = re.compile(
    r"\b(blocked|blocking|awaiting|await|halted|paused|stopped|interrupted|"
    r"deadlock|collision|do not|must not)\b",
    re.IGNORECASE,
)

# Tokens that look like issue keys but are not. CVE and GHSA identifiers appear in
# security checkpoints and would otherwise be reported as tracking issues.
NOT_AN_ISSUE = re.compile(r"^(CVE|GHSA|RFC|ISO|UTC|HTTP|HTTPS|SHA|MD|TLS|SSL|API)-", re.IGNORECASE)


def tilde(path: Path | str) -> str:
    """Render a path in ~/ form when it is under $HOME — how Kevin refers to paths."""
    text = str(path)
    home = str(HOME)
    if text == home:
        return "~"
    if text.startswith(home + os.sep):
        return "~/" + text[len(home) + 1:]
    return text


def run_collector(command: str) -> list[str]:
    """Run `check-git-repos --checkpoint` and return the repository paths it reports.

    Silence is a real answer: the command prints nothing when no checkpoint exists
    anywhere, which means no unfinished AI work is outstanding.
    """
    binary = command.split()[0]
    if shutil.which(binary) is None:
        sys.exit(f"error: {binary} not found on PATH")
    proc = subprocess.run(command.split(), capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"error: {command} exited {proc.returncode}: {proc.stderr.strip()}")

    repos: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        match = REPO_LINE.match(line)
        if match:
            repos.append(match.group("path").strip())
    return repos


def find_checkpoints(repo: str) -> list[Path]:
    """Find every CHECKPOINT.md in a repository.

    Searched in full rather than at the root only: in a tracking repository (~/admin,
    /opt/containers) a project's CHECKPOINT.md belongs in that project's own
    subdirectory. `ai-wt/` worktrees are skipped — a checkpoint never belongs in one,
    and anything found there would be a duplicate of the primary tree's copy.
    """
    root = Path(os.path.expanduser(repo))
    if not root.is_dir():
        return []
    found: list[Path] = []
    for path in root.rglob("CHECKPOINT.md"):
        parts = set(path.parts)
        if ".git" in parts or "ai-wt" in parts or "node_modules" in parts:
            continue
        found.append(path)
    return sorted(found)


def primary_working_tree(path: Path) -> Path | None:
    """Return the repository's primary working tree, or None if path is not in a repo.

    `git rev-parse --show-toplevel` is deliberately not used: inside an ai-wt/<ISSUE-ID>
    worktree it returns the worktree, not the repository.
    """
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).parent


def list_worktrees(repo_root: Path) -> list[dict]:
    """Return the repository's worktrees as {path, branch} dicts."""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return []
    trees: list[dict] = []
    current: dict = {}
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                trees.append(current)
            current = {"path": line[len("worktree "):], "branch": None}
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].removeprefix("refs/heads/")
    if current:
        trees.append(current)
    return trees


def extract_issues(text: str, title: str) -> dict:
    """Work out which YouTrack issues a checkpoint names, and which one it is *for*.

    The H1 title is the strongest signal — every checkpoint on this host opens with
    "# CHECKPOINT — <ISSUE>: <what>". A YouTrack issue URL in the Summary is the next
    strongest. Bare keys elsewhere in the body are recorded as mentioned, because a
    checkpoint routinely names other sessions' issues to explain a collision.
    """
    def clean(keys) -> list[str]:
        return [k for k in dict.fromkeys(keys) if not NOT_AN_ISSUE.match(k)]

    in_title = clean(ISSUE_KEY.findall(title))
    urls = clean(ISSUE_URL.findall(text))
    body = clean(ISSUE_KEY.findall(text))

    if in_title:
        primary = in_title
    elif urls:
        primary = urls[:1]
    else:
        primary = body[:1]

    mentioned = [k for k in body if k not in primary]
    return {"primary": primary, "mentioned": mentioned, "urls": urls}


def extract_summary(lines: list[str]) -> str:
    """Return the ## Summary section — written to be read cold by another agent."""
    out: list[str] = []
    capturing = False
    for line in lines:
        if re.match(r"^##\s+Summary\s*$", line, re.IGNORECASE):
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def extract_timestamps(lines: list[str]) -> dict:
    """Pull the Started / Paused / Interrupted / Halted markers from the header."""
    stamps: dict[str, str] = {}
    for line in lines[:40]:
        match = re.match(
            r"^\**\s*(Started|Paused|Interrupted|Halted|Written|Resumed)\b\**\s*:?\s*(.+)$",
            line.strip().lstrip("*").strip(),
            re.IGNORECASE,
        )
        if match:
            stamps.setdefault(match.group(1).lower(), match.group(2).strip(" *"))
    return stamps


def parse_checkpoint(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), path.name)

    done = [m.group(1).strip() for ln in lines if (m := TASK_DONE.match(ln))]
    open_tasks = [m.group(1).strip() for ln in lines if (m := TASK_OPEN.match(ln))]

    blockers = [
        ln.strip()
        for ln in lines
        if BLOCKER_WORDS.search(ln) and (TASK_OPEN.match(ln) or "**" in ln or ln.startswith("#"))
    ]

    checkpoint_dir = path.parent
    repo_root = primary_working_tree(checkpoint_dir)
    issues = extract_issues(text, title)

    worktrees = list_worktrees(repo_root) if repo_root else []
    matched: list[dict] = []
    for key in issues["primary"] + issues["mentioned"]:
        for tree in worktrees:
            name = Path(tree["path"]).name
            if name == key or tree["branch"] == key or name.startswith(f"{key}-"):
                matched.append({"issue": key, "path": tilde(tree["path"]), "branch": tree["branch"]})

    return {
        "checkpoint": tilde(path),
        "checkpoint_dir": tilde(checkpoint_dir),
        "repo_root": tilde(repo_root) if repo_root else None,
        "in_git_repo": repo_root is not None,
        "title": title,
        "issues": issues,
        "timestamps": extract_timestamps(lines),
        "summary": extract_summary(lines),
        "tasks": {
            "done": len(done),
            "open": len(open_tasks),
            "total": len(done) + len(open_tasks),
            "next_open": open_tasks[0] if open_tasks else None,
            "open_list": open_tasks,
        },
        "blocker_lines": blockers,
        "pull_requests": list(dict.fromkeys(PR_URL.findall(text))),
        "worktrees": matched,
        "all_worktrees": [
            {"path": tilde(t["path"]), "branch": t["branch"]}
            for t in worktrees
            if Path(t["path"]) != repo_root
        ],
    }


def render_text(records: list[dict]) -> str:
    if not records:
        return "No CHECKPOINT.md found — no unfinished AI work is outstanding."

    out: list[str] = []
    for rec in records:
        issues = rec["issues"]["primary"] or ["(none found)"]
        out.append(f"{rec['checkpoint_dir']}")
        out.append(f"  issue    : {', '.join(issues)}")
        out.append(f"  resume in: {rec['checkpoint_dir']}")
        for tree in rec["worktrees"]:
            out.append(f"  worktree : {tree['path']} (branch {tree['branch']})")
        tasks = rec["tasks"]
        out.append(f"  tasks    : {tasks['done']}/{tasks['total']} done")
        if tasks["next_open"]:
            out.append(f"  next     : {tasks['next_open'][:100]}")
        for url in rec["pull_requests"]:
            out.append(f"  PR       : {url}")
        out.append("")
    return "\n".join(out).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="output format (default: json)")
    parser.add_argument("--command", default="check-git-repos --checkpoint",
                        help="collector command to run (default: check-git-repos --checkpoint)")
    parser.add_argument("--path", action="append", default=[],
                        help="parse this CHECKPOINT.md or repository instead of running the "
                             "collector; repeatable")
    args = parser.parse_args()

    if args.path:
        repos = args.path
    else:
        repos = run_collector(args.command)

    records: list[dict] = []
    seen: set[Path] = set()
    for repo in repos:
        target = Path(os.path.expanduser(repo))
        candidates = [target] if target.is_file() else find_checkpoints(repo)
        for checkpoint in candidates:
            resolved = checkpoint.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            records.append(parse_checkpoint(checkpoint))

    if args.format == "json":
        print(json.dumps({"count": len(records), "checkpoints": records}, indent=2))
    else:
        print(render_text(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
