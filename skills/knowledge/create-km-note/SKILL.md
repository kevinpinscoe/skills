---
name: create-km-note
description: Creates a new knowledge-management note in both vaults by walking through the MOC hierarchy with Python choosers, inheriting LCC classification from the deepest selected MOC, and linking the note back into that MOC.
---

# Create KM Note

> Walks through up to three levels of MOC choosers to place a note precisely in the hierarchy, then creates the note in both knowledge vaults with inherited LCC classification and links it back into the selected MOC.

## How This Skill Chains

Three Python choosers run sequentially and conditionally — first-level always, second-level only if children exist, third-level only if children of the second-level exist. Each chooser runs inline as a Bash step; Claude captures its output, presents the list, waits for the human to pick a number, then continues. The entire flow happens in one Claude session. The note inherits its LCC classification from the **deepest MOC selected**.

## Prerequisites

- `~/KnowledgeVault/personal-knowledge-base/moc/` must contain at least one first-level MOC
- `~/KnowledgeVault/personal-knowledge-base/notes/` and `~/PCM/notes/` must exist
- Both vaults must have `templates/note-template.md`
- Python 3 available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `DEEPEST_MOC` | The most specific MOC selected through the chooser chain | _(resolved by choosers)_ |
| `NOTE_TITLE` | The full human-readable title of the note | _(asked after MOC selection)_ |
| `FILENAME_SLUG` | Kebab-case note subject for the filename | _(derived from title)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share the same structural conventions.

### Note Filename Convention

Note filenames are prefixed with a lowercased LCC code (dots removed) followed by a kebab-case title:

```
<lcc-prefix>-<kebab-title>.md
```

Examples:
- Classification `SB` + title "40V HP Brushless Bike Handle Brush Cutter" → `sb-40v-hp-brushless-bike-handle-brush-cutter.md`
- Classification `ZA` + title "Why use LCC Classifications?" → `za-why-use-lcc-classifications.md`
- Classification `QA76` + title "Linux systemd Timers" → `qa76-linux-systemd-timers.md`
- Classification `T58.5` + title "Cloud Hosting Overview" → `t585-cloud-hosting-overview.md`

To derive the prefix: lowercase the LCC code and remove all dots. Examples: `SB` → `sb`, `QA76` → `qa76`, `QA76.75` → `qa7675`, `T58.5` → `t585`.

### Note Template (identical in both vaults)

`templates/note-template.md`:
```yaml
---
title: "{{title}}"
aliases: []
type: note
classification:
classification_label:
classification_source: lcc
primary_moc:
related_mocs: []
tags: []
created: "{{date:YYYY-MM-DD}}T{{time:HH:mm:ss}}"
updated: "{{date:YYYY-MM-DD}}T{{time:HH:mm:ss}}"
---

# {{title}}

## Summary

## Details

## Related

- [[]]
```

### Existing Note Example

`notes/sb-40v-hp-brushless-bike-handle-brush-cutter.md`:
```yaml
title: "40V HP Brushless Bike Handle Brush Cutter"
aliases:
  - "brush cutter"
type: note
classification: SB
classification_label: "Plant culture"
classification_source: lcc
primary_moc: outdoor-lawn-and-garden-maintenance
related_mocs:
  - "Outdoor Lawn and Garden Maintenance"
tags: []
created: 2026-06-15
updated: 2026-06-15
```

### Vault Paths

| Vault | Notes dir | MOC dir |
|---|---|---|
| KnowledgeVault | `~/KnowledgeVault/personal-knowledge-base/notes/` | `~/KnowledgeVault/personal-knowledge-base/moc/` |
| PCM | `~/PCM/notes/` | `~/PCM/moc/` |

The PCM vault's `lcc/` is empty — always use `~/KnowledgeVault/personal-knowledge-base/lcc/` for any classification lookups.

### MOC Level Detection

- **First-level MOC**: `primary_moc:` field is blank or absent
- **Second-level MOC**: `primary_moc:` is set; its value matches a first-level MOC slug or title
- **Third-level MOC**: `primary_moc:` is set; its value matches a second-level MOC slug or title

## Instructions

1. **Run the first-level MOC chooser** — Run immediately, before asking the human anything:

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
       cls_m = re.search(r'^classification:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       cls = cls_m.group(1).strip() if cls_m and cls_m.group(1) else ""
       lbl_m = re.search(r'^classification_label:[ \t]*"?([^"\n]+)"?', fm, re.MULTILINE)
       lbl = lbl_m.group(1).strip() if lbl_m and lbl_m.group(1) else ""
       results.append((fname[:-3], title, cls, lbl))

   for i, (slug, title, cls, lbl) in enumerate(results, 1):
       print(f"{i}. {title}  [{cls} — {lbl}]  ({slug})")
   ```

   Present the numbered list and ask: "Which first-level MOC does this note belong under? Enter the number." Wait for their answer. Record: `l1_slug`, `l1_title`, `l1_cls`, `l1_lbl`.

   Set `deepest_slug = l1_slug`, `deepest_title = l1_title`, `deepest_cls = l1_cls`, `deepest_lbl = l1_lbl`.

2. **Check for second-level MOCs** — Run this script substituting the selected first-level slug and title:

   ```python
   import os, re

   moc_dir = os.path.expanduser("~/KnowledgeVault/personal-knowledge-base/moc")
   parent_slug = "<l1_slug>"    # substitute
   parent_title = "<l1_title>"  # substitute
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
           continue
       parent_val = primary.group(1).strip().strip('"').strip("'")
       if parent_val.lower() not in (parent_slug.lower(), parent_title.lower()):
           continue
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       cls_m = re.search(r'^classification:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       cls = cls_m.group(1).strip() if cls_m and cls_m.group(1) else ""
       lbl_m = re.search(r'^classification_label:[ \t]*"?([^"\n]+)"?', fm, re.MULTILINE)
       lbl = lbl_m.group(1).strip() if lbl_m and lbl_m.group(1) else ""
       results.append((fname[:-3], title, cls, lbl))

   if not results:
       print("NONE")
   else:
       for i, (slug, title, cls, lbl) in enumerate(results, 1):
           print(f"{i}. {title}  [{cls} — {lbl}]  ({slug})")
   ```

   - If output is `NONE`: no second-level MOCs exist under this parent. Skip to Step 5 (note title).
   - If a list is printed: present it and ask: "Select a second-level MOC, or press Enter to use **[l1_title]** as the target MOC." If the human selects one, record: `l2_slug`, `l2_title`, `l2_cls`, `l2_lbl` and update `deepest_*` to these values. If they press Enter / skip, keep the first-level values as deepest.

3. **Check for third-level MOCs** (only if a second-level MOC was selected) — Run this script substituting the selected second-level slug and title:

   ```python
   import os, re

   moc_dir = os.path.expanduser("~/KnowledgeVault/personal-knowledge-base/moc")
   parent_slug = "<l2_slug>"    # substitute
   parent_title = "<l2_title>"  # substitute
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
           continue
       parent_val = primary.group(1).strip().strip('"').strip("'")
       if parent_val.lower() not in (parent_slug.lower(), parent_title.lower()):
           continue
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       cls_m = re.search(r'^classification:[ \t]*(\S.*)?$', fm, re.MULTILINE)
       cls = cls_m.group(1).strip() if cls_m and cls_m.group(1) else ""
       lbl_m = re.search(r'^classification_label:[ \t]*"?([^"\n]+)"?', fm, re.MULTILINE)
       lbl = lbl_m.group(1).strip() if lbl_m and lbl_m.group(1) else ""
       results.append((fname[:-3], title, cls, lbl))

   if not results:
       print("NONE")
   else:
       for i, (slug, title, cls, lbl) in enumerate(results, 1):
           print(f"{i}. {title}  [{cls} — {lbl}]  ({slug})")
   ```

   - If output is `NONE`: no third-level MOCs exist. Keep `deepest_*` at the second-level values. Skip to Step 5.
   - If a list is printed: present it and ask: "Select a third-level MOC, or press Enter to use **[l2_title]** as the target MOC." If the human selects one, record: `l3_slug`, `l3_title`, `l3_cls`, `l3_lbl` and update `deepest_*` to these values.

4. **Confirm the target MOC** — Tell the human: "The note will be linked to: **[deepest_title]** (classification: `deepest_cls` — deepest_lbl)." Proceed.

5. **Ask for the note title** — Ask: "What is the title of this note?" Wait for their answer.

6. **Ask for a one-line summary** (optional) — Ask: "Brief one-line summary for the note's Summary section? (Press Enter to leave blank.)" Wait for their answer.

7. **Ask about body content** — Ask: "Do you have content to add to this note now, or will you edit it later?" If they provide content, record it as `body_content` to write into the `## Details` section. If they say later / press Enter, leave `## Details` blank.

8. **Derive the filename** — Compute:
   - `lcc_prefix`: lowercase `deepest_cls`, remove all dots. Examples: `SB` → `sb`, `QA76.75` → `qa7675`, `T58.5` → `t585`
   - `title_slug`: lowercase the note title, replace spaces and special characters with hyphens, collapse multiple hyphens. Example: "40V HP Brushless Bike Handle Brush Cutter" → `40v-hp-brushless-bike-handle-brush-cutter`
   - `filename`: `<lcc_prefix>-<title_slug>.md`

9. **Get today's date** — Run `date +%Y-%m-%d` for the `created`/`updated` fields.

10. **Create the KnowledgeVault note** — Write `~/KnowledgeVault/personal-knowledge-base/notes/<filename>`:
   ```yaml
   ---
   title: "<Note Title>"
   aliases: []
   type: note
   classification: <deepest_cls>
   classification_label: "<deepest_lbl>"
   classification_source: lcc
   primary_moc: <deepest_slug>
   related_mocs:
     - "<deepest_title>"
   tags: []
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---

   # <Note Title>

   ## Summary

   <one-line summary if provided, otherwise leave blank>

   ## Details

   <body_content if provided, otherwise leave blank>

   ## Related

   - [[<deepest_slug>|<deepest_title>]]
   ```

11. **Create the PCM note** — Write `~/PCM/notes/<filename>` with identical content.

12. **Update the target MOC in both vaults** — In each vault, open `moc/<deepest_slug>.md`:
    - Find the `## Notes` section. If it contains only `- [[]]`, replace that placeholder line with the new link. Otherwise append the link as a new list item.
    - Link format: `- [[<lcc_prefix>-<title_slug>|<Note Title>]]`
    - Update the `updated:` frontmatter field to today's date.
    - If the target MOC does not exist in the PCM vault, create a minimal stub using the KnowledgeVault version as a reference before editing it.

13. **Commit and push in both vaults** — Stage the new note and updated MOC, then commit and push:

    ```bash
    # KnowledgeVault
    git -C ~/KnowledgeVault/personal-knowledge-base add notes/<filename> moc/<deepest_slug>.md
    git -C ~/KnowledgeVault/personal-knowledge-base commit -m "note: add <lcc_prefix>-<title_slug>"
    git -C ~/KnowledgeVault/personal-knowledge-base push

    # PCM vault
    git -C ~/PCM add notes/<filename> moc/<deepest_slug>.md
    git -C ~/PCM commit -m "note: add <lcc_prefix>-<title_slug>"
    git -C ~/PCM push
    ```

    Report the commit hash from each repo after pushing.

14. **Report completion** — Summarize:
    - Note files created: both full paths
    - Target MOC updated: both full paths, with the exact line added
    - Classification applied: `deepest_cls` — `deepest_lbl`
    - Commits pushed: hash and repo for each

## Success Criteria

- `notes/<filename>` exists in both vaults with `primary_moc` set to `deepest_slug` and `classification` filled
- Target MOC in both vaults contains `[[<lcc_prefix>-<title_slug>|<Note Title>]]` in its `## Notes` section
- Filename follows `<lcc_prefix>-<title_slug>.md` convention (lowercase, no dots in prefix, hyphens throughout)
- Neither `home.md` was modified
- Commits pushed in both repos

## Notes

- The human may stop at any chooser level — if they skip the second-level or third-level chooser (by pressing Enter), the note targets the deepest MOC they did select
- The PCM vault's `lcc/` is empty — always use `~/KnowledgeVault/personal-knowledge-base/lcc/` if any additional classification lookup is needed
- `created` and `updated` use plain `YYYY-MM-DD` format (not the `YYYY-MM-DDThh:mm:ss` Obsidian template syntax — that is resolved by Obsidian's template engine, not here)
- Leave `## Details` and `tags: []` blank for the human to fill in after creation
- Related skills: `first-moc-level`, `second-moc-level`, `third-moc-level` (create MOC structure before adding notes)
