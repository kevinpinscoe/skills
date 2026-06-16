---
name: second-moc-level
description: Creates a second-level Map of Content (MOC) file nested under a chosen first-level parent, with LCC classification in frontmatter, using an interactive Python chooser to select the parent.
---

# Create Second-Level MOC

> Creates a second-level Map of Content (MOC) in both knowledge vaults under a human-selected first-level parent MOC, with LCC classification in frontmatter, and links the new MOC into its parent.

## Prerequisites

- `~/KnowledgeVault/personal-knowledge-base/moc/` must contain at least one first-level MOC file
- `~/Projects/private/personal-context-management-private/moc/` must exist
- Both vaults must have `templates/moc-note-template.md`
- Python 3 must be available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SUBJECT` | The topic this MOC will cover | _(required — ask the user)_ |
| `DISPLAY_TITLE` | Human-readable title as it should appear in the parent MOC and links | _(required — ask the user)_ |
| `PARENT_MOC` | The first-level MOC this MOC belongs under | _(required — selected via chooser)_ |
| `LCC_CODE` | LCC classification code (determined via lookup + human confirmation) | _(required — derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share the same structural conventions.

### MOC Hierarchy

MOCs (Maps of Content) are navigation hubs organized in levels:
- **First-level MOCs**: Broad topic maps (AI, Linux, Tools, Health). `primary_moc:` field is empty.
- **Second-level MOCs**: Sub-topic maps nested under a first-level parent. `primary_moc:` is set to the parent title. Example: "Outdoor Lawn and Garden Maintenance" lives under "Tools"; "AWS" lives under "Compute Cloud Hosting".
- **Third-level MOCs**: Narrowly focused maps nested under a second-level parent.

Parent MOCs list their children in a `## Child MOCs` or `## Second-level MOCs` section (existing files use both names; detect what the parent already uses).

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/personal-knowledge-base/`

- `moc/` — all MOC files at all levels; use this directory for the parent chooser
- `lcc/` — LCC outline files (`lcco-a.md` through `lcco-z.md`) for classification lookup
- `home.md` — **do not modify** for second-level MOCs; only first-level MOCs appear there

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

Existing second-level MOC example (`moc/outdoor-lawn-and-garden-maintenance.md`):
```yaml
title: "Outdoor Lawn and Garden Maintenance"
aliases:
  - "moc outdoor lawn and garden maintenance"
type: moc
classification: SB
classification_label: "Plant culture"
classification_source: lcc
primary_moc: tools
related_mocs:
  - "Tools"
tags:
  - moc
created: 2026-06-15
updated: 2026-06-15
```

Existing second-level MOC example (`moc/aws.md`):
```yaml
title: "AWS"
aliases:
  - "moc aws"
type: moc
classification: T58.5
classification_label: "Information technology"
classification_source: lcc
primary_moc: "Compute Cloud Hosting"
related_mocs:
  - "Compute Cloud Hosting"
tags:
  - moc
created: 2026-06-15
updated: 2026-06-15
```

### Vault 2 — Personal Context Management (private)
Path: `~/Projects/private/personal-context-management-private/`

- `moc/` — mirrors the KnowledgeVault; may be empty or have fewer files
- `lcc/` — empty; always use the KnowledgeVault's `lcc/` for lookups
- `home.md` — **do not modify** for second-level MOCs

Template: `templates/moc-note-template.md` (simpler than KnowledgeVault's; add classification fields anyway per vault conventions):
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

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Compute Cloud Hosting" → `compute-cloud-hosting.md`
- **Title, aliases, frontmatter labels**: may use normal capitalization and spaces
- **File must live in** `moc/`

## Instructions

1. **Ask for subject name** — Ask: "What is the subject of this second-level MOC?" Wait for their answer.

2. **Ask for display title** — Ask: "How should the title and link name appear in the parent MOC? (e.g. `[[aws|AWS]]` uses `AWS` as display text.)" Wait for their answer.

3. **Run the parent MOC chooser** — Write and run this Python script to list all first-level MOCs from `~/KnowledgeVault/personal-knowledge-base/moc/`:

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
       # First-level MOCs have primary_moc blank or absent
       primary = re.search(r'^primary_moc:\s*(\S.*)?$', fm, re.MULTILINE)
       if primary and primary.group(1) and primary.group(1).strip():
           continue  # has a parent — skip
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       results.append((fname[:-3], title))

   for i, (slug, title) in enumerate(results, 1):
       print(f"{i}. {title}  ({slug})")
   ```

   Present the numbered list output to the human and ask: "Which first-level MOC is the parent for this new MOC? Enter the number." Wait for their selection and record the parent's slug and title.

4. **Determine the filename slug** — Convert the subject name to a lowercase, hyphen-separated slug. Example: "Compute Cloud Hosting" → `compute-cloud-hosting`.

5. **Search the LCC catalog** — Read the relevant LCC outline file(s) in `~/KnowledgeVault/personal-knowledge-base/lcc/`. Files are named `lcco-a.md` through `lcco-z.md`. Common top-level classes:
   - Q: Science (QA = Mathematics/Computer Science, QH = Biology, QR = Microbiology)
   - R: Medicine
   - S: Agriculture (SB = Plant culture, SF = Animal culture)
   - T: Technology (TA = Engineering, TH = Building, TJ = Mechanical, TK = Electrical, TL = Motor Vehicles, TN = Mining, TP = Chemical, TR = Photography, TS = Manufactures, TT = Handicrafts, TX = Home Economics)
   - H: Social Sciences (HG = Finance, HV = Social pathology)
   - B: Philosophy, Psychology, Religion

6. **Present candidates and confirm** — List 2–4 plausible LCC codes and labels. Call out any ambiguity explicitly (e.g. "lawn equipment" could be SB = Plant culture or TJ = Mechanical engineering). Ask: "Which classification best matches your intent?" Wait for confirmation.

7. **Get today's date** — Run `date +%Y-%m-%d`.

8. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md`:
   - `title`: display title
   - `aliases`: `["moc <title lowercase>"]`
   - `type`: `moc`
   - `classification`: confirmed LCC code
   - `classification_label`: LCC class label
   - `classification_source`: `lcc`
   - `primary_moc`: parent slug (use the slug, e.g. `tools`) — match the style seen in sibling files in the parent's directory
   - `related_mocs`: list containing the parent's display title
   - `tags`: `["moc"]`
   - `created` / `updated`: today's date
   - Body: `# <title> MOC`, one-sentence Overview, `## Notes` with empty `[[]]`, `## Related MOCs` linking to parent

9. **Create the PCM MOC file** — Write `~/Projects/private/personal-context-management-private/moc/<slug>.md` with identical content except the PCM template is the base. Add all classification fields explicitly (they are not in the PCM template by default):
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

10. **Update the parent MOC in both vaults** — In each vault, open the parent MOC file (`moc/<parent-slug>.md`):
    - Find the section named `## Child MOCs`, `## Second-level MOCs`, or similar. If no such section exists, add one before `## Related MOCs` (or before `## Notes` if no Related MOCs section).
    - Add the link: `- [[<slug>|<Display Title>]]`
    - Also update the `updated:` frontmatter field to today's date in both vaults.

11. **Report completion** — Summarize:
    - Files created: both full paths
    - Parent MOC updated: both full paths, with the line added
    - LCC classification applied: code + label

## Success Criteria

- `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md` exists with `primary_moc` set to the parent's slug and `classification` filled
- `~/Projects/private/personal-context-management-private/moc/<slug>.md` exists with the same frontmatter fields
- Parent MOC in both vaults has a new `[[<slug>|<Display Title>]]` entry in its child section
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** in either vault — only first-level MOCs are listed there
- The PCM vault's `lcc/` is empty — always look up classifications in `~/KnowledgeVault/personal-knowledge-base/lcc/`
- `primary_moc` style is inconsistent in existing files (some use the slug, some the title) — prefer the slug for new files to keep it machine-readable, but match the parent's existing style if siblings already exist
- If the parent MOC file does not exist in the PCM vault, create a stub there using the KnowledgeVault version as a reference — but do not overwrite it if it already exists
- Related skills: `first-moc-level` (parent creation), `third-moc-level` (child creation)
