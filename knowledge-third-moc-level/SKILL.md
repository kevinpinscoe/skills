---
name: knowledge-third-moc-level
category: knowledge
description: Creates a third-level Map of Content (MOC) by first choosing a first-level MOC, then choosing a second-level MOC under it, then asking for a further focus area within that subtopic.
disable-model-invocation: true
---

# Create Third-Level MOC

> Opens a chooser popup to select a first-level MOC and then a second-level parent under it (or, as a fallback, two sequential numbered lists), then asks for a further focus area within that subtopic, looks up a deeper LCC classification if one exists, and writes the third-level MOC in both knowledge vaults.

## How This Skill Chains

The parent is chosen in **Step 1**. Claude runs `km-moc-popup --depth 2`, which opens the keyboard-driven `km-moc-chooser` in a tmux popup over this pane. The human picks a first-level MOC and a second-level MOC under it in one pass, and the validated pair comes straight back. Where no popup is possible, the skill falls back to two inline Python numbered lists, in Steps 1 and 3: Claude presents each list and the human picks a number. There is no separate launcher. The entire flow — chooser 1 → chooser 2 → focus area question → LCC lookup → file creation → map regeneration and verification — happens in one sequential Claude session.

## Prerequisites

- `~/Projects/private/knowledge-management-practice` cloned (it provides `km-moc-popup` and
  `km-moc-chooser`). No push access is needed: this skill creates the MOC locally and commits nothing
- Each vault's `scripts/create-moc-map.sh` (it regenerates that vault's `moc-map.md`)
- Both vaults hold the same MOC hierarchy, with at least one first-level and one second-level MOC (the Step 9 preflight checks the vaults agree)
- Both vaults must have `templates/moc-note-template.md`
- Python 3 available (`python3`)
- For the chooser popup (optional; without it Steps 1 and 3 use numbered lists): the session
  runs inside tmux 3.3+, and Fedora's `python3-urwid` is installed

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `GRANDPARENT_MOC` | The first-level MOC (narrows the second-level chooser) | _(resolved in Step 1: chooser popup `FIRST_SLUG`, or the numbered-list fallback)_ |
| `PARENT_MOC` | The second-level MOC this lives under | _(resolved in Step 1: chooser popup `SECOND_SLUG`; or Step 3 in the fallback)_ |
| `FOCUS_AREA` | The further subdivision or focus area within the parent subtopic | _(asked after parent is chosen)_ |
| `DISPLAY_TITLE` | Title as it should appear in parent MOC links | _(asked after focus area is known)_ |
| `LCC_CODE` | Classification code — deeper than parent if one exists, otherwise reuse parent's | _(derived via lookup)_ |

## Background: What These Vaults Are

This skill writes to two knowledge-management repositories that share structural conventions.

### MOC Hierarchy

- **First-level MOCs**: Broad subject maps (AI, Linux, Tools, Software). `primary_moc:` is blank.
- **Second-level MOCs**: Sub-topic maps under a first-level parent. `primary_moc:` is set to the parent's slug.
- **Third-level MOCs**: Narrowly focused maps under a second-level parent. `primary_moc:` is set to the second-level parent's slug.

A parent MOC lists its children in a `## Child MOCs`, `## Second-level MOCs`, or `## Third-level MOCs` section (detect and match what the parent already uses).

### Vault 1 — Personal Knowledge Base
Path: `~/KnowledgeVault/PKM/`

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

- **Filename**: lowercase, hyphen-separated, no spaces. Example: "Package Managers" → `package-managers.md`
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
  preflight (Step 9) proves the two vault maps are identical, so PKM's is the shared one.
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
- **Skip the terminal tab naming** (before Step 1 and in Step 15) — this runs headlessly
  from a script, not in Kevin's own interactive terminal.
- **Parameters** (read from the invoking prompt):
  - `MOC_NAME` — the focus area. Use it as `FOCUS_AREA` (Step 5).
  - `DISPLAY_TITLE` — the title/link text (Step 6). If absent, title-case `MOC_NAME`.
  - `PKM_VAULT`, `PCM_VAULT` — the vault paths (see *Vault locations*). If absent, use the
    defaults.
  - `PARENT_SLUG` — the **second-level** parent MOC's filename slug.
- **Skip Steps 1 and 3 (both choosers): open neither the popup nor the numbered lists.** The second-level parent is `PARENT_SLUG`; read
  its frontmatter per Step 4 (title, classification, classification_label).
- **Slug** — lowercase-hyphenate `MOC_NAME` per Step 7.
- **LCC classification (Step 8)** — search for a deeper class, then **auto-select the best
  match without asking**, reusing the parent's classification if none clearly fits. Do not
  block on ambiguity. Apply the verification rule in Step 8 to any code the local outline does
  not list. If that code cannot be confirmed, use the most specific confirmed class or the
  parent's class, and state this in the final report.
- **Execute Steps 9–15 exactly as written** — the local preflight, both vault files, the parent MOC in both vaults, the map regeneration and the verification. Do **not** modify `home.md`.
- **Step 14 (verification) is never skipped.** If any check fails, do not retry by editing
  other files; stop and report it.
- **Skip Step 16** (the interactive offer to create a note).
- **Final line** — after the completion report, print exactly `MOC-CREATED <slug>` on its
  own line **only** when every Step 14 check passed. Otherwise print `MOC-FAILED <slug>`. The
  navigator repeats the local reachability check itself before it reports success.

When invoked interactively (no parameters in the prompt), ignore this section and follow
the numbered Instructions below as usual.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name MOC`. If the command is not on `PATH`, skip this step silently.

1. **Choose the grandparent and the parent.** Before asking the human anything, open the chooser popup:

   ```bash
   bash ~/Projects/private/knowledge-management-practice/scripts/km-moc-popup.sh --map "$PKM_VAULT/moc-map.md" --depth 2 --title "Parent for the new third-level MOC"
   ```

   `--map` points it at the vault map, so MOCs created locally and not yet published can be
   chosen. It opens `km-moc-chooser` in a tmux popup over this pane, waits while the human picks, and
   prints five validated `KEY=VALUE` lines (`LEVEL`, `FIRST_SLUG`, `FIRST_TITLE`, `SECOND_SLUG`,
   `SECOND_TITLE`). Read them by splitting each line on its **first** `=`. **Never `eval` or
   `source` the output.** Act on the exit code:

   - **`0`**: `GRANDPARENT_MOC` is `FIRST_SLUG` (title `FIRST_TITLE`), and `PARENT_MOC` is
     `SECOND_SLUG` (title `SECOND_TITLE`). `LEVEL` is always `2` here, because the command
     rejects anything else. Do not run either numbered list. Do Step 2, skip Step 3, and continue
     at Step 4.
   - **`1`**: the human cancelled. **Stop.** Create nothing, and say the
     run was cancelled.
   - **`2`**: the popup ran but failed. Its stderr says why: a chooser error, a timeout, or a
     missing, malformed, stale or invalid result. Give the human that reason in one line, then
     use the fallback below.
   - **`3`**: no popup is possible here (not in tmux, no attached client, or tmux older than
     3.3). Use the fallback below without comment.

   Its checks and exit codes are documented in
   `~/Projects/private/knowledge-management-practice/scripts/RUNBOOK.md` → Step 6.

   **Fallback: the numbered lists (Steps 1 and 3).** Run this Python script:

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
           continue  # has a parent — skip
       title_m = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
       title = title_m.group(1).strip() if title_m else fname[:-3]
       results.append((fname[:-3], title))

   for i, (slug, title) in enumerate(results, 1):
       print(f"{i}. {title}  ({slug})")
   ```

   Present the numbered list and ask: "Which first-level MOC contains the second-level MOC you want to nest under? Enter the number." Wait for their answer. Record the selected first-level MOC's **slug** and **title**.

2. **Read the first-level MOC's frontmatter** — Open `$PKM_VAULT/moc/<grandparent-slug>.md` and extract its `title`.

3. **Run the second-level MOC chooser.** This is the fallback only: skip this step when the popup chose the parent in Step 1. Run this Python script, substituting the selected grandparent slug and title:

   ```python
   import os, re

   moc_dir = os.path.join(os.path.expanduser(os.environ.get("PKM_VAULT", "~/KnowledgeVault/PKM")), "moc")
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

4. **Read the second-level MOC's frontmatter** — Open `$PKM_VAULT/moc/<parent-slug>.md` and extract:
   - `title` — the parent's display title
   - `classification` — the parent's LCC code (baseline for this MOC)
   - `classification_label` — the parent's LCC label

5. **Ask for the focus area** — Ask: "What further focus area or subdivision within **[Parent Title]** do you want to map?" Wait for their answer. This becomes the subject of the new third-level MOC.

6. **Ask for the display title** — Ask: "How should this appear as a title and link in the parent MOC? (e.g. `[[package-managers|Package Managers]]`)" Wait for their answer.

7. **Determine the filename slug** — Convert the focus area to a lowercase, hyphen-separated slug. Example: "Package Managers" → `package-managers`.

8. **Search for a deeper LCC classification** — Read the relevant LCC outline file from `$PKM_VAULT/lcc/` starting from the parent's LCC class. Look for a sub-class that more precisely matches the focus area.

   **If a more specific sub-class exists**: use it.

   **If no more specific sub-class fits**: reuse the parent's classification code and label unchanged. Do not force a classification that doesn't fit.

   **Verify any code the local outline does not list.** The outline stops at broad ranges. Before proposing or assigning a more specific code, check it against the full Library of Congress schedule. If the schedule is not available, use the call numbers on matching records in the LC Catalog (https://catalog.loc.gov/). Never assign such a code from memory. Tell the human which source confirmed it. If it cannot be confirmed, say so and offer only confirmed classes.

   Call out ambiguities before confirming. Ask: "Which classification best matches your intent: [list candidates]?" Wait for confirmation.

9. **Get today's date and run the local preflight** — Run `date +%Y-%m-%d`. Then, before
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
     nothing, so the same list must still be staged, and nothing more, at Step 14.

   Pending unstaged edits and a lagging shared reference map are expected. Neither is a reason
   to stop.

10. **Create the KnowledgeVault MOC file** — Write `$PKM_VAULT/moc/<slug>.md`:
   Start from the vault's own `templates/moc-note-template.md` (read the file; the copy in the
   Background above is for orientation and may be out of date). Keep every section and comment
   line it has, including `## Child MOCs` with `None yet.`, and write lists in block style
   (`tags:` then `  - moc`), never `["moc"]`.

   Fill in:
    - `title`: the display title
    - `aliases`: `["moc <title lowercase>"]`
    - `type`: `moc`
    - `classification`: confirmed LCC code (deeper or reused)
    - `classification_label`: LCC label
    - `classification_source`: `lcc`
    - `primary_moc`: the second-level parent's slug
    - `related_mocs`: list with the second-level parent's **slug**, quoted — not its display title
    - `tags`: a block list with `moc`
    - `created` / `updated`: today's date
    - Body, in this order (`rules/moc-section-order.md`): `# <title> MOC`, `## Overview` with a
      one-sentence description of what focus area this covers, `## Child MOCs` with `None yet.`
      (this is the deepest level, so it stays empty), `## Notes` with `- [[]]`, then
      `## Related MOCs` linking back to the parent

11. **Create the PCM MOC file** — Write `$PCM_VAULT/moc/<slug>.md` with the same content. The PCM
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

12. **Update the parent MOC in both vaults** — In each vault, open `moc/<parent-slug>.md`:
    - Find a section named `## Child MOCs`, `## Third-level MOCs`, or similar. If no such
      section exists, add one immediately **before `## Notes`** — `rules/moc-section-order.md` in
      the PCM vault fixes the order as Overview → Child MOCs → Notes → Related MOCs, and it takes
      precedence over any other placement.
    - Add `- [[<slug>|<Display Title>]]`: if the section holds only the `None yet.` placeholder,
      replace that line with the link; otherwise append the link after the last entry.
    - Update the `updated:` frontmatter field to today's date.
    - If the parent MOC is missing from either vault, stop: the vaults have diverged. Never create a stub in one vault.

13. **Regenerate each vault's map** — with that vault's own script (it defaults to its own vault, so it runs from any directory):

    ```bash
    bash "$PKM_VAULT/scripts/create-moc-map.sh" --strict
    bash "$PCM_VAULT/scripts/create-moc-map.sh" --strict
    git -C "$PKM_REPO" diff -- "$PKM_VAULT/moc-map.md"; git -C "$PCM_REPO" diff -- "$PCM_VAULT/moc-map.md"
    ```

    Because Step 9 proved both maps were current, the only new lines are this MOC's, plus any
    earlier local MOCs that are already in the map. Do not edit `moc-map.md` by hand.

14. **Verify** — every check must pass:

    ```bash
    for v in "$PKM_VAULT" "$PCM_VAULT"; do
      grep -F -- "- **3** [[<slug>|<Display Title>]]" "$v/moc-map.md"
      grep -B10000 -F -- "**3** [[<slug>|" "$v/moc-map.md" | grep -E '^  - \*\*2\*\*' | tail -1 \
        | grep -F -- "[[<parent-slug>|"   # the nearest level-2 line above it is the parent
      grep -F -- "[[<slug>|" "$v/moc/<parent-slug>.md"
      grep -F -- "[[moc-map|" "$v/home.md"
    done
    cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
    git -C "$PKM_REPO" diff --cached --name-only; git -C "$PCM_REPO" diff --cached --name-only
    ```

    - The map has the MOC as a level-3 entry directly under its parent (the nearest
      level-2 line above it is the parent), the parent MOC links it, and `home.md` links the MOC
      Map (`[[moc-map|…]]`), so the MOC is reachable from each vault's map.
    - The two maps are identical.
    - The staged lists equal the ones recorded in Step 9. Normally both are empty.
    - Every edit that was pending before Step 9 is still there, unchanged.
      `git -C <repo> status --short` lists the new MOC files and this run's parent-MOC and
      `moc-map.md` changes alongside them.

    If any check fails, report which one and stop. Do not commit to "fix" it.

15. **Report completion** — Summarize:
    - Files created: both full paths
    - Parent MOC updated: both full paths, with the exact line added
    - LCC classification applied: code + label (note if reused from parent or deeper)
    - Map lines added: the new line in each `moc-map.md`
    - Verification: each Step 14 check and its result
    - State plainly that everything is unstaged and uncommitted, that the shared reference map
      was not changed, and that publishing is a separate request (PKM-98)

    After reporting, close the tab: if `set-ghostty-tab-name` was run in the step before Step 1, run `set-ghostty-tab-name MOCc`.

16. **Offer to create a note under this MOC** — After the completion summary, ask the human: "Do you want to create a note under **[this MOC's Display Title]**?" Wait for their answer.
    - **If no**: stop. The skill is complete.
    - **If yes**: ask which vault the note belongs in — "Which vault should this note live in: **PCM** or **PKM**? (A note lives in only one vault; MOCs may exist in both.)" Then execute the matching note skill, using **this third-level MOC as the target MOC** for the note:
      - **PCM** → `~/.claude/skills/knowledge-create-a-pcm-note/SKILL.md`
      - **PKM** → `~/.claude/skills/knowledge-create-a-pkm-note/SKILL.md`

      Read that file and follow its Instructions, but **skip its MOC chooser chain** — the target is already known. Set the note's `deepest_*` values from the MOC just created here:
      - `deepest_slug` = this MOC's `<slug>`
      - `deepest_title` = this MOC's display title
      - `deepest_cls` = this MOC's `classification`
      - `deepest_lbl` = this MOC's `classification_label`

      Then continue from the note skill's "ask for the note title" step onward. The note will inherit this MOC's LCC classification and be linked back into its `## Notes` section in the chosen vault.

## Success Criteria

- `$PKM_VAULT/moc/<slug>.md` exists with `primary_moc` set to the second-level parent's slug and `classification` filled
- `$PCM_VAULT/moc/<slug>.md` exists with the same frontmatter
- Second-level parent MOC in both vaults contains `[[<slug>|<Display Title>]]` in a child section
- Both `moc-map.md` files were regenerated by their own script, list the MOC at level 3 under its parent, and are identical
- Nothing new is staged or committed in either repository, every edit pending before the run is intact, and the shared reference map is unchanged
- Neither `home.md` was modified
- Filename is lowercase, hyphen-separated, no spaces

## Notes

- **Do not modify `home.md`** — only first-level MOCs are listed there
- The canonical LCC outlines live in `~/KnowledgeVault/PKM/lcc/`; `~/PCM/PCM/lcc/` is a symlink to it, so either path works for lookups
- The second-level chooser matches `primary_moc` against both the grandparent slug and title (case-insensitive) to handle the inconsistency in existing files where some use slugs and some use display titles
- Reusing the parent's classification is correct when no tighter LCC sub-class fits
- If the chooser in Step 3 returns no results, stop and direct the human to the `second-moc-level` skill
- Publishing a locally created MOC is a separate request; the workflow for it is PKM-98. Until it is published, `moc-op begin` refuses to start, because the vault maps are ahead of the shared reference map. That is expected, and it does not affect local creation
- Related skills: `first-moc-level` (top-level creation), `second-moc-level` (create the parent first)
