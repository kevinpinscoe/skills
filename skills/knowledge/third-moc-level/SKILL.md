---
name: third-moc-level
description: Creates a third-level Map of Content (MOC) file nested under a chosen second-level parent, with LCC classification in frontmatter, using an interactive Python chooser to select the parent.
---

# Create Third-Level MOC

> Creates a third-level Map of Content (MOC) in both knowledge vaults under a human-selected second-level parent MOC, with LCC classification in frontmatter, and links the new MOC into its parent.

## Prerequisites

- `~/KnowledgeVault/personal-knowledge-base/moc/` must contain at least one second-level MOC file (a file with a non-empty `primary_moc:` field)
- `~/Projects/private/personal-context-management-private/moc/` must exist
- Both vaults must have `templates/moc-note-template.md`
- Python 3 must be available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SUBJECT` | The topic this MOC will cover | _(required — ask the user)_ |
| `DISPLAY_TITLE` | Human-readable title as it should appear in the parent MOC and links | _(required — ask the user)_ |
| `PARENT_MOC` | The second-level MOC this MOC belongs under | _(required — selected via chooser)_ |
| `LCC_CODE` | LCC classification code (determined via lookup + human confirmation) | _(required — derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share the same structural conventions.

### MOC Hierarchy

MOCs (Maps of Content) are navigation hubs organized in levels:
- **First-level MOCs**: Broad topic maps (AI, Linux, Tools). `primary_moc:` is empty.
- **Second-level MOCs**: Sub-topic maps nested under a first-level parent. `primary_moc:` is set to the parent slug or title. Example: "AWS" under "Compute Cloud Hosting"; "Outdoor Lawn and Garden Maintenance" under "Tools".
- **Third-level MOCs**: Narrowly focused maps nested under a second-level parent. `primary_moc:` is set to the second-level parent slug or title.

Parent MOCs list their children in a `## Child MOCs`, `## Second-level MOCs`, or `## Third-level MOCs` section (detect what the parent already uses).

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/personal-knowledge-base/`

- `moc/` — all MOC files at all levels; use this directory for the parent chooser
- `lcc/` — LCC outline files (`lcco-a.md` through `lcco-z.md`) for classification lookup
- `home.md` — **do not modify** for third-level MOCs

Template: `templates/moc-note-template.md`
```yaml
---
title: "{{title}}"
aliases:
  - "moc {{title}}"
type: moc
classification:
classification_label:
classification_source: lcc
primary_moc:
related_mocs: []
tags: []
created: {{date}}
updated: {{date}}
---

# {{title}} MOC

## Overview

<!-- What does this map cover? -->

## Notes

- [[]]

## Related MOCs

- [[]]
```

### Vault 2 — Personal Context Management (private)
Path: `~/Projects/private/personal-context-management-private/`

- `moc/` — mirrors the KnowledgeVault; may have fewer files
- `lcc/` — empty; always use the KnowledgeVault's `lcc/` for lookups
- `home.md` — **do not modify** for third-level MOCs

Template: `templates/moc-note-template.md` (add classification fields even though they are absent from the template):
```yaml
---
title: "{{title}}"
type: moc
tags: []
created: {{date}}
updated: {{date}}
---
```

### Naming Rules (both vaults)

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Digital Ocean Droplets" → `digital-ocean-droplets.md`
- **Title, aliases, frontmatter labels**: may use normal capitalization and spaces
- **File must live in** `moc/`

## Instructions

1. **Ask for subject name** — Ask: "What is the subject of this third-level MOC?" Wait for their answer.

2. **Ask for display title** — Ask: "How should the title and link name appear in the parent MOC? (e.g. `[[digital-ocean-droplets|Digital Ocean Droplets]]`)" Wait for their answer.

3. **Run the parent MOC chooser** — Write and run this Python script to list all second-level MOCs from `~/KnowledgeVault/personal-knowledge-base/moc/`:

   ```python
   import os, re

   moc_dir = os.path.expanduser("~/KnowledgeVault/personal-knowledge-base/moc")
   results = []

   for fname in sorted(os.listdir(moc_dir)):
       if not fname.endswith(".md"):
           continue
       path = os.path.join(moc_dir, fname)
       with open(path) as f:
           content = f.read()
       if not content.startswith("---"):
           continue
       end = content.find("---", 3)
       if end == -1:
           continue
       fm = content[3:end]
       # Second-level MOCs have a non-empty primary_moc field
       primary = re.search(r'^primary_moc:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       if not primary or not primary.group(1) or not primary.group(1).strip():
           continue  # no parent — this is first-level, skip
       parent_val = primary.group(1).strip().strip('"')
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       results.append((fname[:-3], title, parent_val))

   for i, (slug, title, parent) in enumerate(results, 1):
       print(f"{i}. {title}  (parent: {parent}, file: {slug})")
   ```

   Present the numbered list output to the human and ask: "Which second-level MOC is the parent for this new MOC? Enter the number." Wait for their selection and record the parent's slug and title.

4. **Determine the filename slug** — Convert the subject name to a lowercase, hyphen-separated slug. Example: "Digital Ocean Droplets" → `digital-ocean-droplets`.

5. **Search the LCC catalog** — Read the relevant LCC outline file(s) in `~/KnowledgeVault/personal-knowledge-base/lcc/`. Files are named `lcco-a.md` through `lcco-z.md`. Common top-level classes:
   - Q: Science (QA = Mathematics/Computer Science, QH = Biology)
   - R: Medicine
   - S: Agriculture (SB = Plant culture)
   - T: Technology (TA = Engineering, TH = Building, TJ = Mechanical, TK = Electrical, TL = Motor Vehicles, TN = Mining, TP = Chemical, TR = Photography, TS = Manufactures, TT = Handicrafts, TX = Home Economics)
   - H: Social Sciences (HG = Finance)
   - B: Philosophy, Psychology, Religion

6. **Present candidates and confirm** — List 2–4 plausible LCC codes and labels. Call out ambiguity explicitly. Ask: "Which classification best matches your intent?" Wait for confirmation.

7. **Get today's date** — Run `date +%Y-%m-%d`.

8. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md`:
   - `title`: display title
   - `aliases`: `["moc <title lowercase>"]`
   - `type`: `moc`
   - `classification`: confirmed LCC code
   - `classification_label`: LCC class label
   - `classification_source`: `lcc`
   - `primary_moc`: parent slug (e.g. `compute-cloud-hosting`) — use the slug for machine-readability
   - `related_mocs`: list containing the parent's display title
   - `tags`: `["moc"]`
   - `created` / `updated`: today's date
   - Body: `# <title> MOC`, one-sentence Overview, `## Notes` with empty `[[]]`, `## Related MOCs` linking to parent

9. **Create the PCM MOC file** — Write `~/Projects/private/personal-context-management-private/moc/<slug>.md` with the same content. Add all classification fields explicitly:
   ```yaml
   ---
   title: "..."
   aliases:
     - "moc ..."
   type: moc
   classification: ...
   classification_label: "..."
   classification_source: lcc
   primary_moc: <parent-slug>
   related_mocs:
     - "<Parent Display Title>"
   tags:
     - moc
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---
   ```

10. **Update the parent MOC in both vaults** — In each vault, open the parent second-level MOC file (`moc/<parent-slug>.md`):
    - Find a section named `## Child MOCs`, `## Third-level MOCs`, or similar. If no such section exists, add one before `## Related MOCs` (or before `## Notes` if there is no Related MOCs section).
    - Add: `- [[<slug>|<Display Title>]]`
    - Update the `updated:` frontmatter field to today's date in both files.
    - If the parent MOC file does not yet exist in the PCM vault, create it first using the KnowledgeVault version as a reference before adding the child link.

11. **Commit and push in both vaults** — For each vault repo, stage the new MOC file and the updated parent MOC, then commit and push:

    ```bash
    # KnowledgeVault
    git -C ~/KnowledgeVault/personal-knowledge-base add moc/<slug>.md moc/<parent-slug>.md
    git -C ~/KnowledgeVault/personal-knowledge-base commit -m "moc: add <slug> third-level MOC under <parent-slug>"
    git -C ~/KnowledgeVault/personal-knowledge-base push

    # PCM vault
    git -C ~/Projects/private/personal-context-management-private add moc/<slug>.md moc/<parent-slug>.md
    git -C ~/Projects/private/personal-context-management-private commit -m "moc: add <slug> third-level MOC under <parent-slug>"
    git -C ~/Projects/private/personal-context-management-private push
    ```

    Report the commit hash from each repo after pushing.

12. **Report completion** — Summarize:
    - Files created: both full paths
    - Parent MOC updated: both full paths, with the exact line added
    - LCC classification applied: code + label
    - Commits pushed: hash and repo for each

## Success Criteria

- `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md` exists with `primary_moc` set to the parent slug and `classification` filled
- `~/Projects/private/personal-context-management-private/moc/<slug>.md` exists with the same frontmatter fields
- Parent second-level MOC in both vaults has a new `[[<slug>|<Display Title>]]` entry in its child section
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** in either vault — only first-level MOCs are listed there
- The PCM vault's `lcc/` is empty — always look up classifications in `~/KnowledgeVault/personal-knowledge-base/lcc/`
- If the chooser returns no results (no second-level MOCs exist yet), stop and tell the human to first create a second-level MOC using the `second-moc-level` skill
- `primary_moc` in new files should use the parent's slug (lowercase, hyphenated) for consistency — existing files are inconsistent but new ones should be machine-readable slugs
- Related skills: `first-moc-level` (top-level creation), `second-moc-level` (parent creation)
