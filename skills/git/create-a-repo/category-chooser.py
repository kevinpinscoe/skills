#!/usr/bin/env python3
"""Runtime category chooser for the create-a-repo skill (GitHub repos only).

Reads the live category list from the GitHub profile source of truth at
``~/Projects/public/kevinpinscoe/profile.yml`` every time it runs — the
categories are NOT baked into the skill. Each category maps to exactly one
controlled ``area-*`` GitHub topic.

Usage:
  category-chooser.py --list           List categories as "N<TAB>name<TAB>topic"
  category-chooser.py --resolve N       Print the area-* topic for selection N
  category-chooser.py                   Interactive prompt (for a human at a TTY)

The profile path may be overridden with the PROFILE_YML environment variable.
"""
import os
import sys

import yaml

DEFAULT_PROFILE = os.path.expanduser("~/Projects/public/kevinpinscoe/profile.yml")


def load_categories():
    path = os.environ.get("PROFILE_YML", DEFAULT_PROFILE)
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        sys.exit(f"error: profile not found: {path}")
    cats = (data or {}).get("categories") or []
    out = []
    for c in cats:
        name = (c or {}).get("name")
        topic = (c or {}).get("topic")
        if name and topic:
            out.append((name, topic))
    if not out:
        sys.exit(f"error: no categories with name+topic found in {path}")
    return out


def main(argv):
    cats = load_categories()

    if "--list" in argv:
        for i, (name, topic) in enumerate(cats, 1):
            print(f"{i}\t{name}\t{topic}")
        return 0

    if "--resolve" in argv:
        try:
            n = int(argv[argv.index("--resolve") + 1])
            name, topic = cats[n - 1]
        except (IndexError, ValueError):
            sys.exit("error: --resolve requires a valid selection number")
        print(topic)
        return 0

    # Interactive mode (human at a TTY).
    print("Select a category for this GitHub repo:\n")
    for i, (name, topic) in enumerate(cats, 1):
        print(f"  {i:2}. {name}  ({topic})")
    print()
    while True:
        try:
            raw = input(f"Enter a number [1-{len(cats)}]: ").strip()
        except EOFError:
            sys.exit("error: no selection provided")
        try:
            n = int(raw)
            name, topic = cats[n - 1]
        except (IndexError, ValueError):
            print("  invalid selection, try again")
            continue
        print(f"\nSelected: {name}\nTopic:    {topic}")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
