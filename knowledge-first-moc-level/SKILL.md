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
PKM vault's MOC map automatically (`km-moc-dupcheck --map`), which includes MOCs created
locally and not yet published. It asks the human something only when a possible duplicate
turns up.

## Prerequisites

- `~/Projects/private/knowledge-management-practice` cloned (it provides `km-moc-dupcheck`).
  No push access is needed: this skill creates the MOC locally and commits nothing
- `~/KnowledgeVault/PKM/` (or the `PKM_VAULT` supplied) must exist and contain a `lcc/` directory with LCC outline files (`lcco-a.md` through `lcco-z.md`)
- `~/PCM/PCM/` (or the `PCM_VAULT` supplied) must exist
- Each vault's `scripts/create-moc-map.sh` (it regenerates that vault's `moc-map.md`)
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

An operational layer for the PCM workflow — holds ingest pipeline configuration, AI conversation exports, and Obsidian-ready distilled output. Its `moc/` directory holds the same MOC hierarchy as the KnowledgeVault.

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

## Local creation — the default

"Create a MOC" means **create it locally** (AI-148). The MOC is written in **both** vaults,
the navigation is updated, each vault's `moc-map.md` is regenerated with that vault's own
script, and the result is verified as reachable in both vaults. Everything is left **unstaged
and uncommitted**. Creation is complete at that point.

Publishing (committing and pushing PKM and PCM, and updating the shared reference map
`~/Projects/private/knowledge-management-practice/maps/moc-map.md`) is a **separate action Kevin
requests explicitly**. Publishing MOCs that were created locally is pending work under PKM-98.
This skill never runs `moc-op begin` or `moc-op finish`, never runs `git add`, `git commit` or
`git push`, and never touches the shared reference map.

Local creation works when:

- other edits are pending in either vault, including in `moc/` (for example in
  `PCM/moc/uncategorized.md`) — they are never staged, reverted or rewritten;
- earlier MOCs were created locally and are still uncommitted — they are part of the local
  hierarchy, and the next MOC builds on them;
- the shared reference map lags behind the vault maps.

The rules that still hold:

- **Both vaults, always.** Never create a MOC in one vault only, and never pick one vault as
  the authority when they disagree. If their maps differ, stop and report it.
- **The vault maps are the hierarchy.** The duplicate check reads
  `$PKM_VAULT/moc-map.md` (`--map`), not the shared reference map, so a locally created MOC is
  seen. The preflight (Step 6) proves the two vault maps are identical, so PKM's is the shared one.
- **Maps are generated, never hand-edited.** Each vault's `moc-map.md` is rewritten only by
  `<vault>/scripts/create-moc-map.sh --strict`, which always targets its own vault.
- **Edit only what this MOC needs.** The new `moc/<slug>.md`, one line in `home.md`, and the
  regenerated `moc-map.md` in each vault. Nothing else.
- Max depth is three levels.

### Vault locations

| Variable | Default | Repository root |
|----------|---------|-----------------|
| `PKM_VAULT` | `~/KnowledgeVault/PKM` | its parent directory (`~/KnowledgeVault`) |
| `PCM_VAULT` | `~/PCM/PCM` | its parent directory (`~/PCM`) |

The commands below use these variables. Interactively, use the defaults. A caller (the
navigator, or a test) may supply other paths, such as disposable copies. When it does, use
them everywhere, and never fall back to the live vaults.

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
  - `PKM_VAULT`, `PCM_VAULT` — the vault paths (see *Vault locations*). If absent, use the
    defaults.
  - (A first-level MOC has no parent.)
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 3.
- **Duplicate check (Step 3) is never skipped.** If `km-moc-dupcheck` exits `1` or `2`, do
  not ask and do not create anything. Report its output, and finish with
  `MOC-FAILED <slug>`.
- **LCC classification (Steps 4–5)** — perform the lookup, then **auto-select the single
  best-matching class without asking.** If genuinely ambiguous, pick the most likely and
  state the choice in the final report; do not block. Apply the verification rule in Step 5
  to any code the local outline does not list. If that code cannot be confirmed, use the most
  specific confirmed class and state this in the final report.
- **Execute Steps 6–13 exactly as written** — the local preflight, both vault files, both
  `home.md` files, the map regeneration and the verification.
- **Step 12 (verification) is never skipped.** If any check fails, do not retry by editing
  other files; stop and report it.
- **Skip Steps 14–15** (the interactive offers to create a second-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line **only** when every Step 12 check passed. Otherwise print `MOC-FAILED <slug>`. The
  navigator repeats the local reachability check itself before it reports success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions below as usual.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name MOC`. If the command is not on `PATH`, skip this step silently.

1. **Ask for subject name** — Ask the human: "What is the subject of this MOC?" Wait for their answer before proceeding.

2. **Ask for display title and link text** — Ask: "How should the title and link name appear in home.md for each vault? (For example: `[[linux|Linux]]` uses `Linux` as the display text.)" Wait for their answer.

3. **Determine the filename slug** — Convert the subject name to a lowercase, hyphen-separated slug. Example: "Compute Infrastructure" → `compute-infrastructure`. This will be the filename in both vaults: `moc/<slug>.md`.

   Then check the local MOC hierarchy for duplicates, before anything else:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/km-moc-dupcheck.sh \
     --map "$PKM_VAULT/moc-map.md" --title "<Display Title>" --slug <slug>
   ```

   `--map` points it at the vault map, so MOCs created locally and not yet published are
   included. It compares the title and the slug with every MOC in the map, at every level,
   because all MOC files share one `moc/<slug>.md` namespace. It matches exact titles and
   slugs, and also titles and slugs that differ only in case, accents, punctuation,
   whitespace, hyphens, or `&` versus `and`. It only reads.

   - **Exit `0`** (`NO-DUPLICATE`): continue to Step 4 at once, without asking anything.
   - **Exit `1`**: each output line is `MATCH<TAB><kind><TAB><level><TAB><slug><TAB><title>`.
     Show each match as `<title> (<slug>, level <level>, <kind>)` and ask: "This may duplicate
     an existing MOC. Do you want to reuse it, or give a different name?"
     - **Reuse:** create nothing and stop, naming the existing MOC and its file.
     - **Different name:** return to Step 1 with the new name, and run this check again.

     Never create the MOC while a match stands. Never overwrite an existing MOC.
   - **Exit `2`**: the check could not run. Report its stderr and stop. A first-level MOC is
     never created without this check.

4. **Search the LCC catalog** — Read the LCC outline files in `$PKM_VAULT/lcc/`. The files are named `lcco-a.md`, `lcco-b.md`, ..., `lcco-z.md` and contain the Library of Congress Classification hierarchy. Search for classes that plausibly match the subject. Common top-level classes:
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

6. **Get today's date and run the local preflight** — Run `date +%Y-%m-%d`. Then, before
   writing any file:

   ```bash
   PKM_REPO=$(dirname "$PKM_VAULT"); PCM_REPO=$(dirname "$PCM_VAULT")
   test ! -e "$PKM_VAULT/moc/<slug>.md" && test ! -e "$PCM_VAULT/moc/<slug>.md"
   bash "$PKM_VAULT/scripts/create-moc-map.sh" --check --strict
   bash "$PCM_VAULT/scripts/create-moc-map.sh" --check --strict
   cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
   git -C "$PKM_REPO" diff --cached --name-only; git -C "$PCM_REPO" diff --cached --name-only
   ```

   - **The slug exists in either vault:** stop. This is not a new MOC. If it exists in only
     one vault, the vaults have diverged; report that too.
   - **A map is stale** (`--check` fails): something already pending changed the hierarchy
     without regenerating the map. Stop and report the vault. Do not regenerate it here,
     because that would fold an unrelated change into this MOC.
   - **The two maps differ** (`cmp` fails): the vaults disagree about the hierarchy. Stop and
     report the difference (`diff` the two maps). Never resolve it by choosing one vault.
   - **Something is already staged** in either repository: record the list. This skill stages
     nothing, so the same list must still be staged, and nothing more, at Step 12.

   Pending unstaged edits and a lagging shared reference map are expected. Neither is a reason
   to stop.

7. **Create the KnowledgeVault MOC file** — Write `$PKM_VAULT/moc/<slug>.md` using the KnowledgeVault template.
   Start from the vault's own `templates/moc-note-template.md` (read the file; the copy in the
   Background above is for orientation and may be out of date). Keep every section and comment
   line it has, including `## Child MOCs` with `None yet.`, and write lists in block style
   (`tags:` then `  - moc`), never `["moc"]`.

   Fill in:
   - `title`: the display title the human provided (or a sensible title from the subject name)
   - `aliases`: `["moc <title>"]` — lowercase alias
   - `type`: `moc`
   - `classification`: the confirmed LCC code (e.g. `T`, `QA76`, `R`)
   - `classification_label`: the LCC class label (e.g. `"Technology"`, `"Computer science"`, `"Medicine"`)
   - `classification_source`: `lcc`
   - `primary_moc`: leave blank (this is itself a first-level MOC)
   - `related_mocs`: `[]`, or the slugs of any related MOCs the human named (each must exist in both vaults)
   - `tags`: a block list with `moc`
   - `created`: today's date
   - `updated`: today's date
   - Body: fill `# <title> MOC` heading; write a one-sentence overview describing what the map covers

8. **Create the PCM MOC file** — Write `$PCM_VAULT/moc/<slug>.md` using the PCM template. Use the same title, date, and classification fields as the KnowledgeVault file. The PCM template already carries these fields, so this is the shape to fill in, not fields to add:
   ```yaml
   ---
   title: "..."
   aliases:
     - "moc ..."
   type: moc
   classification: ...
   classification_label: "..."
   classification_source: lcc
   primary_moc:
   related_mocs: []
   tags:
     - moc
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---
   ```
   Body: same heading and overview as the KnowledgeVault file.

9. **Update KnowledgeVault home.md** — Open `$PKM_VAULT/home.md`. Add a new entry under `## Maps of Content` in the format:
   ```
   - [[<slug>|<Display Title>]]
   ```
   where `<slug>` is the filename without `.md` and `<Display Title>` is what the human specified. Insert it directly after the last `- [[` entry of that section. The list is not kept alphabetical, so do not reorder it. Change no other line.

10. **Update PCM home.md** — Open `$PCM_VAULT/home.md`. If a `## Maps of Content` section already exists, add the line after its last `- [[` entry, exactly as in Step 9:
    ```
    - [[<slug>|<Display Title>]]
    ```
    If no `## Maps of Content` section exists, add one after `## Quick Links`:
    ```markdown
    ## Maps of Content

    - [[<slug>|<Display Title>]]
    ```

11. **Regenerate each vault's map** — with that vault's own script (it defaults to its own vault, so it runs from any directory):

    ```bash
    bash "$PKM_VAULT/scripts/create-moc-map.sh" --strict
    bash "$PCM_VAULT/scripts/create-moc-map.sh" --strict
    git -C "$PKM_REPO" diff -- "$PKM_VAULT/moc-map.md"; git -C "$PCM_REPO" diff -- "$PCM_VAULT/moc-map.md"
    ```

    Because Step 6 proved both maps were current, the only new lines are this MOC's, plus any
    earlier local MOCs that are already in the map. Do not edit `moc-map.md` by hand.

12. **Verify** — every check must pass:

    ```bash
    for v in "$PKM_VAULT" "$PCM_VAULT"; do
      grep -Fx -- "- **1** [[<slug>|<Display Title>]]" "$v/moc-map.md"
      grep -F -- "[[<slug>|" "$v/home.md"
      grep -F -- "[[moc-map|" "$v/home.md"
    done
    cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
    git -C "$PKM_REPO" diff --cached --name-only; git -C "$PCM_REPO" diff --cached --name-only
    ```

    - The map line is the MOC's level-1 entry, and `home.md` links both the MOC and the MOC
      Map (`[[moc-map|…]]`), so the MOC is reachable from each vault's map.
    - The two maps are identical.
    - The staged lists equal the ones recorded in Step 6. Normally both are empty.
    - Every edit that was pending before Step 6 is still there, unchanged.
      `git -C <repo> status --short` lists the new MOC files and this run's
      `home.md`/`moc-map.md` changes alongside them.

    If any check fails, report which one and stop. Do not commit to "fix" it.

13. **Report completion** — Summarize:
    - Files created: list both full paths
    - LCC classification applied: code + label
    - home.md entries added: show the exact lines added in each file
    - Map lines added: the new line in each `moc-map.md`
    - Verification: each Step 12 check and its result
    - State plainly that everything is unstaged and uncommitted, that the shared reference map
      was not changed, and that publishing is a separate request (PKM-98)

    After reporting, close the tab: if `set-ghostty-tab-name` was run in the step before Step 1, run `set-ghostty-tab-name MOCc`.

14. **Offer to create a second-level MOC** — After the completion summary, ask the human: "Do you want to create a second-level MOC under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `second-moc-level` skill at `~/.claude/skills/knowledge-second-moc-level/SKILL.md` — read that file and follow its Instructions section from Step 1 (the parent chooser). The MOC just created here appears in that chooser as an eligible parent, because the chooser reads the vault map.
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

- `$PKM_VAULT/moc/<slug>.md` exists with correct YAML frontmatter including `classification`, `classification_label`, and `classification_source: lcc`
- `$PCM_VAULT/moc/<slug>.md` exists with the same frontmatter fields
- Both `home.md` files contain a new `[[<slug>|<Display Title>]]` link
- Both `moc-map.md` files were regenerated by their own script, contain `- **1** [[<slug>|<Display Title>]]`, and are identical
- Nothing new is staged or committed in either repository, every edit pending before the run is intact, and the shared reference map is unchanged
- Filename is lowercase, hyphen-separated, no spaces, ends in `.md`
- `type: moc` is set in both files
- `created` and `updated` are set to today's date in `YYYY-MM-DD` format

## Notes

- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/PCM/lcc/` is a symlink to it, so either path works for classification lookups
- When the subject is ambiguous (e.g. "tools", "radio", "security"), always surface the ambiguity before choosing a classification — do not guess
- The `primary_moc` field in the KnowledgeVault template is left blank for first-level MOCs; second-level MOCs (child MOCs) would set this to their parent
- If the `.gitkeep` file is the only file in `moc/` of the PCM vault, it can remain in place — git will still track the directory with real content present
- Publishing a locally created MOC is a separate request; the workflow for it is PKM-98. Until it is published, `moc-op begin` refuses to start, because the vault maps are ahead of the shared reference map. That is expected, and it does not affect local creation
- Related skills: `second-moc-level` (for child MOCs), `third-moc-level` (for leaf MOCs), `create-a-pcm-note` / `create-a-pkm-note` (for individual notes, one per vault)
