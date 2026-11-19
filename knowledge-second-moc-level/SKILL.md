---
name: knowledge-second-moc-level
category: knowledge
description: Creates a second-level Map of Content (MOC) nested under a human-selected first-level parent, asking for a subtopic within that subject, then classifying and writing the MOC in both vaults.
disable-model-invocation: true
---

# Create Second-Level MOC

> Runs a Python chooser to select a first-level parent MOC, then asks for a subtopic or focus area within that subject, looks up a deeper LCC classification if one exists, and writes the second-level MOC in both knowledge vaults.

## How This Skill Chains

The Python chooser is **Step 1 of this skill** — it runs inline via `python3`, Claude captures its output, presents the numbered list to the human, and the human picks a number. There is no separate launcher. The entire flow — chooser → subtopic question → LCC lookup → file creation — happens in one sequential Claude session. The skill's parameter (the parent MOC) is resolved at runtime through the chooser, not passed in advance.

## Prerequisites

- `~/Projects/private/knowledge-management-practice` cloned (it provides `moc-op` and the
  canonical map), and push access to the PKM, PCM and knowledge-management-practice repositories
- Both vaults hold the same MOC hierarchy, with at least one first-level MOC (the Step 7 preflight checks this)
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
  - "tools"
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
primary_moc: compute-cloud-hosting
related_mocs:
  - "compute-cloud-hosting"
tags:
  - moc
created: 2026-06-15
updated: 2026-06-15
```

### Vault 2 — Personal Context Management (private)
Path: `~/PCM/PCM/`

- `moc/` — mirrors the KnowledgeVault; may be empty or partial
- `lcc/` — `~/PCM/PCM/lcc/` is a symlink to the canonical `~/KnowledgeVault/PKM/lcc/`; either path works for lookups
- `home.md` — **do not modify**

Template (`templates/moc-note-template.md`) — identical to the KnowledgeVault's. It already
carries the classification fields, `primary_moc`, and a `## Child MOCs` section, so there is
nothing extra to add:
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

### Naming Rules

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Compute Cloud Hosting" → `compute-cloud-hosting.md`
- **Frontmatter values** (title, labels, aliases): normal capitalization and spaces are fine
- **Files must live in** `moc/`

## Hierarchy alignment — one logical operation

The PKM and PCM vaults share **one** MOC hierarchy, and
`~/Projects/private/knowledge-management-practice/maps/moc-map.md` is its canonical copy. The
rules and the procedure are not restated here. They are defined in
`~/Projects/private/knowledge-management-practice/practices/moc-hierarchy-alignment.md`, and the `moc-op` command enforces them:

```bash
MOC_OP=~/Projects/private/knowledge-management-practice/scripts/moc-op.sh
```

This skill runs that procedure:

- **Preflight** — `bash $MOC_OP begin` runs before any file is written (Step 7). It fetches all
  three repositories, refuses unsafe local state, and requires the three maps to agree. If it
  fails, stop: show its report and create nothing.
- **Apply** — write the MOC in **both** vaults and wire the parent's `## Child MOCs` in both vaults. Never one vault only.
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

- **No questions.** Do not pause for human input. The root directive's confirmation
  requirement is waived for this automated invocation — it declares itself unattended.
- **Skip the terminal tab naming** (before Step 1 and in Step 13) — this runs headlessly
  from a script, not in Kevin's own interactive terminal.
- **Parameters** (read from the invoking prompt):
  - `MOC_NAME` — the subtopic. Use it as `SUBTOPIC` (Step 3).
  - `DISPLAY_TITLE` — the title/link text (Step 4). If absent, title-case `MOC_NAME`.
  - `PARENT_SLUG` — the **first-level** parent MOC's filename slug.
- **Skip Step 1 (the parent chooser).** The parent is `PARENT_SLUG`; read its frontmatter
  per Step 2 (title, classification, classification_label).
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 5.
- **LCC classification (Step 6)** — search for a deeper class, then **auto-select the best
  match without asking**, reusing the parent's classification if none clearly fits. Do not
  block on ambiguity. Apply the verification rule in Step 6 to any code the local outline does
  not list. If that code cannot be confirmed, use the most specific confirmed class or the
  parent's class, and state this in the final report.
- **Execute Steps 7–13 exactly as written** — create both vault files, update the parent MOC in both vaults, and finish the operation (Step 11). Do **not** modify `home.md`.
- **Step 11 (finishing the operation) is never skipped.** If the result is anything other
  than `MOC-OP-RESULT OK`, do not retry by editing files; stop and report it.
- **Skip Steps 14–15** (the interactive offers to create a third-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line **only** when Step 11 ended with `MOC-OP-RESULT OK`. Otherwise print
  `MOC-FAILED <slug> <operation-id>` (`none` if no operation was opened). The navigator
  also confirms the result itself with `moc-op check --expect-slug <slug>`.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions below as usual.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name MOC`. If the command is not on `PATH`, skip this step silently.

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

   **Verify any code the local outline does not list.** The outline stops at broad ranges. Before proposing or assigning a more specific code, check it against the full Library of Congress schedule. If the schedule is not available, use the call numbers on matching records in the LC Catalog (https://catalog.loc.gov/). Never assign such a code from memory. Tell the human which source confirmed it. If it cannot be confirmed, say so and offer only confirmed classes.

   Call out ambiguities explicitly before confirming. Example: "lawn tools" could be TJ (Mechanical machinery) or SB (Plant culture) or TT (Handicrafts). Ask: "Which classification best matches your intent: [list candidates]?" Wait for confirmation.

7. **Get today's date and open the MOC operation** — Run `date +%Y-%m-%d`. Then run the
   preflight, which opens the operation, before writing any file:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh begin --slug <slug> --description "second-level MOC <slug>"
   ```

   Before running it, confirm `moc/<slug>.md` exists in **neither** vault. If it exists in
   either, stop: this is not a new MOC (and if it exists in only one, the vaults have
   diverged, which the preflight will also report).

   Record the operation id from its `MOC-OP preparing <id>` line. If the output does not end
   with `MOC-OP-RESULT OK`, **stop**: show the human its report (it names each MOC that differs
   and each repository involved), create nothing, and go no further. If this run stops for any
   other reason after this point and before Step 11, run
   `bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh abandon --op <id>` and tell the human which files were left in place.

8. **Create the KnowledgeVault MOC file** — Write `~/KnowledgeVault/PKM/moc/<slug>.md`:
   - `title`: the display title
   - `aliases`: `["moc <title lowercase>"]`
   - `type`: `moc`
   - `classification`: the confirmed LCC code (deeper if found, or reused from parent)
   - `classification_label`: the LCC label
   - `classification_source`: `lcc`
   - `primary_moc`: the parent's slug (e.g. `tools`)
   - `related_mocs`: list with the parent's **slug**, quoted (e.g. `- "tools"`) — not its display title
   - `tags`: `["moc"]`
   - `created` / `updated`: today's date
   - Body, in this order (`rules/moc-section-order.md`): `# <title> MOC`, `## Overview` with a
     one-sentence description of what subdivision this covers, `## Child MOCs` with `None yet.`,
     `## Notes` with `- [[]]`, then `## Related MOCs` linking back to the parent

9. **Create the PCM MOC file** — Write `~/PCM/PCM/moc/<slug>.md` with the same content. The PCM
   template already carries these fields, so this is the shape to fill in, not fields to add:
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
     - "<parent-slug>"
   tags:
     - moc
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---
   ```

10. **Update the parent MOC in both vaults** — In each vault, open `moc/<parent-slug>.md`:
    - Find the section named `## Child MOCs`, `## Second-level MOCs`, or similar. If no such
      section exists, add one immediately **before `## Notes`** — `rules/moc-section-order.md` in
      the PCM vault fixes the order as Overview → Child MOCs → Notes → Related MOCs, and it takes
      precedence over any other placement.
    - Append: `- [[<slug>|<Display Title>]]`
    - Update the `updated:` frontmatter field to today's date.

11. **Finish the operation** — validate, commit, push in order and verify, in one call:

    ```bash
    bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh finish --op <id> \
      --message "moc: add <slug> second-level MOC under <parent-slug>" --expect-slug <slug>
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

13. **Report completion** — State:
    - Files created: both full paths
    - Parent updated: both full paths, with the exact line added
    - Classification applied: code + label (note if reused from parent or if a deeper one was found)
    - Operation: the id and its final `MOC-OP-RESULT`
    - Commits: each repository's commit and push state, from `bash ~/Projects/private/knowledge-management-practice/scripts/moc-op.sh status --op <id>`

    After reporting, close the tab: if `set-ghostty-tab-name` was run in the step before Step 1, run `set-ghostty-tab-name MOCc`.

14. **Offer to create a third-level MOC** — After the completion summary, ask the human: "Do you want to create a third-level MOC under **[this MOC's Display Title]**?" Wait for their answer.
    - **If yes**: execute the `third-moc-level` skill at `~/.claude/skills/knowledge-third-moc-level/SKILL.md` — read that file and follow its Instructions section from Step 1. The second-level MOC just created here will appear as an eligible parent.
    - **If no**: continue to Step 15.

15. **Offer to create a note under this MOC** — Ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If no**: stop. The skill is complete.
    - **If yes**: ask which vault the note belongs in — "Which vault should this note live in: **PCM** or **PKM**? (A note lives in only one vault; MOCs may exist in both.)" Then execute the matching note skill, using **this second-level MOC as the target MOC** for the note:
      - **PCM** → `~/.claude/skills/knowledge-create-a-pcm-note/SKILL.md`
      - **PKM** → `~/.claude/skills/knowledge-create-a-pkm-note/SKILL.md`

      Read that file and follow its Instructions, but **skip its MOC chooser chain** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
      - `deepest_slug` = this MOC's `<slug>`
      - `deepest_title` = this MOC's display title
      - `deepest_cls` = this MOC's `classification`
      - `deepest_lbl` = this MOC's `classification_label`

      Then continue from the note skill's "ask for the note title" step onward. The note will inherit this MOC's LCC classification and be linked back into its `## Notes` section in the chosen vault.

## Success Criteria

- `~/KnowledgeVault/PKM/moc/<slug>.md` exists with `primary_moc` set to the parent slug and `classification` filled
- `~/PCM/PCM/moc/<slug>.md` exists with the same frontmatter
- Parent MOC in both vaults contains `[[<slug>|<Display Title>]]` in a child section
- `moc-op finish` ended with `MOC-OP-RESULT OK`: the MOC is on `origin/main` in PKM, PCM and
  the canonical map, and the three maps agree line for line
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** — only first-level MOCs are listed there
- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/PCM/lcc/` is a symlink to it, so either path works for lookups
- Reusing the parent's classification is correct and expected when no more specific LCC sub-class fits (e.g. AWS under Compute Cloud Hosting both use T58.5)
- If the parent MOC is missing from either vault, the vaults have diverged and the Step 7 preflight stops. Never create a stub in one vault to get past it; fix the divergence through its own MOC operation first
- Related skills: `first-moc-level` (create the parent first), `third-moc-level` (create a child of this MOC)
