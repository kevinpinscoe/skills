---
name: youtrack-move-a-youtrack-ticket
category: youtrack
description: Move an existing YouTrack issue to another YouTrack project through the REST API, preserve and verify its data, then create a POE follow-up ticket for updating home-directory Markdown references to the issue's new ID.
disable-model-invocation: true
---

# Move a YouTrack Ticket

> Move an existing YouTrack issue to another YouTrack project through the REST API, preserve and verify its data, then create a POE follow-up ticket for updating home-directory Markdown references to the issue's new ID.

This is a real move of the existing issue, made by updating its project with `POST /api/issues/{id}` and `{"project": {"id": ...}}`, so its history stays attached. It never recreates or copies the issue, and it never automates the web UI.

The evidence is gathered in a fixed order. Each step needs the one before it:

```text
human yt-export BEFORE -> API snapshot BEFORE (+ other-issue scan) -> textual-risk report
  -> project move -> human yt-export AFTER -> API snapshot AFTER -> structural + textual comparison
```

The human-run `yt-export` files are the human-readable evidence. The API snapshots are what the comparison actually runs on. **A snapshot never replaces an export, and no evidence file is deleted after a successful move.**

## What YouTrack does to text on a move

This was observed on the KSA-81 -> GLASS-2 move (2026-10-04), which is this skill's regression case. YouTrack rewrites the bare old key to the new one **inside issue text**:

- in this issue's description and comments: 234 mentions across 67 comments;
- in other issues' text, too (APP-43, PARZIVAL-77, KSA-117 and others).

| Rewritten | Left as written |
| --- | --- |
| Bare `KSA-81`, `ai-wt/KSA-81`, `KSA-81-frodo-hostkey`, `docs: KSA-81 design`, `` `git log main..KSA-81` `` | `https://youtrack.kevininscoe.com/issue/KSA-81`, `` `KSA-81` `` (code span holding exactly the key), `KSA-81s`, custom string fields (`Working branch`, `Ghostty tab name`) |

References should change. **Literal names of real objects should not.** Branches, worktree paths, commit subjects, commands, filenames and quoted logs still exist under the old key. So after a move:

- comment text is **not** expected to be byte-for-byte identical;
- it is expected to differ **only** by old-to-new substitutions, and the comparison sorts each substitution into one of three kinds.

| Kind | Meaning | Effect |
| --- | --- | --- |
| A. Expected reference rewrite | The occurrence names the moved issue | Fine |
| B. Historical-artifact rewrite | The occurrence was part of a literal name | Recorded; remediated by the POE ticket, never by this skill |
| C. Unexplained change | Anything beyond an old-to-new substitution | Stop for Kevin |

The old key and its URLs keep resolving to the moved issue. YouTrack's rewrite never reaches the filesystem: Git repositories, Markdown files, RUNBOOKs and `CHECKPOINT.md` files still say the old key. That is what the POE ticket's Part A is for.

## Prerequisites

- **A Home host with `parzival`: the FLDW or `core`.** API calls use Claude Code's brokered path, `parzival exec --as ai youtrack-claude-code`, wrapped by `scripts/yt-move`. On a Work host (`work-macbook`, `mac-container`) the `Claude_Code` identity is not provisioned. Stop and tell Kevin.
- `Claude_Code` is on the team of the source project, the destination project, and `POE`. A `404` means a team grant is missing, which only Kevin can add. Its searches see only projects on its team. So the cross-issue scan's claim is exactly "searched all issues visible to the Claude_Code identity to exhaustion", never "all issues in YouTrack".
- `yt-export` (`~/private-tools/yt-export`) is installed **for Kevin to run**. It wraps `~/Projects/private/youtrack.kevininscoe.com/YouTrack/hosted/youtrack-hosted-export-issue-markdown.py`, whose syntax is `yt-export <ISSUE> --out <FILE>` (or `-o`).
- `python3` and `curl`.

## Parameters

| Name          | Description                                                               | Default                     |
| ------------- | ------------------------------------------------------------------------- | --------------------------- |
| `SOURCE_ID`   | The issue's current readable ID, e.g. `KTA-19` (an issue URL is accepted) | _(required — ask the user)_ |
| `DESTINATION` | The target project's short name, e.g. `GLASS` (a project URL is accepted) | _(required — ask the user)_ |

## Instructions

`H` below is this skill's `scripts/` directory. Use `python3 $H/yt_move.py <cmd>` for the offline subcommands (`check-id`, `check-export`, `risk`, `compare`, `followup-text`), and `bash $H/yt-move <cmd>` for the API ones (`resolve-issue`, `resolve-project`, `snapshot`, `move`, `create-followup`). Never print or echo a token. Never write one into a file.

### Hard limits on yt-export

On the FLDW and `core`, `yt-export` gets its token through `parzival get --as youtrack-kevin`. That is Kevin's human identity, so per `when-creating-a-youtrack-ticket.md` §14 it is **not an AI read path**. The agent running this skill **must not**:

- invoke `yt-export`, or first try it to see whether it is refused;
- invoke `parzival get`, or use `youtrack-kevin`, `app/YouTrack`, or any other human credential;
- probe or work around the Parzival human/agent boundary, for example by unsetting a harness variable or using `bao-breakglass`.

Kevin runs every export himself. **He runs it in his own terminal, not with the `!` prefix in this session.** A `!` command runs inside the agent's shell, and `parzival get` refuses there.

### Steps

1. **Ask for the source issue.** Prompt Kevin for `SOURCE_ID`. Validate and normalise it with `python3 $H/yt_move.py check-id <SOURCE_ID>`. That step is a format check only and makes no API call. Refer to the result as `OLD`.

2. **Ask Kevin to run the pre-move export, then STOP.** This is the first operational step, and it comes before any API call. The command is:

   ```text
   yt-export OLD --out ~/tmp/OLD-before-project-move.md
   ```

   (With `OLD` substituted.) If that line is longer than 60 characters, also write it to `~/tmp/yt-export-OLD-before.sh`, opening with `#!/usr/bin/env bash` and `set -euo pipefail` plus a comment saying why Kevin runs it rather than the AI. Then give him `bash ~/tmp/yt-export-OLD-before.sh`. Tell him to run it in his own terminal. Wait for him to report the resulting path.

3. **Validate the pre-move export.** Run `python3 $H/yt_move.py check-export <reported path> OLD`. It checks that the file exists and is non-empty, that its heading is `# OLD — …`, that its URL names `OLD`, and that it has the custom-fields table. On any `FAIL`, stop and show the failures. Continue only on `OK`.

4. **Resolve the issue and take the pre-move API snapshot.**
   - `bash $H/yt-move resolve-issue OLD` gives the immutable entity ID (`3-NNNN`, called `EID` below), the source project, and the summary. If the issue does not exist, refuse.
   - `bash $H/yt-move snapshot OLD ~/tmp/OLD-before-project-move.api.json --scan OLD` captures:
     - the issue: entity and readable ID, project, summary, description, every custom field, tags, links, attachment metadata, comments (IDs, authors, timestamps and bodies), work items, and dates;
     - **other issues whose text mentions `OLD`**, with their mentioning comments. The scan has searched all issues visible to the Claude_Code identity to exhaustion. A short page never ends it, and a pager that repeats a page is an error, never a silent stop. Issues in projects that identity cannot see are not covered; say so whenever the scan is reported.

5. **Pre-move textual-risk report.** Run `python3 $H/yt_move.py risk ~/tmp/OLD-before-project-move.api.json`. Show Kevin:
   - how many occurrences of `OLD` the issue text holds, in this issue and in other issues, with the coverage line ("searched all issues visible to the Claude_Code identity to exhaustion");
   - how many YouTrack will likely rewrite, split into likely references and likely literal historical artifacts, with examples;
   - this warning, verbatim:

     > YouTrack may rewrite the old readable issue ID inside descriptions/comments when the issue moves. References should change, but literal branch names, worktree paths, commit subjects, commands, filenames or quoted logs may become historically inaccurate.

   Nothing has to be fixed before the move. On the KSA-81 regression data the prediction matched the real outcome exactly: 233 rewritten, 3 left.

6. **Ask for the destination and resolve it.** Prompt Kevin for `DESTINATION`. Run `bash $H/yt-move resolve-project <DESTINATION> --for-issue EID` to get its database ID (`0-NN`, called `PID`) and apply the refusals. Never guess or hardcode `PID`. The helper **refuses**, and the skill stops with nothing changed, if:
   - no project matches;
   - `PID` is the source project's ID;
   - the destination is a template project. A move into one, such as `TMPL`, is a one-way trip (`when-creating-a-youtrack-ticket.md` §1). The `Claude_Code` token is **not shown** the project's `template` or `archived` flag; both are absent even for `TMPL`. So the helper fails closed instead. It refuses `TMPL`, any project whose name contains "template", and any project in which search finds no issue, because template projects are excluded from search. A genuinely new, empty project therefore needs one issue filed in it first. There is no override flag;
   - authentication or authorization fails on the brokered path. Troubleshoot per §14 and never fall back to another credential.

   An **archived** destination cannot be detected for the same reason. When showing Kevin the resolved project, say so, so he can catch one himself. `bash $H/yt-move move` applies the same refusals again just before it posts.

7. **Confirm, then move.** Tell Kevin exactly what will happen: "Move `OLD` (entity `EID`, _summary_) from _source project_ to _destination project_ (`PID`). YouTrack will rewrite about _N_ mentions in issue text, about _M_ of them literal artifacts." Wait for an explicit yes. Then run `bash $H/yt-move move EID PID`. It posts `{"project": {"id": "PID"}}` to `/api/issues/EID` and re-resolves the issue **by entity ID**, so the changing readable ID cannot confuse it. If the re-read still shows the source project, the helper fails with `move reported success but issue is in …`. That is a stop: nothing moved, the pre-move evidence stays valid, and Kevin decides what happens next. Record the new readable ID as `NEW` (`OLD -> NEW`). If the call errors, re-resolve with `bash $H/yt-move resolve-issue EID` before saying anything. The move may have landed even though the response failed.

8. **Ask Kevin to run the post-move export, then STOP.** As in step 2, but for the new ID: `yt-export NEW --out ~/tmp/NEW-after-project-move.md` (or `~/tmp/yt-export-NEW-after.sh` if the line is long). Wait for the reported path. Then validate it with `python3 $H/yt_move.py check-export <reported path> NEW --project-name "<destination project name>"`. On any `FAIL`, stop and report.

9. **Take the post-move snapshot and compare.**

   ```text
   bash $H/yt-move snapshot EID ~/tmp/NEW-after-project-move.api.json \
     --references-from ~/tmp/OLD-before-project-move.api.json --scan NEW
   python3 $H/yt_move.py compare ~/tmp/OLD-before-project-move.api.json ~/tmp/NEW-after-project-move.api.json \
     --json ~/tmp/OLD-to-NEW-preservation-check.json > ~/tmp/OLD-to-NEW-preservation-check.txt; echo "compare rc=$?"
   cat ~/tmp/OLD-to-NEW-preservation-check.txt
   ```

   `--references-from` re-reads the other issues found before the move. `--scan NEW` finds issues that now mention `NEW` but were not in the pre-move evidence, so their text cannot be classified.

   **Cross-issue checks fail toward review, never toward clean.** Each of the following is _unverifiable_ cross-issue state:
   - a referencing issue from the pre-move evidence that cannot be re-read after the move;
   - a comment captured from a referencing issue that is no longer readable afterwards.

   Unverifiable state, like unclassified issues, makes the result exit `3`. It never makes it `0`, and on its own it never makes it `1`.

   **Structural preservation** holds when all of the following are true:
   - the entity ID is unchanged and the project changed;
   - created and resolved dates, reporter, votes and tags are identical;
   - comments have the same IDs, authors, creation times, deletion state and attachments. A changed `updated` time is accepted only on a comment whose text was rewritten;
   - attachments have the same identities, sizes, types and times;
   - links are the same;
   - work items are the same;
   - every non-text custom field is unchanged, nothing is lost, and nothing gained a value.

   **Text** — summary, description, comments, attachment names, work-item text and string fields — is checked by the rewrite analysis: kinds A, B and C above.

   | `compare` exit | Meaning | Next |
   | --- | --- | --- |
   | `0` | Structural preservation clean; no artifact remediation required | Step 10 (Part A only) |
   | `3` | Structural preservation clean and the move itself succeeded, but historical-artifact rewrites, unclassified issues or unverifiable cross-issue state were detected and must go to the POE remediation section | Step 10 (Parts A and B) |
   | `1` | Structural or unexplained textual discrepancy | **STOP.** The move is not verified |

   **On exit `1`, STOP.** Do not repair anything. Do not move the issue back. Do not create the POE follow-up. Report every `STRUCTURAL` and `UNEXPLAINED` line, both exports, both snapshots and the check files, then wait for Kevin's decision.

   **Never mass-replace `NEW` back to `OLD`**, here or anywhere. It would revert legitimate references. Historical-artifact rewrites are recorded and handed to the POE ticket, never restored by this skill.

10. **Create the POE follow-up: one ticket, separate sections.** First show Kevin the text with `python3 $H/yt_move.py followup-text OLD NEW --report ~/tmp/OLD-to-NEW-preservation-check.json`, then run `bash $H/yt-move create-followup OLD NEW --report ~/tmp/OLD-to-NEW-preservation-check.json`. It:
    - creates the issue in `POE`, with fields resolved by prototype ID from a live POE issue;
    - sets `Status` `Not yet started`, `Priority` `Normal`, `Type` `Task`, `Assignee` `Claude_Code`, and `Date time entered` to now (epoch milliseconds);
    - records the repository metadata (`when-creating-a-youtrack-ticket.md` §3). Any code change the follow-up makes is to Part A's shared rewrite utility, owned by `~/private-tools`. So `~/private-tools` owns the ticket: a `Repository: ~/private-tools` comment, and its forge URL in `Repo URL` (`157-17`). The URL is derived from that repo's `origin` at run time, and creation is refused, before any API call, if it cannot be derived;
    - omits what does not apply (§4): there is no Obsidian note line, and `Affected host` stays unset because the work is about files and issue text, not one host's state;
    - records `Old issue ID: OLD` and `New issue ID: NEW`, plus the paths of every evidence file;
    - always includes **Part A**, the home-directory Markdown cleanup. That covers the human-run boundary-aware `rg` inventory and the ban on AI recursive search (A1, A2). It covers the state-based bootstrap/reuse protocol for the shared `~/private-tools/yt-rewrite-moved-issue-id.py` utility (A3). It gives that utility's 18-point contract (A4) and its required tests (A5). And it covers attaching the inventory, artifact review, mapping each approved inventory path to the same relative path in that repository's POE worktree (the inventory says _which_ file; the worktree copy is _where_ it changes, never the main checkout), with both lexical and resolved (symlink-safe) containment, an approved path that is outside Git, untracked or in another worktree reported to Kevin rather than edited in place or dropped, one utility run per worktree copy, and the explicit-file diff review (A6);
    - includes **Part B**, historical-text remediation, only when the comparison found artifact rewrites, unclassified issues or unverifiable cross-issue state. Part B lists the locations, names every issue and comment that could not be re-checked, points at the pre-move snapshot, and requires that only verified literal artifacts are restored, location by location, with Kevin's approval and never by mass replacement;
    - uses the summary `Update Markdown references after OLD moved to NEW`, or `Update Markdown references and restore historical text after OLD moved to NEW` when Part B is present;
    - reads the issue back, and fails if any of those fields or the `Repository:` comment does not read back as written.

    Filing is not starting. The issue stays `Not yet started`, with no start comment and no tab rename (§7, §11).

11. **Report and end.** Output, from the comparison and the follow-up:

    ```text
    Moved: OLD -> NEW
    Immutable issue ID preserved: PASS
    Structural preservation: PASS
    Expected YouTrack text rewrites: <count>
    Historical-artifact rewrites: <count>
    Unexplained changes: 0
    Cross-issue scan: searched all issues visible to the Claude_Code identity to exhaustion
    Pre-move export: ~/tmp/OLD-before-project-move.md
    Post-move export: ~/tmp/NEW-after-project-move.md
    Filesystem-reference follow-up: POE-<n> https://youtrack.kevininscoe.com/issue/POE-<n>
    Historical-text remediation: POE-<n> (Part B of the same ticket)
    ```

    Include the last line only when Part B exists. Keep the cross-issue scan line worded exactly as shown; it is not a claim about all of YouTrack. Never summarise the text result as plain `PASS` when historical artifacts were rewritten. Give URLs as bare text. Tell Kevin the POE ticket is ready for him to hand to an AI agent. Remind him of any `~/tmp/yt-export-*.sh` scripts this run wrote, and offer to remove them. The evidence files stay. **The skill is then done.**

## Success Criteria

- The issue's entity ID is unchanged, it is in the destination project, and it has a new readable ID.
- Two validated human-run exports, two API snapshots and the comparison files exist in `~/tmp`. `compare` exited `0` or `3`, with `Structural preservation: PASS` and `Unexplained changes: 0`.
- A POE issue exists with `Assignee` `Claude_Code`, `Status` `Not yet started`, `Date time entered`, `Repo URL` and the `Repository:` comment, both IDs, Part A, and Part B whenever remediation or review is needed. It was read back, and its full URL was reported.
- Nothing in the out-of-scope list below was done.

## Notes

- **Out of scope for this skill. Each of these belongs to the POE ticket:**
  - running any recursive `rg`/`ripgrep`/`ugrep` search;
  - editing Markdown references;
  - writing the rewrite utility;
  - restoring rewritten historical text;
  - working the POE ticket.

  Bypassing the human-only `rg` wrapper or the Parzival boundary is out of scope for everyone.
- **The artifact classifier is deliberately conservative. Do not tune it to match a hand count.** It looks at paths, `-suffix` names, branch, worktree and command words, commit-subject prefixes and code spans. On the real KSA-81 data it put 150 of 233 rewrites in kind B, where an earlier hand estimate was about 111. A false positive costs one human check in Part B. A false negative would leave a real branch, path or commit identifier silently wrong. Part B's per-location approval is the safety mechanism.
- **Who creates the rewrite utility is decided by repository state, never by ticket.** Part A's A3 has three cases.
  - **Case 1:** the utility is tracked on `private-tools` main. The ticket validates it, runs its tests and reuses it.
  - **Case 2:** a concrete implementation is in progress: an open PR, a pushed branch, or a recorded worktree with committed work. The ticket records the dependency and stops.
  - **Case 3:** neither exists. The current ticket becomes the bootstrap owner and builds the utility in its own `private-tools` worktree. It opens a prerequisite PR and stops until Kevin merges it, then rewrites from main.

  An open POE ticket, or a planned implementation, is not a lock. Neither is file presence: a remote branch that contains the utility counts only if a current ticket, lane or open PR actively owns it. A stale or unowned branch is reported, not obeyed. Two genuinely active implementations at once is a stop for Kevin. This replaced an unconditional "create the utility" step, after POE-28 waited on POE-27's plan while no implementation existed anywhere (2026-10-05). The move skill itself still never creates the utility.
- **Boundary-aware matching on the filesystem.** Part A matches `OLD` only where the character before it is not a letter, digit or hyphen, and the character after it is not a digit. So `KTA-19` never rewrites `KTA-190` or `ABC-KTA-19`. The `rg` inventory and the rewrite utility share that one pattern.
- **Use the issue-update form, not the `/project` sub-resource.** JetBrains documents `POST /api/issues/{id}/project` with `{"id": ...}`. On this instance (YouTrack 2026.2, build 17765) it returned 200 and moved nothing: KSA-117 -> GLASS, 2026-10-04. `Claude_Code` held every issue permission in both projects, so that was not the cause. The issue-update form was proven the same day: a throwaway TEST-7 was moved by the helper to AI-70, confirmed by entity ID, and deleted. Keep the re-read check whichever form is used.
- **YouTrack's cross-project move warning is boilerplate.** Field data is actually lost only when the source carries a field, or a bundle value, that the destination lacks. The structural check catches that.
- **Activity history is not compared.** The `Claude_Code` token cannot see every activity record (`reference/custom-fields.md`). The exports and snapshots are the record.
- Test the helper with `python3 $H/test_yt_move.py`. It is offline and fixtures-only, never moves anything, and its regression fixtures model the KSA-81 -> GLASS-2 behaviour with synthetic text.
