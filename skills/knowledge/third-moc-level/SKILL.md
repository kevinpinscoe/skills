---
name: third-moc-level
description: Creates a third-level Map of Content (MOC) by first choosing a first-level MOC, then choosing a second-level MOC under it, then asking for a further focus area within that subtopic.
---

# Create Third-Level MOC

> Runs two sequential Python choosers — first to select a first-level parent, then to select a second-level parent under it — then asks for a further focus area within that subtopic, looks up a deeper LCC classification if one exists, and writes the third-level MOC in both knowledge vaults.

## How This Skill Chains

Both Python choosers run **inline as Steps 1 and 3** of this skill. Claude runs each script, presents the numbered list, waits for the human to pick a number, then continues. There is no separate launcher. The entire flow — chooser 1 → chooser 2 → focus area question → LCC lookup → file creation → commit — happens in one sequential Claude session.

## Prerequisites

- `~/KnowledgeVault/personal-knowledge-base/moc/` must contain at least one first-level MOC and at least one second-level MOC
- `~/PCM/moc/` must exist
- Both vaults must have `templates/moc-note-template.md`
- Python 3 available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `GRANDPARENT_MOC` | The first-level MOC (narrows the second-level chooser) | _(resolved via chooser in Step 1)_ |
| `PARENT_MOC` | The second-level MOC this lives under | _(resolved via chooser in Step 3)_ |
| `FOCUS_AREA` | The further subdivision or focus area within the parent subtopic | _(asked after parent is chosen)_ |
| `DISPLAY_TITLE` | Title as it should appear in parent MOC links | _(asked after focus area is known)_ |
| `LCC_CODE` | Classification code — deeper than parent if one exists, otherwise reuse parent's | _(derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share structural conventions.

### MOC Hierarchy

- **First-level MOCs**: Broad subject maps (AI, Linux, Tools, Software). `primary_moc:` is blank.
- **Second-level MOCs**: Sub-topic maps under a first-level parent. `primary_moc:` is set to the parent slug or title.
- **Third-level MOCs**: Narrowly focused maps under a second-level parent. `primary_moc:` is set to the second-level parent's slug.

A parent MOC lists its children in a `## Child MOCs`, `## Second-level MOCs`, or `## Third-level MOCs` section (detect and match what the parent already uses).

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/personal-knowledge-base/`

- `moc/` — all MOC files at all levels; source of truth for both choosers
- `lcc/` — LCC outline files (`lcco-a.md` through `lcco-z.md`) for classification lookup
- `home.md` — **do not modify**; only first-level MOCs appear there

Template (`templates/moc-note-template.md`):
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
Path: `~/PCM/`

- `moc/` — mirrors the KnowledgeVault; may be empty or partial
- `lcc/` — empty; always use the KnowledgeVault's `lcc/` for all lookups
- `home.md` — **do not modify**

Template (`templates/moc-note-template.md`) — simpler; add classification fields explicitly:
```yaml
---
title: "{{title}}"
type: moc
tags: []
created: {{date}}
updated: {{date}}
---
```

### Naming Rules

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Package Managers" → `package-managers.md`
- **Frontmatter values** (title, labels, aliases): normal capitalization and spaces are fine
- **Files must live in** `moc/`

## Instructions

1. **Run the first-level MOC chooser** — Run this Python script immediately, before asking the human anything:

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
       primary = re.search(r'^primary_moc:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       if primary and primary.group(1) and primary.group(1).strip():
           continue  # has a parent — skip
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       results.append((fname[:-3], title))

   for i, (slug, title) in enumerate(results, 1):
       print(f"{i}. {title}  ({slug})")
   ```

   Present the numbered list and ask: "Which first-level MOC contains the second-level MOC you want to nest under? Enter the number." Wait for their answer. Record the selected first-level MOC's **slug** and **title**.

2. **Read the first-level MOC's frontmatter** — Open `~/KnowledgeVault/personal-knowledge-base/moc/<grandparent-slug>.md` and extract its `title`.

3. **Run the second-level MOC chooser** — Run this Python script, substituting the selected grandparent slug and title:

   ```python
   import os, re

   moc_dir = os.path.expanduser("~/KnowledgeVault/personal-knowledge-base/moc")
   grandparent_slug = "<grandparent-slug>"   # substitute from step 1
   grandparent_title = "<Grandparent Title>" # substitute from step 1
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
       primary = re.search(r'^primary_moc:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       if not primary or not primary.group(1) or not primary.group(1).strip():
           continue  # no parent — first-level, skip
       parent_val = primary.group(1).strip().strip('"').strip("'")
       if parent_val.lower() not in (grandparent_slug.lower(), grandparent_title.lower()):
           continue  # belongs to a different first-level MOC
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       class_m = re.search(r'^classification:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       cls = class_m.group(1).strip() if class_m and class_m.group(1) else ""
       results.append((fname[:-3], title, cls))

   if not results:
       print("No second-level MOCs found under this parent. Create one first with the second-moc-level skill.")
   else:
       for i, (slug, title, cls) in enumerate(results, 1):
           print(f"{i}. {title}  (classification: {cls}, file: {slug})")
   ```

   If the output reports no second-level MOCs under that parent, stop and tell the human to run the `second-moc-level` skill first.

   Otherwise, present the numbered list and ask: "Which second-level MOC is the parent for this new third-level MOC? Enter the number." Wait for their answer. Record the selected second-level MOC's **slug**, **title**, **classification code**, and **classification_label**.

4. **Read the second-level MOC's frontmatter** — Open `~/KnowledgeVault/personal-knowledge-base/moc/<parent-slug>.md` and extract:
   - `title` — the parent's display title
   - `classification` — the parent's LCC code (baseline for this MOC)
   - `classification_label` — the parent's LCC label

5. **Ask for the focus area** — Ask: "What further focus area or subdivision within **[Parent Title]** do you want to map?" Wait for their answer. This becomes the subject of the new third-level MOC.

6. **Ask for the display title** — Ask: "How should this appear as a title and link in the parent MOC? (e.g. `[[package-managers|Package Managers]]`)" Wait for their answer.

7. **Determine the filename slug** — Convert the focus area to a lowercase, hyphen-separated slug. Example: "Package Managers" → `package-managers`.

8. **Search for a deeper LCC classification** — Read the relevant LCC outline file from `~/KnowledgeVault/personal-knowledge-base/lcc/` starting from the parent's LCC class. Look for a sub-class that more precisely matches the focus area.

   **If a more specific sub-class exists**: use it.

   **If no more specific sub-class fits**: reuse the parent's classification code and label unchanged. Do not force a classification that doesn't fit.

   Call out ambiguities before confirming. Ask: "Which classification best matches your intent: [list candidates]?" Wait for confirmation.

9. **Get today's date** — Run `date +%Y-%m-%d`.

10. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md`:
    - `title`: the display title
    - `aliases`: `["moc <title lowercase>"]`
    - `type`: `moc`
    - `classification`: confirmed LCC code (deeper or reused)
    - `classification_label`: LCC label
    - `classification_source`: `lcc`
    - `primary_moc`: the second-level parent's slug
    - `related_mocs`: list with the second-level parent's display title
    - `tags`: `["moc"]`
    - `created` / `updated`: today's date
    - Body: `# <title> MOC`, one-sentence Overview describing what focus area this covers, `## Notes` with `- [[]]`, `## Related MOCs` linking back to parent

11. **Create the PCM MOC file** — Write `~/PCM/moc/<slug>.md` with the same content. Add all classification fields explicitly since the PCM template omits them:
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

12. **Update the parent MOC in both vaults** — In each vault, open `moc/<parent-slug>.md`:
    - Find a section named `## Child MOCs`, `## Third-level MOCs`, or similar. If no such section exists, add one immediately before `## Related MOCs` (or before `## Notes` if there is no Related MOCs section).
    - Append: `- [[<slug>|<Display Title>]]`
    - Update the `updated:` frontmatter field to today's date.
    - If the parent MOC file does not yet exist in the PCM vault, create a minimal stub using the KnowledgeVault version as a reference before editing it.

13. **Commit and push in both vaults** — For each vault repo, stage the new MOC file and the updated parent MOC, then commit and push:

    ```bash
    # KnowledgeVault
    git -C ~/KnowledgeVault/personal-knowledge-base add moc/<slug>.md moc/<parent-slug>.md
    git -C ~/KnowledgeVault/personal-knowledge-base commit -m "moc: add <slug> third-level MOC under <parent-slug>"
    git -C ~/KnowledgeVault/personal-knowledge-base push

    # PCM vault
    git -C ~/PCM add moc/<slug>.md moc/<parent-slug>.md
    git -C ~/PCM commit -m "moc: add <slug> third-level MOC under <parent-slug>"
    git -C ~/PCM push
    ```

    Report the commit hash from each repo after pushing.

14. **Report completion** — Summarize:
    - Files created: both full paths
    - Parent MOC updated: both full paths, with the exact line added
    - LCC classification applied: code + label (note if reused from parent or deeper)
    - Commits pushed: hash and repo for each

15. **Offer to create a note under this MOC** — After the completion summary, ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `create-km-note` skill at `~/skills/skills/knowledge/create-km-note/SKILL.md`, using **this third-level MOC as the target MOC** for the note. Read that file and follow its Instructions, but **skip the MOC chooser chain (Steps 1–4)** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
      - `deepest_slug` = this MOC's `<slug>`
      - `deepest_title` = this MOC's display title
      - `deepest_cls` = this MOC's `classification`
      - `deepest_lbl` = this MOC's `classification_label`

      Then continue from Step 5 (ask for the note title) onward. The note will inherit this MOC's LCC classification and be linked back into its `## Notes` section.
    - **If no**: stop. The skill is complete.

## Unattended parameterized invocation

This skill is normally interactive. When it is invoked **headlessly by
`scripts/moc-navigator.py`** in the PCM repo (via `claude -p`), it runs UNATTENDED with
parameters supplied in the prompt. In that mode, follow these rules instead of the
interactive prompts in the numbered Instructions:

- **No questions.** Do not pause for human input. The root directive's confirmation
  requirement is waived for this automated invocation — it declares itself unattended.
- **Parameters** (read from the invoking prompt):
  - `MOC_NAME` — the focus area. Use it as `FOCUS_AREA` (Step 5).
  - `DISPLAY_TITLE` — the title/link text (Step 6). If absent, title-case `MOC_NAME`.
  - `PARENT_SLUG` — the **second-level** parent MOC's filename slug.
- **Skip Steps 1 and 3 (both choosers).** The second-level parent is `PARENT_SLUG`; read
  its frontmatter per Step 4 (title, classification, classification_label).
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 7.
- **LCC classification (Step 8)** — search for a deeper class, then **auto-select the best
  match without asking**, reusing the parent's classification if none clearly fits. Do not
  block on ambiguity.
- **Execute Steps 9–14 exactly as written** — create both vault files, update the
  second-level parent MOC in both vaults, commit and push. Do **not** modify `home.md`.
- **Skip Step 15** (the interactive offer to create a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line so the caller can confirm success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions above as usual.

## Success Criteria

- `~/KnowledgeVault/personal-knowledge-base/moc/<slug>.md` exists with `primary_moc` set to the second-level parent's slug and `classification` filled
- `~/PCM/moc/<slug>.md` exists with the same frontmatter
- Second-level parent MOC in both vaults contains `[[<slug>|<Display Title>]]` in a child section
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** — only first-level MOCs are listed there
- The PCM vault's `lcc/` is empty — always look up classifications in `~/KnowledgeVault/personal-knowledge-base/lcc/`
- The second-level chooser matches `primary_moc` against both the grandparent slug and title (case-insensitive) to handle the inconsistency in existing files where some use slugs and some use display titles
- Reusing the parent's classification is correct when no tighter LCC sub-class fits
- If the chooser in Step 3 returns no results, stop and direct the human to the `second-moc-level` skill
- Related skills: `first-moc-level` (top-level creation), `second-moc-level` (create the parent first)
