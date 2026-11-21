---
name: knowledge-second-moc-level
category: knowledge
description: Creates a second-level Map of Content (MOC) nested under a human-selected first-level parent, asking for a subtopic within that subject, then classifying and writing the MOC in both vaults.
disable-model-invocation: true
---

# Create Second-Level MOC

> Opens a chooser popup (or, as a fallback, a numbered list) to select a first-level parent MOC, then asks for a subtopic or focus area within that subject, looks up a deeper LCC classification if one exists, and writes the second-level MOC in both knowledge vaults.

## How This Skill Chains

The parent is chosen in **Step 1 of this skill**. Claude runs `km-moc-popup`, which opens the keyboard-driven `km-moc-chooser` in a tmux popup over this pane and hands the validated choice straight back: no copying, pasting or number typing. Where no popup is possible, Step 1 falls back to the inline Python numbered list: Claude presents the list and the human picks a number. There is no separate launcher. The entire flow — chooser → subtopic question → LCC lookup → file creation — happens in one sequential Claude session. The skill's parameter (the parent MOC) is resolved at runtime through the chooser, not passed in advance.

## Prerequisites

- `~/Projects/private/knowledge-management-practice` cloned (it provides `km-moc-popup` and
  `km-moc-chooser`). No push access is needed: this skill creates the MOC locally and commits nothing
- Each vault's `scripts/create-moc-map.sh` (it regenerates that vault's `moc-map.md`)
- Both vaults hold the same MOC hierarchy, with at least one first-level MOC (the Step 7 preflight checks the vaults agree)
- Both vaults must have `templates/moc-note-template.md`
- Python 3 available (`python3`)
- For the chooser popup (optional; without it Step 1 uses the numbered list): the session
  runs inside tmux 3.3+, and Fedora's `python3-urwid` is installed

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `PARENT_MOC` | The first-level MOC this lives under | _(resolved in Step 1: chooser popup, or the numbered-list fallback)_ |
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

- `moc/` — holds the same MOC hierarchy as the KnowledgeVault
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

## Local creation — the default

"Create a MOC" means **create it locally** (AI-148). The MOC is written in **both** vaults,
the parent's `## Child MOCs` is updated in both vaults, each vault's `moc-map.md` is
regenerated with that vault's own script, and the result is verified as reachable in both
vaults. Everything is left **unstaged and uncommitted**. Creation is complete at that point.

Publishing (committing and pushing PKM and PCM, and updating the shared reference map
`~/Projects/private/knowledge-management-practice/maps/moc-map.md`) is a **separate action Kevin
requests explicitly**. Publishing MOCs that were created locally is pending work under PKM-98.
This skill never runs `moc-op begin` or `moc-op finish`, never runs `git add`, `git commit` or
`git push`, and never touches the shared reference map.

Local creation works when:

- other edits are pending in either vault, including in `moc/` (for example in
  `PCM/moc/uncategorized.md`) — they are never staged, reverted or rewritten;
- earlier MOCs were created locally and are still uncommitted — they are part of the local
  hierarchy, can be chosen as parents, and the next MOC builds on them;
- the shared reference map lags behind the vault maps.

The rules that still hold:

- **Both vaults, always.** Never create a MOC in one vault only, and never pick one vault as
  the authority when they disagree. If their maps differ, stop and report it.
- **The vault maps are the hierarchy.** The chooser reads `$PKM_VAULT/moc-map.md` (`--map`),
  not the shared reference map, so a locally created MOC can be chosen as a parent. The
  preflight (Step 7) proves the two vault maps are identical, so PKM's is the shared one.
- **Maps are generated, never hand-edited.** Each vault's `moc-map.md` is rewritten only by
  `<vault>/scripts/create-moc-map.sh --strict`, which always targets its own vault.
- **Edit only what this MOC needs.** The new `moc/<slug>.md`, one line (and the `updated:`
  date) in the parent MOC, and the regenerated `moc-map.md` in each vault. Never `home.md`.
- Max depth is three levels.

### Vault locations

| Variable | Default | Repository root |
|----------|---------|-----------------|
| `PKM_VAULT` | `~/KnowledgeVault/PKM` | its parent directory (`~/KnowledgeVault`) |
| `PCM_VAULT` | `~/PCM/PCM` | its parent directory (`~/PCM`) |

The commands below use these variables. Interactively, use the defaults. A caller (the
navigator, or a test) may supply other paths, such as disposable copies. When it does, use
them everywhere — export both before running any command or the fallback chooser — and never
fall back to the live vaults.

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
  - `PKM_VAULT`, `PCM_VAULT` — the vault paths (see *Vault locations*). If absent, use the
    defaults.
  - `PARENT_SLUG` — the **first-level** parent MOC's filename slug.
- **Skip Step 1 (the parent chooser): open neither the popup nor the numbered list.** The parent is `PARENT_SLUG`; read its frontmatter
  per Step 2 (title, classification, classification_label).
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 5.
- **LCC classification (Step 6)** — search for a deeper class, then **auto-select the best
  match without asking**, reusing the parent's classification if none clearly fits. Do not
  block on ambiguity. Apply the verification rule in Step 6 to any code the local outline does
  not list. If that code cannot be confirmed, use the most specific confirmed class or the
  parent's class, and state this in the final report.
- **Execute Steps 7–13 exactly as written** — the local preflight, both vault files, the parent MOC in both vaults, the map regeneration and the verification. Do **not** modify `home.md`.
- **Step 12 (verification) is never skipped.** If any check fails, do not retry by editing
  other files; stop and report it.
- **Skip Steps 14–15** (the interactive offers to create a third-level MOC or a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line **only** when every Step 12 check passed. Otherwise print `MOC-FAILED <slug>`. The
  navigator repeats the local reachability check itself before it reports success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions below as usual.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name MOC`. If the command is not on `PATH`, skip this step silently.

1. **Choose the parent.** Before asking the human anything, open the chooser popup:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/km-moc-popup.sh --map "$PKM_VAULT/moc-map.md" --depth 1 --title "Parent for the new second-level MOC"
   ```

   `--map` points it at the vault map, so MOCs created locally and not yet published can be
   chosen. It opens `km-moc-chooser` in a tmux popup over this pane, waits while the human picks, and
   prints five validated `KEY=VALUE` lines (`LEVEL`, `FIRST_SLUG`, `FIRST_TITLE`, `SECOND_SLUG`,
   `SECOND_TITLE`). Read them by splitting each line on its **first** `=`. **Never `eval` or
   `source` the output.** Act on the exit code:

   - **`0`**: the parent is `FIRST_SLUG` (title `FIRST_TITLE`; `LEVEL` is always `1` here). Do not
     run the numbered list below. Go to Step 2.
   - **`1`**: the human cancelled. **Stop.** Create nothing, and say the
     run was cancelled.
   - **`2`**: the popup ran but failed. Its stderr says why: a chooser error, a timeout, or a
     missing, malformed, stale or invalid result. Give the human that reason in one line, then
     use the fallback below.
   - **`3`**: no popup is possible here (not in tmux, no attached client, or tmux older than
     3.3). Use the fallback below without comment.

   Its checks and exit codes are documented in
   `~/Projects/private/knowledge-management-practice/scripts/RUNBOOK.md` → Step 6.

   **Fallback: the numbered list.** Run this Python script:

   ```python
   import os, re

   moc_dir = os.path.join(os.path.expanduser(os.environ.get("PKM_VAULT", "~/KnowledgeVault/PKM")), "moc")
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

2. **Read the parent MOC's frontmatter** — Open `$PKM_VAULT/moc/<parent-slug>.md` and extract:
   - `title` — the parent's display title (e.g. "Tools")
   - `classification` — the parent's LCC code (e.g. `T`)
   - `classification_label` — the parent's LCC label (e.g. "Technology")

   These values are the baseline for the new MOC's classification. If the file does not exist,
   stop: the chooser's map and the vault disagree, and the Step 7 preflight would refuse anyway.

3. **Ask for the subtopic** — Ask: "What subtopic, focus area, or subdivision within **[Parent Title]** do you want to map?" Wait for their answer. This becomes the subject of the new second-level MOC.

4. **Ask for the display title** — Ask: "How should this appear as a title and link in the parent MOC? (e.g. `[[outdoor-lawn-and-garden-maintenance|Outdoor Lawn and Garden Maintenance]]`)" Wait for their answer.

5. **Determine the filename slug** — Convert the subtopic to a lowercase, hyphen-separated slug. Example: "Outdoor Lawn and Garden Maintenance" → `outdoor-lawn-and-garden-maintenance`.

6. **Search for a deeper LCC classification** — Read the relevant LCC outline file from `$PKM_VAULT/lcc/` starting from the parent's LCC class letter. Look for a sub-class code that more precisely matches the subtopic.

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

7. **Get today's date and run the local preflight** — Run `date +%Y-%m-%d`. Then, before
   writing any file:

   ```bash
   PKM_REPO=$(dirname "$PKM_VAULT"); PCM_REPO=$(dirname "$PCM_VAULT")
   test ! -e "$PKM_VAULT/moc/<slug>.md" && test ! -e "$PCM_VAULT/moc/<slug>.md"
   test -e "$PKM_VAULT/moc/<parent-slug>.md" && test -e "$PCM_VAULT/moc/<parent-slug>.md"
   bash "$PKM_VAULT/scripts/create-moc-map.sh" --check --strict
   bash "$PCM_VAULT/scripts/create-moc-map.sh" --check --strict
   cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
   git -C "$PKM_REPO" diff --cached --name-only; git -C "$PCM_REPO" diff --cached --name-only
   ```

   - **The slug exists in either vault:** stop. This is not a new MOC. If it exists in only
     one vault, the vaults have diverged; report that too.
   - **The parent is missing from either vault:** stop. The vaults have diverged. Never create
     a stub in one vault to get past it.
   - **A map is stale** (`--check` fails): something already pending changed the hierarchy
     without regenerating the map. Stop and report the vault. Do not regenerate it here,
     because that would fold an unrelated change into this MOC.
   - **The two maps differ** (`cmp` fails): the vaults disagree about the hierarchy. Stop and
     report the difference (`diff` the two maps). Never resolve it by choosing one vault.
   - **Something is already staged** in either repository: record the list. This skill stages
     nothing, so the same list must still be staged, and nothing more, at Step 12.

   Pending unstaged edits and a lagging shared reference map are expected. Neither is a reason
   to stop.

8. **Create the KnowledgeVault MOC file** — Write `$PKM_VAULT/moc/<slug>.md`:
   Start from the vault's own `templates/moc-note-template.md` (read the file; the copy in the
   Background above is for orientation and may be out of date). Keep every section and comment
   line it has, including `## Child MOCs` with `None yet.`, and write lists in block style
   (`tags:` then `  - moc`), never `["moc"]`.

   Fill in:
   - `title`: the display title
   - `aliases`: `["moc <title lowercase>"]`
   - `type`: `moc`
   - `classification`: the confirmed LCC code (deeper if found, or reused from parent)
   - `classification_label`: the LCC label
   - `classification_source`: `lcc`
   - `primary_moc`: the parent's slug (e.g. `tools`)
   - `related_mocs`: list with the parent's **slug**, quoted (e.g. `- "tools"`) — not its display title
   - `tags`: a block list with `moc`
   - `created` / `updated`: today's date
   - Body, in this order (`rules/moc-section-order.md`): `# <title> MOC`, `## Overview` with a
     one-sentence description of what subdivision this covers, `## Child MOCs` with `None yet.`,
     `## Notes` with `- [[]]`, then `## Related MOCs` linking back to the parent

9. **Create the PCM MOC file** — Write `$PCM_VAULT/moc/<slug>.md` with the same content. The PCM
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
    - Add `- [[<slug>|<Display Title>]]`: if the section holds only the `None yet.` placeholder,
      replace that line with the link; otherwise append the link after the last entry.
    - Update the `updated:` frontmatter field to today's date.

11. **Regenerate each vault's map** — with that vault's own script (it defaults to its own vault, so it runs from any directory):

    ```bash
    bash "$PKM_VAULT/scripts/create-moc-map.sh" --strict
    bash "$PCM_VAULT/scripts/create-moc-map.sh" --strict
    git -C "$PKM_REPO" diff -- "$PKM_VAULT/moc-map.md"; git -C "$PCM_REPO" diff -- "$PCM_VAULT/moc-map.md"
    ```

    Because Step 7 proved both maps were current, the only new lines are this MOC's, plus any
    earlier local MOCs that are already in the map. Do not edit `moc-map.md` by hand.

12. **Verify** — every check must pass:

    ```bash
    for v in "$PKM_VAULT" "$PCM_VAULT"; do
      grep -F -- "- **2** [[<slug>|<Display Title>]]" "$v/moc-map.md"
      grep -B10000 -F -- "**2** [[<slug>|" "$v/moc-map.md" | grep -E '^- \*\*1\*\*' | tail -1 \
        | grep -F -- "[[<parent-slug>|"   # the nearest level-1 line above it is the parent
      grep -F -- "[[<slug>|" "$v/moc/<parent-slug>.md"
      grep -F -- "[[moc-map|" "$v/home.md"
    done
    cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
    git -C "$PKM_REPO" diff --cached --name-only; git -C "$PCM_REPO" diff --cached --name-only
    ```

    - The map has the MOC as a level-2 entry directly under its parent (the nearest
      level-1 line above it is the parent), the parent MOC links it, and `home.md` links the MOC
      Map (`[[moc-map|…]]`), so the MOC is reachable from each vault's map.
    - The two maps are identical.
    - The staged lists equal the ones recorded in Step 7. Normally both are empty.
    - Every edit that was pending before Step 7 is still there, unchanged.
      `git -C <repo> status --short` lists the new MOC files and this run's parent-MOC and
      `moc-map.md` changes alongside them.

    If any check fails, report which one and stop. Do not commit to "fix" it.

13. **Report completion** — State:
    - Files created: both full paths
    - Parent updated: both full paths, with the exact line added
    - Classification applied: code + label (note if reused from parent or if a deeper one was found)
    - Map lines added: the new line in each `moc-map.md`
    - Verification: each Step 12 check and its result
    - State plainly that everything is unstaged and uncommitted, that the shared reference map
      was not changed, and that publishing is a separate request (PKM-98)

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

- `$PKM_VAULT/moc/<slug>.md` exists with `primary_moc` set to the parent slug and `classification` filled
- `$PCM_VAULT/moc/<slug>.md` exists with the same frontmatter
- Parent MOC in both vaults contains `[[<slug>|<Display Title>]]` in a child section
- Both `moc-map.md` files were regenerated by their own script, list the MOC at level 2 under its parent, and are identical
- Nothing new is staged or committed in either repository, every edit pending before the run is intact, and the shared reference map is unchanged
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** — only first-level MOCs are listed there
- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/PCM/lcc/` is a symlink to it, so either path works for lookups
- Reusing the parent's classification is correct and expected when no more specific LCC sub-class fits (e.g. AWS under Compute Cloud Hosting both use T58.5)
- If the parent MOC is missing from either vault, the vaults have diverged and the Step 7 preflight stops. Never create a stub in one vault to get past it; fix the divergence first
- Publishing a locally created MOC is a separate request; the workflow for it is PKM-98. Until it is published, `moc-op begin` refuses to start, because the vault maps are ahead of the shared reference map. That is expected, and it does not affect local creation
- Related skills: `first-moc-level` (create the parent first), `third-moc-level` (create a child of this MOC)
