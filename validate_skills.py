#!/usr/bin/env python3
"""Read-only compliance check for the skills this repo owns (AI-93).

An owned skill is a real top-level directory of the repo: not a symlink, not
gitignored, and not one of the non-skill directories below. Each one must have:

  - SKILL.md and an executable run.sh
  - YAML frontmatter with name:, category:, description: and
    disable-model-invocation: true
  - name: equal to the directory name; category: a lowercase hyphenated slug
    that prefixes the directory name
  - an H1 title, then a one-sentence > blockquote
  - ## Prerequisites, ## Instructions and ## Success Criteria, with
    ## Parameters and ## Notes optional, in template.md's relative order

Additional sections are allowed anywhere. Headings inside fenced code blocks
do not count.

Symlinked skills (the vanco-skills bridges) are owned by another repository and
are excluded from the owned-skill compliance checks: they are reported in their
own section and never fail the run. Where a link resolves, the report still
reads through it, to say which of SKILL.md and run.sh are present and whether
the SKILL.md frontmatter sets disable-model-invocation; that is informational
only. A link that does not resolve is reported as host-specific: the committed
relative links resolve only when this repo is checked out at ~/.claude/skills.

The script only reads. It runs no skill, changes no setting and writes no file.

Usage:
  python3 validate_skills.py [--root DIR]

Exit status: 0 when every owned skill complies, 1 when any does not, 2 on a
usage error.
"""

import argparse
import os
import re
import subprocess
import sys

# Top-level directories that are part of the repo but are not skills.
NON_SKILL_DIRS = {"synced", "ai-wt"}
REQUIRED_KEYS = ("name", "category", "description")
SECTION_ORDER = ["Prerequisites", "Parameters", "Instructions", "Success Criteria", "Notes"]
REQUIRED_SECTIONS = {"Prerequisites", "Instructions", "Success Criteria"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def gitignored(root, names):
    """Return the subset of names git ignores under root; empty outside git."""
    if not names:
        return set()
    try:
        out = subprocess.run(["git", "-C", root, "check-ignore", "--stdin"],
                             input="\n".join(names), capture_output=True, text=True)
    except OSError:
        return set()
    if out.returncode not in (0, 1):  # 128: not a git repository
        return set()
    return {line.strip().rstrip("/") for line in out.stdout.splitlines() if line.strip()}


def classify(root):
    """Split top-level entries into (owned skill dirs, linked skill names)."""
    candidates = []
    for name in sorted(os.listdir(root)):
        if name.startswith(".") or name.startswith("gsd-") or name in NON_SKILL_DIRS:
            continue
        path = os.path.join(root, name)
        if os.path.islink(path) or os.path.isdir(path):
            candidates.append(name)
    ignored = gitignored(root, candidates)
    owned, linked = [], []
    for name in candidates:
        if name in ignored:
            continue
        (linked if os.path.islink(os.path.join(root, name)) else owned).append(name)
    return owned, linked


def parse_frontmatter(text):
    """Return (dict of top-level keys, body after the closing ---) or (None, text)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        return None, text
    fm, key = {}, None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, "\n".join(lines[end + 1:])


def outside_fences(body):
    """Yield the lines of body that are not inside a fenced code block."""
    fence = None
    for line in body.split("\n"):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            yield line
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and not line.strip()[len(m.group(1)):].strip():
            fence = None


def check_skill(root, name):
    """Return the list of compliance problems for one owned skill directory."""
    d = os.path.join(root, name)
    problems = []
    skill_md = os.path.join(d, "SKILL.md")
    run_sh = os.path.join(d, "run.sh")
    if not os.path.isfile(run_sh):
        problems.append("missing run.sh")
    elif not os.access(run_sh, os.X_OK):
        problems.append("run.sh is not executable")
    if not os.path.isfile(skill_md):
        problems.append("missing SKILL.md")
        return problems

    with open(skill_md, encoding="utf-8") as fh:
        fm, body = parse_frontmatter(fh.read())
    if fm is None:
        problems.append("no YAML frontmatter")
        fm = {}
    else:
        for key in REQUIRED_KEYS:
            if not fm.get(key):
                problems.append(f"frontmatter: missing {key}:")
        if fm.get("disable-model-invocation") != "true":
            problems.append("frontmatter: disable-model-invocation: true is missing")
        if fm.get("name") and fm["name"] != name:
            problems.append(f"frontmatter: name: {fm['name']!r} does not equal the directory name")
        cat = fm.get("category")
        if cat:
            if not SLUG.match(cat):
                problems.append(f"frontmatter: category: {cat!r} is not a lowercase hyphenated slug")
            elif not name.startswith(cat + "-"):
                problems.append(f"frontmatter: category: {cat!r} is not the directory-name prefix")

    lines = [l for l in outside_fences(body)]
    content = [l for l in lines if l.strip()]
    if not content or not re.match(r"^# \S", content[0]):
        problems.append("the first line after the frontmatter is not an H1 title")
    elif len(content) < 2 or not content[1].startswith(">"):
        problems.append("no > blockquote description after the H1")

    found = [l[3:].strip() for l in lines if l.startswith("## ")]
    for section in SECTION_ORDER:
        if section in REQUIRED_SECTIONS and section not in found:
            problems.append(f"missing ## {section}")
    known = [s for s in found if s in SECTION_ORDER]
    for section in set(known):
        if known.count(section) > 1:
            problems.append(f"## {section} appears {known.count(section)} times")
    firsts = [s for i, s in enumerate(known) if s not in known[:i]]
    if firsts != sorted(firsts, key=SECTION_ORDER.index):
        problems.append("required sections out of order: " + " → ".join(firsts))
    return problems


def describe_link(root, name):
    """One line about a symlinked skill; never a failure."""
    path = os.path.join(root, name)
    target = os.readlink(path)
    if not os.path.exists(path):
        return f"{name} -> {target}: does not resolve here (host-specific; see RUNBOOK.md)"
    has = [f for f in ("SKILL.md", "run.sh") if os.path.isfile(os.path.join(path, f))]
    line = f"{name} -> {target}: resolves; has {', '.join(has) or 'neither SKILL.md nor run.sh'}"
    if "SKILL.md" in has:
        with open(os.path.join(path, "SKILL.md"), encoding="utf-8") as fh:
            fm, _ = parse_frontmatter(fh.read())
        if (fm or {}).get("disable-model-invocation") != "true":
            line += "; no frontmatter flag (sync-skill-overrides.sh covers it per host)"
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only compliance check for owned skills.")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)),
                    help="repository root to check (default: this script's directory)")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    owned, linked = classify(root)
    failures = 0
    print(f"Owned skills ({len(owned)}):")
    for name in owned:
        problems = check_skill(root, name)
        if problems:
            failures += 1
            print(f"  FAIL {name}")
            for p in problems:
                print(f"       - {p}")
        else:
            print(f"  ok   {name}")
    print(f"\nLinked skills ({len(linked)}), owned by another repository and not checked:")
    for name in linked:
        print(f"  link {describe_link(root, name)}")
    print(f"\n{len(owned) - failures} of {len(owned)} owned skills comply.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
