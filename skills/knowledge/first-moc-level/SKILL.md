---
name: first-moc-level
description: Creates a first-level Map of Content (MOC) file in both the personal knowledge base and personal context management vaults, with LCC classification in frontmatter.
---

# Create First-Level MOC

> Creates a first-level Map of Content (MOC) markdown file in both knowledge vaults, performs an LCC classification lookup, confirms the correct category with the human, and adds a navigation link to each vault's home.md.

## Prerequisites

- `~/KnowledgeVault/PKM/` must exist and contain a `lcc/` directory with LCC outline files (`lcco-a.md` through `lcco-z.md`)
- `~/PCM/` must exist
- Both vaults must have `templates/moc-note-template.md` and `moc/` directories

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SUBJECT` | The topic this MOC will cover | _(required — ask the user)_ |
| `DISPLAY_TITLE` | Human-readable title as it should appear in home.md links | _(required — ask the user)_ |
| `LCC_CODE` | LCC classification code (determined via lookup + human confirmation) | _(required — derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two separate knowledge-management repositories. Both follow the same structural conventions, so an AI unfamiliar with them can apply this skill correctly.

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/PKM/`

A long-term technical knowledge base organized around MOCs, shallow folders, links, and LCC classification. Core principle: folders are for storage, MOCs are for navigation, links are for relationships.

Key directories:
- `moc/` — Map of Content files (navigation hubs). First-level MOCs are broad topic maps (AI, Linux, Tools, Health, etc.)
- `lcc/` — Library of Congress Classification outlines (`lcco-a.md` through `lcco-z.md`); used to determine classification codes and labels for frontmatter
- `notes/` — Evergreen notes, often prefixed with LCC codes (e.g. `qa76-linux-systemd-timers.md`)
- `home.md` — The vault front door; contains a `## Main Indexes` section with wiki-links to each first-level MOC

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

Existing first-level MOC examples (filename → classification):
- `moc/ai.md` → classification: QA76, label: "Computer science"
- `moc/tools.md` → classification: T, label: "Technology"
- `moc/linux.md` → classification: QA76, label: "Computer science"
- `moc/health.md` → classification: R, label: "Medicine"

### Vault 2 — Personal Context Management (private)
Path: `~/PCM/`

An operational layer for the PCM workflow — holds ingest pipeline configuration, AI conversation exports, and Obsidian-ready distilled output. Its `moc/` directory mirrors the same structure as the KnowledgeVault but starts empty.

Key directories:
- `moc/` — same role as in the KnowledgeVault
- `lcc/` — exists but is empty; use the KnowledgeVault's `lcc/` for all lookups
- `home.md` — currently contains only quick links to directories; add a `## Maps of Content` section if one does not already exist

Template: `templates/moc-note-template.md`
```yaml
---
title: "{{title}}"
type: moc
tags: []
created: {{date}}
updated: {{date}}
---

# {{title}}

## Overview

<!-- What does this map cover? -->

## Notes

- [[]]

## Related MOCs

- [[]]
```

Note: The PCM template does not include classification fields by default. **Add them anyway** — the human has requested LCC classification in frontmatter for both vaults.

## Naming Rules (both vaults)

- **Filename**: lowercase, hyphen-separated, no spaces. Derived from the subject name. Example: "Compute Infrastructure" → `compute-infrastructure.md`
- **Title, aliases, classification labels, and display names in home.md** may use normal capitalization, spaces, and punctuation
- **File must live in** `moc/`

## Canonical hierarchy — stacks.md

`~/PCM/moc/stacks.md` is the single source of truth for the MOC hierarchy, shared by
both vaults and maintained **only in PCM**. This skill must keep it in sync:

- **Before creating**, review it: `~/PCM/scripts/moc-stacks-editor.sh --list`. Confirm
  this is genuinely a new **top-level** MOC (not already a child of another MOC).
- **After creating** (in the commit step), register the node:
  `~/PCM/scripts/moc-stacks-editor.sh --add "<DISPLAY_TITLE>" --parent "MOCs"` then include
  `moc/stacks.md` in the PCM commit. The tool is idempotent and refuses depth > 3 levels.

## Instructions

1. **Ask for subject name** — Ask the human: "What is the subject of this MOC?" Wait for their answer before proceeding.

2. **Ask for display title and link text** — Ask: "How should the title and link name appear in home.md for each vault? (For example: `[[linux|Linux]]` uses `Linux` as the display text.)" Wait for their answer.

3. **Determine the filename slug** — Convert the subject name to a lowercase, hyphen-separated slug. Example: "Compute Infrastructure" → `compute-infrastructure`. This will be the filename in both vaults: `moc/<slug>.md`.

4. **Search the LCC catalog** — Read the LCC outline files in `~/KnowledgeVault/PKM/lcc/`. The files are named `lcco-a.md`, `lcco-b.md`, ..., `lcco-z.md` and contain the Library of Congress Classification hierarchy. Search for classes that plausibly match the subject. Common top-level classes:
   - A: General Works
   - B: Philosophy, Psychology, Religion
   - G: Geography, Anthropology, Recreation
   - H: Social Sciences
   - J: Political Science
   - K: Law
   - L: Education
   - M: Music
   - N: Fine Arts
   - P: Language and Literature
   - Q: Science (QA = Mathematics/Computer Science, QB = Astronomy, QC = Physics, QD = Chemistry, QH = Biology, QK = Botany, QL = Zoology, QM = Anatomy, QP = Physiology, QR = Microbiology)
   - R: Medicine
   - S: Agriculture
   - T: Technology (TA = Engineering, TH = Building, TJ = Mechanical, TK = Electrical, TL = Motor Vehicles, TT = Handicrafts, TX = Home Economics)
   - U: Military Science
   - V: Naval Science
   - Z: Bibliography, Library Science

5. **Present candidates and confirm** — Present 2–4 candidate LCC codes and labels that could match the subject. Be explicit about potential ambiguities. Examples of disambiguation to include:
   - "Tools" could mean: T (Technology broadly), TJ (Mechanical engineering and machinery), TT (Handicrafts/Arts and crafts — hand tools), or QA76 (Computer software — software tools/utilities)
   - "Radio" could mean: TK (Electrical engineering and electronics) or P (Language and Literature — broadcasting)
   - "Finance" could mean: HG (Finance) or HJ (Public finance)
   
   Ask: "Which LCC classification best matches your intent? [list candidates with codes and labels]" Wait for confirmation before continuing.

6. **Get today's date** — Run `date +%Y-%m-%d` to get the current date in YYYY-MM-DD format.

7. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/PKM/moc/<slug>.md` using the KnowledgeVault template. Fill in:
   - `title`: the display title the human provided (or a sensible title from the subject name)
   - `aliases`: `["moc <title>"]` — lowercase alias
   - `type`: `moc`
   - `classification`: the confirmed LCC code (e.g. `T`, `QA76`, `R`)
   - `classification_label`: the LCC class label (e.g. `"Technology"`, `"Computer science"`, `"Medicine"`)
   - `classification_source`: `lcc`
   - `primary_moc`: leave blank (this is itself a first-level MOC)
   - `related_mocs`: `[]`
   - `tags`: `["moc"]`
   - `created`: today's date
   - `updated`: today's date
   - Body: fill `# <title> MOC` heading; write a one-sentence overview describing what the map covers

8. **Create the PCM MOC file** — Write `~/PCM/moc/<slug>.md` using the PCM template. Use the same title, date, and classification fields as the KnowledgeVault file. The PCM template omits classification fields; add them in the same order and format as the KnowledgeVault version:
   ```yaml
   ---
   title: "..."
   aliases:
     - "moc ..."
   type: moc
   classification: ...
   classification_label: "..."
   classification_source: lcc
   related_mocs: []
   tags:
     - moc
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---
   ```
   Body: same heading and overview as the KnowledgeVault file.

9. **Update KnowledgeVault home.md** — Open `~/KnowledgeVault/PKM/home.md`. Add a new entry under `## Main Indexes` in the format:
   ```
   - [[<slug>|<Display Title>]]
   ```
   where `<slug>` is the filename without `.md` and `<Display Title>` is what the human specified. Keep the list alphabetically ordered or append at the end if ordering is unclear.

10. **Update PCM home.md** — Open `~/PCM/home.md`. If a `## Maps of Content` section already exists, add:
    ```
    - [[<slug>|<Display Title>]]
    ```
    If no `## Maps of Content` section exists, add one after `## Quick Links`:
    ```markdown
    ## Maps of Content

    - [[<slug>|<Display Title>]]
    ```

11. **Commit and push in both vaults** — For each vault repo, stage the new MOC file and the updated `home.md`, then commit and push:

    ```bash
    # KnowledgeVault
    git -C ~/KnowledgeVault/PKM add moc/<slug>.md home.md
    git -C ~/KnowledgeVault/PKM commit -m "moc: add <slug> first-level MOC"
    git -C ~/KnowledgeVault/PKM push

    # PCM vault — also register the node in the canonical hierarchy
    ~/PCM/scripts/moc-stacks-editor.sh --add "<DISPLAY_TITLE>" --parent "MOCs"
    git -C ~/PCM add moc/<slug>.md home.md moc/stacks.md
    git -C ~/PCM commit -m "moc: add <slug> first-level MOC"
    git -C ~/PCM push
    ```

    Report the commit hash from each repo after pushing.

12. **Report completion** — Summarize:
    - Files created: list both full paths
    - LCC classification applied: code + label
    - home.md entries added: show the exact lines added in each file
    - Commits pushed: hash and repo for each

13. **Offer to create a second-level MOC** — After the completion summary, ask the human: "Do you want to create a second-level MOC under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `second-moc-level` skill at `~/skills/skills/knowledge/second-moc-level/SKILL.md` — read that file and follow its Instructions section from Step 1 (the parent chooser). The MOC just created here will appear in that chooser as an eligible parent.
    - **If no**: continue to Step 14.

14. **Offer to create a note under this MOC** — Ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If no**: stop. The skill is complete.
    - **If yes**: ask which vault the note belongs in — "Which vault should this note live in: **PCM** or **PKM**? (A note lives in only one vault; MOCs may exist in both.)" Then execute the matching note skill, using **this first-level MOC as the target MOC** for the note:
      - **PCM** → `~/skills/skills/knowledge/create-a-pcm-note/SKILL.md`
      - **PKM** → `~/skills/skills/knowledge/create-a-pkm-note/SKILL.md`

      Read that file and follow its Instructions, but **skip its MOC chooser chain** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
      - `deepest_slug` = this MOC's `<slug>`
      - `deepest_title` = this MOC's display title
      - `deepest_cls` = this MOC's `classification`
      - `deepest_lbl` = this MOC's `classification_label`

      Then continue from the note skill's "ask for the note title" step onward. The note will inherit this MOC's LCC classification and be linked back into its `## Notes` section in the chosen vault.

## Unattended parameterized invocation

This skill is normally interactive. When it is invoked **headlessly by
`scripts/moc-navigator.py`** in the PCM repo (via `claude -p`), it runs UNATTENDED with
parameters supplied in the prompt. In that mode, follow these rules instead of the
interactive prompts in the numbered Instructions:

- **No questions.** Do not pause for human input at any step. The root directive's
  confirmation requirement is waived for this automated invocation — it declares itself
  unattended/headless, equivalent to a systemd context.
- **Parameters** (read from the invoking prompt):
  - `MOC_NAME` — the subject of the MOC. Use it as `SUBJECT` (Step 1).
  - `DISPLAY_TITLE` — the title/link text (Step 2). If absent, title-case `MOC_NAME`.
  - (A first-level MOC has no parent.)
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 3.
- **LCC classification (Steps 4–5)** — perform the lookup, then **auto-select the single
  best-matching class without asking.** If genuinely ambiguous, pick the most likely and
  state the choice in the final report; do not block.
- **Execute Steps 6–12 exactly as written** — create both vault files, update both
  `home.md` files, commit and push in both repos.
- **Skip Steps 13–14** (the interactive offers to create a second-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line so the caller can confirm success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions above as usual.

## Success Criteria

- `~/KnowledgeVault/PKM/moc/<slug>.md` exists with correct YAML frontmatter including `classification`, `classification_label`, and `classification_source: lcc`
- `~/PCM/moc/<slug>.md` exists with the same frontmatter fields
- Both `home.md` files contain a new `[[<slug>|<Display Title>]]` link
- Filename is lowercase, hyphen-separated, no spaces, ends in `.md`
- `type: moc` is set in both files
- `created` and `updated` are set to today's date in `YYYY-MM-DD` format

## Notes

- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/lcc/` is a symlink to it, so either path works for classification lookups
- When the subject is ambiguous (e.g. "tools", "radio", "security"), always surface the ambiguity before choosing a classification — do not guess
- The `primary_moc` field in the KnowledgeVault template is left blank for first-level MOCs; second-level MOCs (child MOCs) would set this to their parent
- If the `.gitkeep` file is the only file in `moc/` of the PCM vault, it can remain in place — git will still track the directory with real content present
- Related skills: `second-moc-level` (for child MOCs), `third-moc-level` (for leaf MOCs), `create-a-pcm-note` / `create-a-pkm-note` (for individual notes, one per vault)
