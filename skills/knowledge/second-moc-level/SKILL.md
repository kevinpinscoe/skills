---
name: second-moc-level
description: Creates a second-level Map of Content (MOC) nested under a human-selected first-level parent, asking for a subtopic within that subject, then classifying and writing the MOC in both vaults.
---

# Create Second-Level MOC

> Runs a Python chooser to select a first-level parent MOC, then asks for a subtopic or focus area within that subject, looks up a deeper LCC classification if one exists, and writes the second-level MOC in both knowledge vaults.

## How This Skill Chains

The Python chooser is **Step 1 of this skill** — it runs inline via `python3`, Claude captures its output, presents the numbered list to the human, and the human picks a number. There is no separate launcher. The entire flow — chooser → subtopic question → LCC lookup → file creation — happens in one sequential Claude session. The skill's parameter (the parent MOC) is resolved at runtime through the chooser, not passed in advance.

## Prerequisites

- `~/KnowledgeVault/PKM/moc/` must contain at least one first-level MOC
- `~/PCM/moc/` must exist
- Both vaults must have `templates/moc-note-template.md`
- Python 3 available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `PARENT_MOC` | The first-level MOC this lives under | _(resolved via chooser in Step 1)_ |
| `SUBTOPIC` | The subdivision or focus area within the parent subject | _(asked after parent is chosen)_ |
| `DISPLAY_TITLE` | Title as it should appear in parent MOC links | _(asked after subtopic is known)_ |
| `LCC_CODE` | Classification code — deeper than parent if one exists, otherwise reuse parent's | _(derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share structural conventions.

### MOC Hierarchy

- **First-level MOCs**: Broad subject maps (AI, Linux, Tools, Health). `primary_moc:` is blank.
- **Second-level MOCs**: Sub-topic maps under a first-level parent. `primary_moc:` is set to the parent's slug. Example: "Outdoor Lawn and Garden Maintenance" under "Tools"; "AWS" under "Compute Cloud Hosting".
- **Third-level MOCs**: Narrow maps under a second-level parent.

A parent MOC lists its children in a `## Child MOCs` or `## Second-level MOCs` section (existing files vary; detect and match what the parent uses).

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/PKM/`

- `moc/` — all MOC files; source of truth for the chooser
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

Existing second-level MOC examples:

`moc/outdoor-lawn-and-garden-maintenance.md` — parent: tools, deeper LCC found (SB, Plant culture):
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

`moc/aws.md` — parent: compute-cloud-hosting, no deeper LCC (reuses parent T58.5):
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

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Compute Cloud Hosting" → `compute-cloud-hosting.md`
- **Frontmatter values** (title, labels, aliases): normal capitalization and spaces are fine
- **Files must live in** `moc/`

## Canonical hierarchy — stacks.md

`~/PCM/moc/stacks.md` is the single source of truth for the MOC hierarchy, shared by
both vaults and maintained **only in PCM**. This skill must keep it in sync:

- **Before creating**, review it: `~/PCM/scripts/moc-stacks-editor.sh --list`. Confirm
  the chosen **first-level parent** appears in the tree.
- **After creating** (in the commit step), register the node:
  `~/PCM/scripts/moc-stacks-editor.sh --add "<DISPLAY_TITLE>" --parent the parent's display title` then include
  `moc/stacks.md` in the PCM commit. The tool is idempotent and refuses depth > 3 levels.

## Instructions

1. **Run the parent chooser** — Run this Python script immediately, before asking the human anything:

   ```python
   import os, re

   moc_dir = os.path.expanduser("~/KnowledgeVault/PKM/moc")
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
           continue  # has a parent — is second-level or deeper, skip
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       results.append((fname[:-3], title))

   for i, (slug, title) in enumerate(results, 1):
       print(f"{i}. {title}  ({slug})")
   ```

   Present the numbered list to the human and ask: "Which first-level MOC is the parent for this new second-level MOC? Enter the number." Wait for their answer.

2. **Read the parent MOC's frontmatter** — Open `~/KnowledgeVault/PKM/moc/<parent-slug>.md` and extract:
   - `title` — the parent's display title (e.g. "Tools")
   - `classification` — the parent's LCC code (e.g. `T`)
   - `classification_label` — the parent's LCC label (e.g. "Technology")

   These values are the baseline for the new MOC's classification.

3. **Ask for the subtopic** — Ask: "What subtopic, focus area, or subdivision within **[Parent Title]** do you want to map?" Wait for their answer. This becomes the subject of the new second-level MOC.

4. **Ask for the display title** — Ask: "How should this appear as a title and link in the parent MOC? (e.g. `[[outdoor-lawn-and-garden-maintenance|Outdoor Lawn and Garden Maintenance]]`)" Wait for their answer.

5. **Determine the filename slug** — Convert the subtopic to a lowercase, hyphen-separated slug. Example: "Outdoor Lawn and Garden Maintenance" → `outdoor-lawn-and-garden-maintenance`.

6. **Search for a deeper LCC classification** — Read the relevant LCC outline file from `~/KnowledgeVault/PKM/lcc/` starting from the parent's LCC class letter. Look for a sub-class code that more precisely matches the subtopic.

   **If a more specific sub-class exists**: use it (e.g. parent is `T`, subtopic is lawn and garden → use `SB` Plant culture).

   **If no more specific sub-class fits**: reuse the parent's classification code and label unchanged. Do not force a classification that doesn't fit.

   Common sub-classes by top-level letter:
   - Q: QA (Math/CS), QB (Astronomy), QC (Physics), QD (Chemistry), QH (Biology), QK (Botany), QL (Zoology), QP (Physiology), QR (Microbiology)
   - R: RA (Public health), RC (Internal medicine), RD (Surgery), RF (Otolaryngology), RK (Dentistry), RL (Dermatology), RM (Pharmacology), RS (Pharmacy), RT (Nursing)
   - S: SB (Plant culture), SD (Forestry), SF (Animal culture), SH (Aquaculture/Fishing), SK (Hunting)
   - T: TA (Engineering), TC (Hydraulic), TD (Environmental/Sanitary), TE (Highway), TF (Railroad), TG (Bridge), TH (Building), TJ (Mechanical/Machinery), TK (Electrical/Electronics), TL (Motor Vehicles/Aviation), TN (Mining), TP (Chemical tech), TR (Photography), TS (Manufactures), TT (Handicrafts/Arts and crafts), TX (Home economics)
   - H: HA (Statistics), HB (Economic theory), HC (Economic history), HD (Industries/Labor), HE (Transportation), HF (Commerce), HG (Finance), HJ (Public finance), HM (Sociology), HN (Social history), HQ (Family/Sexuality), HV (Social pathology/Criminology), HX (Socialism)
   - B: BC (Logic), BD (Speculative philosophy), BF (Psychology), BJ (Ethics), BL (Religion), BP (Islam), BQ (Buddhism), BR (Christianity), BS (Bible), BT (Doctrinal theology), BX (Christian denominations)

   Call out ambiguities explicitly before confirming. Example: "lawn tools" could be TJ (Mechanical machinery) or SB (Plant culture) or TT (Handicrafts). Ask: "Which classification best matches your intent: [list candidates]?" Wait for confirmation.

7. **Get today's date** — Run `date +%Y-%m-%d`.

8. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/PKM/moc/<slug>.md`:
   - `title`: the display title
   - `aliases`: `["moc <title lowercase>"]`
   - `type`: `moc`
   - `classification`: the confirmed LCC code (deeper if found, or reused from parent)
   - `classification_label`: the LCC label
   - `classification_source`: `lcc`
   - `primary_moc`: the parent's slug (e.g. `tools`)
   - `related_mocs`: list with the parent's display title
   - `tags`: `["moc"]`
   - `created` / `updated`: today's date
   - Body: `# <title> MOC`, one-sentence Overview describing what subdivision this covers, `## Notes` with `- [[]]`, `## Related MOCs` linking back to parent

9. **Create the PCM MOC file** — Write `~/PCM/moc/<slug>.md` with the same content. Since the PCM template lacks classification fields, add them explicitly:
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

10. **Update the parent MOC in both vaults** — In each vault, open `moc/<parent-slug>.md`:
    - Find the section named `## Child MOCs`, `## Second-level MOCs`, or similar. If no such section exists, add one immediately before `## Related MOCs` (or before `## Notes` if there is no Related MOCs section).
    - Append: `- [[<slug>|<Display Title>]]`
    - Update the `updated:` frontmatter field to today's date.

11. **Commit and push in both vaults** — For each vault repo, stage the new MOC file and the updated parent MOC, then commit and push:

    ```bash
    # KnowledgeVault
    git -C ~/KnowledgeVault/PKM add moc/<slug>.md moc/<parent-slug>.md
    git -C ~/KnowledgeVault/PKM commit -m "moc: add <slug> second-level MOC under <parent-slug>"
    git -C ~/KnowledgeVault/PKM push

    # PCM vault — also register the node in the canonical hierarchy
    ~/PCM/scripts/moc-stacks-editor.sh --add "<DISPLAY_TITLE>" --parent "<PARENT_DISPLAY_TITLE>"
    git -C ~/PCM add moc/<slug>.md moc/<parent-slug>.md moc/stacks.md
    git -C ~/PCM commit -m "moc: add <slug> second-level MOC under <parent-slug>"
    git -C ~/PCM push
    ```

    Report the commit hash from each repo after pushing.

12. **Report completion** — State:
    - Files created: both full paths
    - Parent updated: both full paths, with the exact line added
    - Classification applied: code + label (note if reused from parent or if a deeper one was found)
    - Commits pushed: hash and repo for each

13. **Offer to create a third-level MOC** — After the completion summary, ask the human: "Do you want to create a third-level MOC under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `third-moc-level` skill at `~/skills/skills/knowledge/third-moc-level/SKILL.md` — read that file and follow its Instructions section from Step 1. The second-level MOC just created here will appear as an eligible parent.
    - **If no**: continue to Step 14.

14. **Offer to create a note under this MOC** — Ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `create-km-note` skill at `~/skills/skills/knowledge/create-km-note/SKILL.md`, using **this second-level MOC as the target MOC** for the note. Read that file and follow its Instructions, but **skip the MOC chooser chain (Steps 1–4)** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
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
  - `MOC_NAME` — the subtopic. Use it as `SUBTOPIC` (Step 3).
  - `DISPLAY_TITLE` — the title/link text (Step 4). If absent, title-case `MOC_NAME`.
  - `PARENT_SLUG` — the **first-level** parent MOC's filename slug.
- **Skip Step 1 (the parent chooser).** The parent is `PARENT_SLUG`; read its frontmatter
  per Step 2 (title, classification, classification_label).
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 5.
- **LCC classification (Step 6)** — search for a deeper class, then **auto-select the best
  match without asking**, reusing the parent's classification if none clearly fits. Do not
  block on ambiguity.
- **Execute Steps 7–12 exactly as written** — create both vault files, update the parent
  MOC in both vaults, commit and push. Do **not** modify `home.md`.
- **Skip Steps 13–14** (the interactive offers to create a third-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line so the caller can confirm success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions above as usual.

## Success Criteria

- `~/KnowledgeVault/PKM/moc/<slug>.md` exists with `primary_moc` set to the parent slug and `classification` filled
- `~/PCM/moc/<slug>.md` exists with the same frontmatter
- Parent MOC in both vaults contains `[[<slug>|<Display Title>]]` in a child section
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** — only first-level MOCs are listed there
- The PCM vault's `lcc/` is empty — always look up classifications in `~/KnowledgeVault/PKM/lcc/`
- Reusing the parent's classification is correct and expected when no more specific LCC sub-class fits (e.g. AWS under Compute Cloud Hosting both use T58.5)
- If the parent MOC does not yet exist in the PCM vault, create a minimal stub there using the KnowledgeVault version as a reference before editing it
- Related skills: `first-moc-level` (create the parent first), `third-moc-level` (create a child of this MOC)
