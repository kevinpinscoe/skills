---
name: knowledge-create-a-pcm-note
category: knowledge
description: Creates a new note in the PCM vault only by walking the MOC hierarchy with Python choosers, inheriting LCC classification from the deepest selected MOC, and linking the note back into that MOC.
disable-model-invocation: true
---

# Create a PCM Note

> Walks through up to three levels of MOC choosers to place a note precisely in the hierarchy, then creates the note in the **PCM vault only** (`~/PCM/PCM/`) with inherited LCC classification and links it back into the selected MOC.

## Scope

This skill writes the note to **PCM only** (`~/PCM/PCM/`). It does **not** touch the KnowledgeVault (PKM). Its sibling `create-a-pkm-note` is the PKM-only counterpart — a note lives in exactly one vault. MOCs may exist in both vaults (they are categories); notes must not.

## Shared MOC hierarchy

The PKM and PCM vaults share **one** MOC hierarchy. Each vault's `moc-map.md` is its local
copy, and the two must be identical. The shared reference map
(`~/Projects/private/knowledge-management-practice/maps/moc-map.md`) is the published copy and
may lag behind them until locally created MOCs are published. The rules are defined in
`~/Projects/private/knowledge-management-practice/practices/moc-hierarchy-alignment.md`; they are not restated here. For this skill that means:

- **The chooser shows the local hierarchy.** Before it runs, Step 0 checks that both vault maps
  (`moc-map.md`) are current and identical; if they are not, stop before choosing a MOC. MOCs
  created locally and not yet published are part of that hierarchy and can be chosen.
- **A missing MOC is created only through the MOC-level skills**, which create it locally in
  **both** vaults and leave it unstaged and uncommitted (AI-148). This skill never creates, renames, re-parents or
  retires a MOC, and never edits `home.md` or a `## Child MOCs` section.
- **The note itself goes to one vault only.** Linking it into the target MOC's `## Notes` list
  is a vault-specific change, not a hierarchy change.

## How This Skill Chains

Three Python choosers run sequentially — first-level always, then second- and third-level when the human wants to go deeper. At each level the human may pick an existing MOC or create a new one, which this skill delegates to the matching MOC-level skill so the MOC is created in both vaults. Each chooser runs inline as a Bash step; Claude captures its output, presents the list, waits for the human to pick a number, then continues. The entire flow happens in one Claude session. The note inherits its LCC classification from the **deepest MOC selected**.

## Prerequisites

- `~/PCM/PCM/moc/` must contain at least one first-level MOC (or the human is willing to create one)
- `~/Projects/private/knowledge-management-practice` cloned (the MOC-level skills use its `km-moc-*` tools), and the MOC-level skills under `~/.claude/skills/knowledge-*/`
- `~/PCM/PCM/notes/` must exist
- `~/PCM/PCM/templates/note-template.md` must exist
- Python 3 available (`python3`)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `DEEPEST_MOC` | The most specific MOC selected through the chooser chain | _(resolved by choosers)_ |
| `NOTE_TITLE` | The full human-readable title of the note | _(asked after MOC selection)_ |
| `FILENAME_SLUG` | Kebab-case note subject for the filename | _(derived from title)_ |

## Background

### Note Filename Convention

Note filenames are prefixed with a lowercased LCC code (dots removed) followed by a kebab-case title:

```
<lcc-prefix>-<kebab-title>.md
```

Examples:
- Classification `SB` + title "40V HP Brushless Bike Handle Brush Cutter" → `sb-40v-hp-brushless-bike-handle-brush-cutter.md`
- Classification `QA76` + title "Linux systemd Timers" → `qa76-linux-systemd-timers.md`
- Classification `T58.5` + title "Cloud Hosting Overview" → `t585-cloud-hosting-overview.md`

To derive the prefix: lowercase the LCC code and remove all dots. Examples: `SB` → `sb`, `QA76` → `qa76`, `QA76.75` → `qa7675`, `T58.5` → `t585`.

**Ranged codes (`Z696-697`, `BF309-499`, `T55.4-60.8`) — match the shelf that already exists.**
The corpus is genuinely split here: some notes keep the whole range (`bf309-499-*`) and others
truncate to the leading segment (`bf309-*`, `he8689-*`, `t55-*`). Before deriving a prefix from a
ranged code, list `~/PCM/PCM/notes/` for notes already shelved under that classification and reuse
whichever prefix they use. Only when no note exists on that shelf, fall back to the leading
segment. Deriving blindly splits one subject across two prefixes — e.g. adding a `z696-697-` note
beside three existing `z696-` ones — which is invisible in Obsidian and defeats the point of a
shelf marker.

### Vault Paths (PCM only)

| Purpose | Path |
|---|---|
| Notes | `~/PCM/PCM/notes/` |
| MOC files | `~/PCM/PCM/moc/` |
| Note template | `~/PCM/PCM/templates/note-template.md` |
| LCC outlines | `~/PCM/PCM/lcc/` (a symlink to `~/KnowledgeVault/PKM/lcc/`) |

`~/PCM/PCM/lcc/` is a symlink to the canonical `~/KnowledgeVault/PKM/lcc/`, so classification lookups work from the PCM path directly.

### MOC Level Detection

- **First-level MOC**: `primary_moc:` field is blank or absent
- **Second-level MOC**: `primary_moc:` is set; its value matches a first-level MOC slug or title
- **Third-level MOC**: `primary_moc:` is set; its value matches a second-level MOC slug or title

### Vault locations

`PKM_VAULT` defaults to `~/KnowledgeVault/PKM` and `PCM_VAULT` to `~/PCM/PCM`. Each vault's
repository root is its parent directory. The Instructions use these variables; a caller or a
test may supply other paths (such as disposable copies), and then they are exported and used
everywhere, never falling back to the live vaults.

## Instructions

Before Step 1, name the terminal tab this run is using: if `set-ghostty-tab-name` is on `PATH`, run `set-ghostty-tab-name PCM-note`. If the command is not on `PATH`, skip this step silently.

0. **Confirm the shared hierarchy** — Run, before anything else:

   ```bash
   bash "$PKM_VAULT/scripts/create-moc-map.sh" --check --strict
   bash "$PCM_VAULT/scripts/create-moc-map.sh" --check --strict
   cmp "$PKM_VAULT/moc-map.md" "$PCM_VAULT/moc-map.md"
   git -C "$(dirname "$PCM_VAULT")" diff --cached --name-only
   ```

   It is read-only. Both vault maps must be current and identical. That is the local MOC
   hierarchy, including MOCs created locally and not yet published (AI-148). The shared
   reference map may lag behind them, which is expected. If a check fails, show the human which
   one and stop: do not choose a MOC or write a note against a hierarchy that has diverged.
   Record the staged list printed by the last command (normally empty). Step 12 must leave it
   exactly as it is.

1. **Run the first-level MOC chooser** — Run immediately, before asking the human anything:

   ```python
   import os, re

   moc_dir = os.path.join(os.path.expanduser(os.environ.get("PCM_VAULT", "~/PCM/PCM")), "moc")
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

   Present the numbered list and ask: "Which first-level MOC does this note belong under? Enter the number, or **N** to create a new first-level MOC." Wait for their answer.
   - **A number** → record `l1_slug`, `l1_title`, `l1_cls`, `l1_lbl` from that row.
   - **N** → execute the `first-moc-level` skill at `~/.claude/skills/knowledge-first-moc-level/SKILL.md`: read it and follow its Instructions to create the MOC in both vaults. Do **not** follow its offer-to-create tail steps; return here and use the MOC it created as `l1_*`.

   A delegated MOC skill counts as finished only when its verification step passed: the MOC
   exists in both vaults and is reachable from both vault maps. It is local and uncommitted,
   which is expected (AI-148). If it reports a failed check, stop this note flow and report it.
   Never file the note under a MOC that is missing from either vault.


   Set `deepest_slug = l1_slug`, `deepest_title = l1_title`, `deepest_cls = l1_cls`, `deepest_lbl = l1_lbl`.

2. **Check for second-level MOCs** — Run this script substituting the selected first-level slug and title:

   ```python
   import os, re

   moc_dir = os.path.join(os.path.expanduser(os.environ.get("PCM_VAULT", "~/PCM/PCM")), "moc")
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

   Present any list printed (`NONE` means there are no second-level MOCs yet) and ask: "Select a second-level MOC, **N** to create a new one under **[l1_title]**, or press Enter to use **[l1_title]** as the target MOC."
   - **A number** → record `l2_slug`, `l2_title`, `l2_cls`, `l2_lbl` and update `deepest_*` to these values.
   - **N** → execute the `second-moc-level` skill at `~/.claude/skills/knowledge-second-moc-level/SKILL.md` with **[l1_title]** as the parent; skip its chooser and its offer-to-create tail steps, and use the MOC it created as `l2_*`. The same verification rule as Step 1 applies.
   - **Enter** → keep the first-level values as deepest and skip to Step 4.

3. **Check for third-level MOCs** (only if a second-level MOC was selected) — Run the same script as Step 2, substituting the selected **second-level** slug and title for `parent_slug` / `parent_title`.

   Present any list printed and ask: "Select a third-level MOC, **N** to create a new one under **[l2_title]**, or press Enter to use **[l2_title]** as the target MOC."
   - **A number** → record `l3_slug`, `l3_title`, `l3_cls`, `l3_lbl` and update `deepest_*` to these values.
   - **N** → execute the `third-moc-level` skill at `~/.claude/skills/knowledge-third-moc-level/SKILL.md` with **[l2_title]** as the parent; skip its choosers and its offer-to-create tail steps, and use the MOC it created as `l3_*`. The same verification rule as Step 1 applies.
   - **Enter** → keep the second-level values as deepest.

4. **Confirm the target MOC** — Tell the human: "The note will be linked to: **[deepest_title]** (classification: `deepest_cls` — deepest_lbl)." Proceed.

5. **Ask for the note title** — Ask: "What is the title of this note?" Wait for their answer. Challenge any spelling/grammar problems and propose a corrected version before proceeding.

6. **Ask for a one-line summary** (optional) — Ask: "Brief one-line summary for the note's Summary section? (Press Enter to leave blank.)" Wait for their answer.

7. **Ask about body content** — Ask: "Do you have content to add to this note now, or will you edit it later?" If they provide content, record it as `body_content` to write into the `## Details` section. If they say later / press Enter, leave `## Details` blank.

8. **Derive the filename** — Compute:
   - `lcc_prefix`: lowercase `deepest_cls`, remove all dots. Examples: `SB` → `sb`, `QA76.75` → `qa7675`, `T58.5` → `t585`
   - `title_slug`: lowercase the note title, replace spaces and special characters with hyphens, collapse multiple hyphens.
   - `filename`: `<lcc_prefix>-<title_slug>.md`

9. **Get today's date** — Run `date +%Y-%m-%d` for the `created`/`updated` fields.

10. **Create the PCM note** — Write `$PCM_VAULT/notes/<filename>`.

    `primary_moc` is the **deepest** MOC (`deepest_slug`); `related_mocs` lists the **broader
    ancestor MOCs above it**, as slugs — never a repeat of `deepest_slug`, and never a display
    title. A note whose deepest MOC is second-level therefore carries its first-level
    grandparent here; a note placed directly on a first-level MOC carries `related_mocs: []`.

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
      - "<ancestor-moc-slug>"   # the broader MOC(s) ABOVE deepest_slug, as slugs
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

11. **Update the target MOC in PCM** — Open `$PCM_VAULT/moc/<deepest_slug>.md`:
    - **First**, run Step 12's state check on this MOC and keep its answer (`new`, `pending` or `clean`).
    - Find the `## Notes` section. If it contains only `- [[]]`, replace that placeholder line with the new link. Otherwise append the link as a new list item.
    - Link format: `- [[<lcc_prefix>-<title_slug>|<Note Title>]]`
    - Update the `updated:` frontmatter field to today's date.

12. **Commit and push, or file locally** — decide by the state of the target MOC **in this
    vault**, recorded before Step 11 changed it, and never stage anything that is not this
    note's own:

    ```bash
    m="moc/<deepest_slug>.md"
    if ! git -C "$PCM_VAULT" ls-files --error-unmatch "$m" >/dev/null 2>&1; then echo new
    elif ! git -C "$PCM_VAULT" diff --quiet -- "$m" || ! git -C "$PCM_VAULT" diff --cached --quiet -- "$m"; then echo pending
    else echo clean; fi
    ```

    Run that check **before** editing the MOC in Step 11, and keep the answer.

    - **`new`** (the MOC was created locally and is not committed yet) or **`pending`** (the
      MOC already has edits that are not committed, so staging it would take them along):
      **file locally.** Stage nothing, commit nothing, push nothing. Verify:

      ```bash
      test -f "$PCM_VAULT/notes/<filename>"
      grep -F -- "[[<lcc_prefix>-<title_slug>|" "$PCM_VAULT/$m"
      git -C "$(dirname "$PCM_VAULT")" diff --cached --name-only   # must equal the Step 0 list
      ```

      Then report exactly: `Note filed locally under <deepest_title>; publication pending.`
      The note and its backlink are published with the MOC, as a separate request (PKM-98).

    - **`clean`** (the MOC is committed and had no pending edits): commit only this note's own
      paths, so nothing else staged or pending is included, then push:

      ```bash
      git -C "$PCM_VAULT" add notes/<filename> "$m"
      git -C "$PCM_VAULT" commit -m "note: add <lcc_prefix>-<title_slug>" -- notes/<filename> "$m"
      git -C "$PCM_VAULT" push
      ```

      `git commit -- <paths>` commits only those paths and leaves anything else that was
      already staged still staged. Report the commit hash after pushing.

13. **Report completion** — Summarize:
    - Note file created: full path
    - Target MOC updated: full path, with the exact line added
    - Classification applied: `deepest_cls` — `deepest_lbl`
    - Any MOC created during the walk: which skill, which slug, and that it is local and unpublished
    - Commit pushed: hash, or `Note filed locally under <deepest_title>; publication pending.`

    After reporting, close the tab: if `set-ghostty-tab-name` was run in the step before Step 1, run `set-ghostty-tab-name PCM-notec`.

## Success Criteria

- `$PCM_VAULT/notes/<filename>` exists with `primary_moc` set to `deepest_slug` and `classification` filled
- The note was **not** written to the KnowledgeVault (PKM)
- Target MOC in PCM contains `[[<lcc_prefix>-<title_slug>|<Note Title>]]` in its `## Notes` section
- Filename follows `<lcc_prefix>-<title_slug>.md` convention (lowercase, no dots in prefix, hyphens throughout)
- Step 0 found both vault maps current and identical before the chooser ran
- Every MOC created during the walk was created locally by a MOC-level skill whose verification passed, so it exists in both vaults
- `home.md` was not modified by this skill
- PCM commit pushed — or, when the target MOC was new or already had pending edits, the note was filed locally: nothing staged, committed or pushed, and the staged list is unchanged

## Notes

- The human may stop at any chooser level — if they skip the second-level or third-level chooser (by pressing Enter), the note targets the deepest MOC they did select
- `~/PCM/PCM/lcc/` is a symlink to `~/KnowledgeVault/PKM/lcc/`; use it for any classification lookups
- `created` and `updated` use plain `YYYY-MM-DD` format (not the `YYYY-MM-DDThh:mm:ss` Obsidian template syntax — that is resolved by Obsidian's template engine, not here)
- Leave `## Details` and `tags: []` blank for the human to fill in after creation
- For saving a web article into PCM (with image archival), prefer the ingest pipeline `~/PCM/PCM/scripts/ingest-html-page.sh <url>` over this manual skill
- MOCs are created only through `first-moc-level`, `second-moc-level` and `third-moc-level`, never in PCM alone — see `~/Projects/private/knowledge-management-practice/practices/moc-hierarchy-alignment.md`
- Related skills: `create-a-pkm-note` (the PKM-only counterpart), `first-moc-level`, `second-moc-level`, `third-moc-level`
