---
name: create-a-pkm-note
description: Creates a new KnowledgeVault (PKM) note from a link or pasted text by walking the MOC hierarchy (first → second → third level), inferring and suggesting a first-level MOC from the content, creating MOC levels on demand, and writing a classified Markdown note with YAML frontmatter and any grabbed images.
---

# Create a PKM Note

> Starts from a link or pasted text, infers and suggests a first-level MOC, then walks down the MOC hierarchy one level at a time — selecting or creating second- and third-level MOCs only when wanted — and finally writes a classified note (with frontmatter and any downloaded images) into the KnowledgeVault, linked back into the deepest MOC selected.

## Scope

This skill writes the note to the **KnowledgeVault (PKM) only** (`~/KnowledgeVault/PKM/`). It does **not** write the note to the PCM vault — use `create-a-pcm-note` for that. A note lives in exactly one vault; MOCs may exist in both (they are categories), notes must not.

## How This Skill Chains

This is an **orchestrator**. It reuses the existing knowledge skills rather than duplicating their logic:

| Step | Delegates to |
|---|---|
| List / suggest first-level MOC | first-level chooser (inline Python, below) |
| Create a new first-level MOC | `~/skills/skills/knowledge/first-moc-level/SKILL.md` |
| Select / create a second-level MOC | `~/skills/skills/knowledge/second-moc-level/SKILL.md` |
| Select / create a third-level MOC | `~/skills/skills/knowledge/third-moc-level/SKILL.md` |
| Write the note + link into the MOC | this skill (the **PKM-only** note creator) |

Everything happens in one sequential Claude session. The human is asked before each MOC level is selected or created. **At a minimum a note must have a first-level MOC** — the first-level step can never be skipped. The second and third levels are optional. The note inherits its LCC classification from the **deepest MOC selected**.

## Prerequisites

- `~/KnowledgeVault/PKM/` exists with `moc/`, `notes/`, `attachments/`, `lcc/`, and `templates/note-template.md`
- `~/KnowledgeVault/PKM/moc/` contains at least one first-level MOC (or the human is willing to create one)
- The MOC-creation skills exist under `~/skills/skills/knowledge/`
- Python 3 available (`python3`)
- `curl` available (for best-effort image downloads)
- Network access if the input is a link

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SOURCE` | A URL/link **or** raw pasted text to base the note on | _(required — ask the user first)_ |
| `DEEPEST_MOC` | The most specific MOC selected through the level walk | _(resolved during the walk)_ |
| `NOTE_TITLE` | The full human-readable title of the note | _(asked / inferred from the source)_ |
| `FILENAME_SLUG` | Kebab-case note subject for the filename | _(derived from the title)_ |

## Background

### Vault Paths (KnowledgeVault only)

| Purpose | Path |
|---|---|
| Notes | `~/KnowledgeVault/PKM/notes/` |
| MOC files | `~/KnowledgeVault/PKM/moc/` |
| Images / attachments | `~/KnowledgeVault/PKM/attachments/` |
| LCC outlines | `~/KnowledgeVault/PKM/lcc/` |
| Note template | `~/KnowledgeVault/PKM/templates/note-template.md` |

### Note Filename Convention

`<lcc-prefix>-<kebab-title>.md`

To derive `<lcc-prefix>`: lowercase the deepest MOC's LCC code and remove all dots.
Examples: `SB` → `sb`, `QA76` → `qa76`, `QA76.75` → `qa7675`, `T58.5` → `t585`.

To derive `<kebab-title>`: lowercase the note title, replace spaces and special characters with hyphens, collapse repeated hyphens.
Example: "How Agentic RAG Works" → `how-agentic-rag-works` → file `qa76-how-agentic-rag-works.md`.

### MOC Level Detection

- **First-level MOC**: `primary_moc:` is blank or absent
- **Second-level MOC**: `primary_moc:` matches a first-level MOC slug or title
- **Third-level MOC**: `primary_moc:` matches a second-level MOC slug or title

## Instructions

1. **Ask for the source** — Before anything else, ask the human:

   > "What should this note be built from? Paste a **link** (URL) or the **text** you want in the note."

   Wait for their answer. Record it as `SOURCE`. Decide its type:
   - Starts with `http://` or `https://` → treat as a **link**.
   - Otherwise → treat as **pasted text**.

2. **Gather the content.**

   **If the source is a link:**
   - Fetch the page content with `WebFetch` and ask it to return the main readable article/body converted to clean Markdown (drop nav, ads, cookie banners, and boilerplate).
   - Capture a sensible `NOTE_TITLE` from the page's `<title>` or main heading. Confirm it with the human (see Step 4); challenge any spelling/grammar problems in the title and propose a corrected version.
   - **Grab images (best effort):** identify image URLs referenced in the article body. For each, download it with `curl` into the attachments folder. Use a stable, slug-based filename. Run for each image (substitute values):

     ```bash
     mkdir -p ~/KnowledgeVault/PKM/attachments
     curl -fsSL --max-time 30 -o \
       ~/KnowledgeVault/PKM/attachments/<note-slug>-01.<ext> \
       "<image-url>"
     ```

     - `<note-slug>` is the kebab title from Step 8; number images `-01`, `-02`, … in order of appearance.
     - Keep the source extension (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`). If the URL has no extension, inspect the `Content-Type` and choose one.
     - If a download fails (403, timeout, hotlink protection), **skip it** — do not block the note. Note which images were skipped in the final report.
     - In the note body, embed each successfully downloaded image with an Obsidian embed at the place it appeared: `![[<note-slug>-01.<ext>]]`.
   - The cleaned Markdown becomes `body_content` for the note's `## Details` section. Add a source attribution line at the top of `## Details`: `Source: <original URL>`.

   **If the source is pasted text:**
   - Use the text as-is for `body_content`, lightly cleaned into valid Markdown (fix obvious heading/list formatting; do not rewrite the meaning).
   - There are no images to grab.
   - Infer a `NOTE_TITLE` from the first heading or first sentence; confirm it with the human in Step 4.

3. **Infer the subject and prepare a first-level MOC suggestion** — From the gathered content, determine the dominant subject. Run the **first-level MOC chooser** to list the existing first-level MOCs:

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

   Present the numbered list. Then state your recommendation, for example:

   > "Based on the content (which is about <subject>), I suggest first-level MOC **<N>. <Title>**. You can accept it, pick a different number, or create a new first-level MOC."

4. **Confirm the note title** — Show the proposed `NOTE_TITLE` and ask the human to confirm or correct it. Always propose a spelling/grammar-corrected version if the source title has problems, and let the human override.

5. **Resolve the first-level MOC (required).** Based on the human's choice in Step 3:
   - **Accept the suggestion or pick another number** → record `l1_slug`, `l1_title`, `l1_cls`, `l1_lbl` from the chosen row.
   - **None fit / create new** → execute the `first-moc-level` skill at `~/skills/skills/knowledge/first-moc-level/SKILL.md`: read it and follow its Instructions to create the new first-level MOC. When it finishes, use the MOC it created as `l1_*`. **Do not** follow that skill's own "offer to create a second-level MOC / note" tail steps — return here. **Then immediately link the new first-level MOC into `home.md` (see Step 5a).**

   Set `deepest_slug = l1_slug`, `deepest_title = l1_title`, `deepest_cls = l1_cls`, `deepest_lbl = l1_lbl`.

5a. **Link any newly created first-level MOC into `home.md` (required whenever a first-level MOC is created).** A first-level MOC must always appear in the vault's home page so it is reachable from the main navigation. If — and only if — Step 5 created a **new** first-level MOC, open `~/KnowledgeVault/PKM/home.md` and:

    - Find the `## Main Indexes` section.
    - Append a new list item in the same format as the existing entries: `- [[<l1_slug>|<l1_title>]]`.
    - Do **not** add a duplicate if a line already links `<l1_slug>`.
    - Update `home.md`'s `updated:` frontmatter field to today's date (Step 9).

    If Step 5 selected an **existing** first-level MOC, do not modify `home.md` — but if you notice the selected first-level MOC is missing from `## Main Indexes`, add it the same way (every first-level MOC belongs in the home index). Include `home.md` in the Step 13 commit whenever it changed.

6. **Prompt about a second-level MOC.** Ask:

   > "Do you want this note under a **second-level MOC** beneath **[l1_title]**, or keep it directly under [l1_title]?"

   - **Keep at first level** → skip to Step 8.
   - **Use / create a second-level MOC** → first list any existing second-level MOCs under this parent (substitute `<l1_slug>` and `<l1_title>`):

     ```python
     import os, re

     moc_dir = os.path.expanduser("~/KnowledgeVault/PKM/moc")
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

     - If `NONE` or the human wants a new one → execute the `second-moc-level` skill at `~/skills/skills/knowledge/second-moc-level/SKILL.md`; when it finishes, use the MOC it created as `l2_*`. Do not run that skill's own offer-tail; return here.
     - If they pick an existing one → record it as `l2_slug`, `l2_title`, `l2_cls`, `l2_lbl`.

     Update `deepest_* = l2_*`.

7. **Prompt about a third-level MOC** (only if a second-level MOC was selected). Ask:

   > "Do you want a **third-level MOC** beneath **[l2_title]**, or keep the note at [l2_title]?"

   - **Keep at second level** → skip to Step 8.
   - **Use / create a third-level MOC** → list existing third-level MOCs under `<l2_slug>` / `<l2_title>` using the same Python pattern as Step 6 (substitute the second-level slug/title for the parent).
     - If `NONE` or the human wants a new one → execute the `third-moc-level` skill at `~/skills/skills/knowledge/third-moc-level/SKILL.md`; when it finishes, use the MOC it created as `l3_*`. Do not run its offer-tail; return here.
     - If they pick an existing one → record it as `l3_slug`, `l3_title`, `l3_cls`, `l3_lbl`.

     Update `deepest_* = l3_*`.

8. **Derive filename and slug** — Compute:
   - `lcc_prefix`: lowercase `deepest_cls`, remove all dots (`QA76.75` → `qa7675`).
   - `note_slug`: kebab-case of `NOTE_TITLE`.
   - `filename`: `<lcc_prefix>-<note_slug>.md`.

   (If image downloads in Step 2 ran before the slug existed, rename the downloaded `attachments/*` files to use `<note_slug>` now, and update the embed references accordingly.)

9. **Get today's date** — Run `date +%Y-%m-%d` for `created` / `updated`.

10. **Confirm the plan** — Tell the human, then proceed:
    > "I will create **notes/<filename>**, classified **`deepest_cls` — deepest_lbl**, linked under **[deepest_title]**, with <K> image(s) saved to attachments/."

11. **Write the note (KnowledgeVault only)** — Write `~/KnowledgeVault/PKM/notes/<filename>`:
    ```yaml
    ---
    title: "<NOTE_TITLE>"
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

    # <NOTE_TITLE>

    ## Summary

    <one- or two-line summary inferred from the content>

    ## Details

    Source: <original URL, only if the source was a link>

    <body_content — the converted Markdown, with ![[<note_slug>-NN.ext]] embeds for any downloaded images>

    ## Related

    - [[<deepest_slug>|<deepest_title>]]
    ```

12. **Link the note into the deepest MOC** — Open `~/KnowledgeVault/PKM/moc/<deepest_slug>.md`:
    - Find the `## Notes` section. If it contains only the `- [[]]` placeholder, replace that line with the new link. Otherwise append a new list item.
    - Link format: `- [[<lcc_prefix>-<note_slug>|<NOTE_TITLE>]]`
    - Update the MOC's `updated:` frontmatter field to today's date.

13. **Commit and push (KnowledgeVault only)** — Stage the new note, the updated MOC, and any new attachments, then commit and push:

    ```bash
    git -C ~/KnowledgeVault/PKM add \
      notes/<filename> moc/<deepest_slug>.md home.md attachments/
    git -C ~/KnowledgeVault/PKM commit -m "note: add <lcc_prefix>-<note_slug>"
    git -C ~/KnowledgeVault/PKM push
    ```

    (Include `home.md` only if it was changed in Step 5a; otherwise drop it from the `add` list.)

    Report the commit hash after pushing.

14. **Report completion** — Summarize:
    - Source used (link or pasted text)
    - Note file created (full path)
    - MOC level reached and target MOC linked (full path + exact line added)
    - Classification applied: `deepest_cls` — `deepest_lbl`
    - Images downloaded (filenames) and any images skipped (with the reason)
    - Any MOC levels created during the walk (which skill, which slug)
    - Whether `home.md`'s `## Main Indexes` was updated (and the line added), if a first-level MOC was created
    - Commit hash pushed

## Success Criteria

- `notes/<filename>` exists in the KnowledgeVault with `classification` filled and `primary_moc` set to `deepest_slug`
- The note has **at least** a first-level MOC (`primary_moc` is never blank)
- The deepest MOC's `## Notes` section contains `[[<lcc_prefix>-<note_slug>|<NOTE_TITLE>]]`
- Filename follows `<lcc_prefix>-<note_slug>.md` (lowercase, no dots in prefix, hyphens throughout)
- Any successfully downloaded images live in `attachments/` and are embedded in the note body
- The note was **not** written to the PCM vault
- Whenever a new first-level MOC was created, `home.md`'s `## Main Indexes` section links it (`[[<l1_slug>|<l1_title>]]`); when only existing MOCs were used, `home.md` is updated only if the selected first-level MOC was missing from the index
- KnowledgeVault commit pushed

## Notes

- **First level is mandatory; second and third are optional.** The human is prompted before each deeper level and may stop at any point — the note targets the deepest MOC actually selected.
- Image grabbing is **best effort**. Hotlink protection, 403s, paywalls, and timeouts are expected on some sites; skip and report rather than failing the note.
- This skill writes the **note** to the KnowledgeVault only. The delegated MOC-creation skills (`first-moc-level`, `second-moc-level`, `third-moc-level`) keep their own dual-vault behavior — that is their concern, not this skill's.
- When delegating to a MOC-creation skill, **stop before its "offer to create a child MOC / note" tail steps** and return to this skill's flow, so the level walk stays under this orchestrator's control.
- `created` and `updated` use plain `YYYY-MM-DD` (not the Obsidian `{{date}}` template tokens — those are resolved by Obsidian, not here).
- Leave `tags: []` blank for the human to fill in later.
- For saving a web article into PKM with robust image archival, the ingest pipeline `~/KnowledgeVault/PKM/scripts/ingest-html-page.sh <url>` is an alternative to this skill's best-effort `curl` grab.
- Related skills: `create-a-pcm-note` (the PCM-only counterpart), `first-moc-level`, `second-moc-level`, `third-moc-level`.
