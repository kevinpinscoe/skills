---
name: knowledge-first-moc-level
category: knowledge
description: Creates a first-level Map of Content (MOC) file in both the personal knowledge base and personal context management vaults, with LCC classification in frontmatter.
disable-model-invocation: true
---

# Create First-Level MOC

> Creates a first-level Map of Content (MOC) markdown file in both knowledge vaults, performs an LCC classification lookup, confirms the correct category with the human, and adds a navigation link to each vault's home.md.

## The MOC chooser does not apply here

`km-moc-chooser` picks an existing **parent** MOC. A first-level MOC has no parent, so this
skill never opens the chooser or its popup. Instead, Step 3 checks the new name against the
canonical MOC map automatically (`km-moc-dupcheck`). It asks the human something only when a
possible duplicate turns up.

## Prerequisites

- `~/Projects/private/knowledge-management-practice` cloned (it provides `moc-op` and the
  canonical map), and push access to the PKM, PCM and knowledge-management-practice repositories
- `~/KnowledgeVault/PKM/` must exist and contain a `lcc/` directory with LCC outline files (`lcco-a.md` through `lcco-z.md`)
- `~/PCM/PCM/` must exist
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
- `home.md` — The vault front door; contains a `## Maps of Content` section with wiki-links to each first-level MOC

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
Path: `~/PCM/PCM/`

An operational layer for the PCM workflow — holds ingest pipeline configuration, AI conversation exports, and Obsidian-ready distilled output. Its `moc/` directory mirrors the same structure as the KnowledgeVault but starts empty.

Key directories:
- `moc/` — same role as in the KnowledgeVault
- `lcc/` — a symlink to the canonical `~/KnowledgeVault/PKM/lcc/`; either path works for lookups
- `home.md` — currently contains only quick links to directories; add a `## Maps of Content` section if one does not already exist

Template: `templates/moc-note-template.md` — identical to the KnowledgeVault's:
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

## Child MOCs

None yet.

## Notes

- [[]]

## Related MOCs

- [[]]
```

## Naming Rules (both vaults)

- **Filename**: lowercase, hyphen-separated, no spaces. Derived from the subject name. Example: "Compute Infrastructure" → `compute-infrastructure.md`
- **Title, aliases, classification labels, and display names in home.md** may use normal capitalization, spaces, and punctuation
- **File must live in** `moc/`

## Hierarchy alignment — one logical operation

The PKM and PCM vaults share **one** MOC hierarchy, and
`~/Projects/private/knowledge-management-practice/maps/moc-map.md` is its canonical copy. The
rules and the procedure are not restated here. They are defined in
`~/Projects/private/knowledge-management-practice/practices/moc-hierarchy-alignment.md`, and the `moc-op` command enforces them:

```bash
MOC_OP=~/Projects/private/knowledge-management-practice/scripts/moc-op.sh
```

This skill runs that procedure:

- **Preflight** — `bash $MOC_OP begin` runs before any file is written (Step 6). It fetches all
  three repositories, refuses unsafe local state, and requires the three maps to agree. If it
  fails, stop: show its report and create nothing.
- **Apply** — write the MOC in **both** vaults and update `home.md` in both vaults. Never one vault only.
- **Validate, stage, integrate, verify** — `bash $MOC_OP finish` (Step 11) regenerates both
  vault maps with `create-moc-map.py --strict`, requires them to be identical, writes the
  canonical map from them, commits each repository with a shared `MOC-Operation` trailer,
  pushes PKM → PCM → canonical, and verifies that all three remote maps agree.
- **Complete** only on `MOC-OP-RESULT OK`. Any other result is reported as it stands, never as
  success.

Do not edit any `moc-map.md` by hand, do not `git add`/`commit`/`push` the MOC paths yourself,
and never reconcile a difference by choosing one vault as the authority. The choosers read
PKM's `moc/`; the preflight guarantees both vaults hold the same hierarchy, so that is the
shared one. Max depth is three levels.

## Unattended parameterized invocation

This skill is normally interactive. When it is invoked **headlessly by
`scripts/moc-navigator.py`** in the PCM repo (via `claude -p`), it runs UNATTENDED with
parameters supplied in the prompt. In that mode, follow these rules instead of the
interactive prompts in the numbered Instructions:

- **No questions.** Do not pause for human input at any step. The root directive's
  confirmation requirement is waived for this automated invocation — it declares itself
  unattended/headless, equivalent to a systemd context.
- **Skip the terminal tab naming** (before Step 1 and in Step 13) — this runs headlessly
  from a script, not in Kevin's own interactive terminal.
- **Parameters** (read from the invoking prompt):
  - `MOC_NAME` — the subject of the MOC. Use it as `SUBJECT` (Step 1).
  - `DISPLAY_TITLE` — the title/link text (Step 2). If absent, title-case `MOC_NAME`.
  - (A first-level MOC has no parent.)
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 3.
- **Duplicate check (Step 3) is never skipped.** If `km-moc-dupcheck` exits `1` or `2`, do
  not ask and do not create anything. Report its output, and finish with
  `MOC-FAILED <slug> none`.
- **LCC classification (Steps 4–5)** — perform the lookup, then **auto-select the single
  best-matching class without asking.** If genuinely ambiguous, pick the most likely and
  state the choice in the final report; do not block. Apply the verification rule in Step 5
  to any code the local outline does not list. If that code cannot be confirmed, use the most
  specific confirmed class and state this in the final report.
- **Execute Steps 6–13 exactly as written** — create both vault files, update both
  `home.md` files, and finish the operation (Step 11).
- **Step 11 (finishing the operation) is never skipped.** If the result is anything other
  than `MOC-OP-RESULT OK`, do not retry by editing files; stop and report it.
- **Skip Steps 14–15** (the interactive offers to create a second-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line **only** when Step 11 ended with `MOC-OP-RESULT OK`. Otherwise print
  `MOC-FAILED <slug> <operation-id>` (`none` if no operation was opened). The navigator
  also confirms the result itself with `moc-op check --expect-slug <slug>`.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions below as usual.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name MOC`. If the command is not on `PATH`, skip this step silently.

1. **Ask for subject name** — Ask the human: "What is the subject of this MOC?" Wait for their answer before proceeding.

2. **Ask for display title and link text** — Ask: "How should the title and link name appear in home.md for each vault? (For example: `[[linux|Linux]]` uses `Linux` as the display text.)" Wait for their answer.

3. **Determine the filename slug** — Convert the subject name to a lowercase, hyphen-separated slug. Example: "Compute Infrastructure" → `compute-infrastructure`. This will be the filename in both vaults: `moc/<slug>.md`.

   Then check the canonical MOC map for duplicates, before anything else:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/km-moc-dupcheck.sh --title "<Display Title>" --slug <slug>
   ```

   It compares the title and the slug with every MOC in the map, at every level, because all
   MOC files share one `moc/<slug>.md` namespace. It matches exact titles and slugs, and also
   titles and slugs that differ only in case, accents, punctuation, whitespace, hyphens, or
   `&` versus `and`. It only reads.

   - **Exit `0`** (`NO-DUPLICATE`): continue to Step 4 at once, without asking anything.
   - **Exit `1`**: each output line is `MATCH<TAB><kind><TAB><level><TAB><slug><TAB><title>`.
     Show each match as `<title> (<slug>, level <level>, <kind>)` and ask: "This may duplicate
     an existing MOC. Do you want to reuse it, or give a different name?"
     - **Reuse:** create nothing, open no operation, and stop, naming the existing MOC and its
       file.
     - **Different name:** return to Step 1 with the new name, and run this check again.

     Never create the MOC while a match stands. Never overwrite an existing MOC.
   - **Exit `2`**: the check could not run. Report its stderr and stop. A first-level MOC is
     never created without this check.

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

   **Verify any code the local outline does not list.** The outline stops at broad ranges. Before proposing or assigning a more specific code, check it against the full Library of Congress schedule. If the schedule is not available, use the call numbers on matching records in the LC Catalog (https://catalog.loc.gov/). Never assign such a code from memory. Tell the human which source confirmed it. If it cannot be confirmed, say so and offer only confirmed classes.

   Ask: "Which LCC classification best matches your intent? [list candidates with codes and labels]" Wait for confirmation before continuing.

6. **Get today's date and open the MOC operation** — Run `date +%Y-%m-%d`. Then run the
   preflight, which opens the operation, before writing any file:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh begin --slug <slug> --description "first-level MOC <slug>"
   ```

   Before running it, confirm `moc/<slug>.md` exists in **neither** vault. If it exists in
   either, stop: this is not a new MOC (and if it exists in only one, the vaults have
   diverged, which the preflight will also report).

   Record the operation id from its `MOC-OP preparing <id>` line. If the output does not end
   with `MOC-OP-RESULT OK`, **stop**: show the human its report (it names each MOC that differs
   and each repository involved), create nothing, and go no further. If this run stops for any
   other reason after this point and before Step 11, run
   `bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh abandon --op <id>` and tell the human which files were left in place.

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

8. **Create the PCM MOC file** — Write `~/PCM/PCM/moc/<slug>.md` using the PCM template. Use the same title, date, and classification fields as the KnowledgeVault file. The PCM template already carries these fields, so this is the shape to fill in, not fields to add:
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

9. **Update KnowledgeVault home.md** — Open `~/KnowledgeVault/PKM/home.md`. Add a new entry under `## Maps of Content` in the format:
   ```
   - [[<slug>|<Display Title>]]
   ```
   where `<slug>` is the filename without `.md` and `<Display Title>` is what the human specified. Keep the list alphabetically ordered or append at the end if ordering is unclear.

10. **Update PCM home.md** — Open `~/PCM/PCM/home.md`. If a `## Maps of Content` section already exists, add:
    ```
    - [[<slug>|<Display Title>]]
    ```
    If no `## Maps of Content` section exists, add one after `## Quick Links`:
    ```markdown
    ## Maps of Content

    - [[<slug>|<Display Title>]]
    ```

11. **Finish the operation** — validate, commit, push in order and verify, in one call:

    ```bash
    bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh finish --op <id> \
      --message "moc: add <slug> first-level MOC" --expect-slug <slug>
    ```

    It commits only the MOC paths: `moc/`, `home.md` and `moc-map.md` in each vault, and
    `maps/moc-map.md` in knowledge-management-practice. PKM's pre-commit hook still regenerates
    and stages `toc.md`, `index.md` and `runbooks/index.md` in the PKM commit; that is expected.

12. **Act on the result** — read the final `MOC-OP-RESULT` line:
    - **`OK`** — the MOC is on `origin/main` in both vaults and the three maps agree. Continue.
    - **`FAILED` at validation** — the two vault maps differ, or `--strict` failed. Nothing was
      committed. Show the report, correct the named MOC in the named vault so both match, and
      run the same `finish` command again.
    - **`FAILED` or `INTEGRATING` after committing** — some repositories have the operation and
      some do not. Show the report: it lists the repositories that advanced, those pending, and
      the cause. Once the cause is fixed, `bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh resume --op <id>` continues safely and never
      duplicates a commit.
    - **`BLOCKED`** — show the reason and stop.

    Never report the MOC as created unless the result is `OK`. Never reset, force-push, or
    edit a map by hand to make the check pass.

13. **Report completion** — Summarize:
    - Files created: list both full paths
    - LCC classification applied: code + label
    - home.md entries added: show the exact lines added in each file
    - Operation: the id and its final `MOC-OP-RESULT`
    - Commits: each repository's commit and push state, from `bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh status --op <id>`

    After reporting, close the tab: if `set-ghostty-tab-name` was run in the step before Step 1, run `set-ghostty-tab-name MOCc`.

14. **Offer to create a second-level MOC** — After the completion summary, ask the human: "Do you want to create a second-level MOC under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `second-moc-level` skill at `~/.claude/skills/knowledge-second-moc-level/SKILL.md` — read that file and follow its Instructions section from Step 1 (the parent chooser). The MOC just created here will appear in that chooser as an eligible parent.
    - **If no**: continue to Step 15.

15. **Offer to create a note under this MOC** — Ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If no**: stop. The skill is complete.
    - **If yes**: ask which vault the note belongs in — "Which vault should this note live in: **PCM** or **PKM**? (A note lives in only one vault; MOCs may exist in both.)" Then execute the matching note skill, using **this first-level MOC as the target MOC** for the note:
      - **PCM** → `~/.claude/skills/knowledge-create-a-pcm-note/SKILL.md`
      - **PKM** → `~/.claude/skills/knowledge-create-a-pkm-note/SKILL.md`

      Read that file and follow its Instructions, but **skip its MOC chooser chain** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
      - `deepest_slug` = this MOC's `<slug>`
      - `deepest_title` = this MOC's display title
      - `deepest_cls` = this MOC's `classification`
      - `deepest_lbl` = this MOC's `classification_label`

      Then continue from the note skill's "ask for the note title" step onward. The note will inherit this MOC's LCC classification and be linked back into its `## Notes` section in the chosen vault.

## Success Criteria

- `~/KnowledgeVault/PKM/moc/<slug>.md` exists with correct YAML frontmatter including `classification`, `classification_label`, and `classification_source: lcc`
- `~/PCM/PCM/moc/<slug>.md` exists with the same frontmatter fields
- Both `home.md` files contain a new `[[<slug>|<Display Title>]]` link
- `moc-op finish` ended with `MOC-OP-RESULT OK`: the MOC is on `origin/main` in PKM, PCM and
  the canonical map, and the three maps agree line for line
- Filename is lowercase, hyphen-separated, no spaces, ends in `.md`
- `type: moc` is set in both files
- `created` and `updated` are set to today's date in `YYYY-MM-DD` format

## Notes

- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/PCM/lcc/` is a symlink to it, so either path works for classification lookups
- When the subject is ambiguous (e.g. "tools", "radio", "security"), always surface the ambiguity before choosing a classification — do not guess
- The `primary_moc` field in the KnowledgeVault template is left blank for first-level MOCs; second-level MOCs (child MOCs) would set this to their parent
- If the `.gitkeep` file is the only file in `moc/` of the PCM vault, it can remain in place — git will still track the directory with real content present
- Related skills: `second-moc-level` (for child MOCs), `third-moc-level` (for leaf MOCs), `create-a-pcm-note` / `create-a-pkm-note` (for individual notes, one per vault)
