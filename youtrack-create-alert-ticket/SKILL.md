---
name: youtrack-create-alert-ticket
category: youtrack
description: Capture a pasted alert (or block of alerts) as a YouTrack issue in a project Kevin picks interactively — Type Problem, Status To do, assigned to Claude_Code — and hand back the ticket URL.
---

# Create Alert Ticket

> Turn a pasted alert or block of alerts into a correctly-populated YouTrack issue in the project Kevin selects, then report its URL. Filing only — this skill never troubleshoots or works the alert itself.

## Prerequisites

- Python 3 standard library only (`urllib`, `json`) — no `pip install` required
- Credential access goes through **parzival**, not a direct `bao` call. `run.sh` sources
  `~/.environment/openbao/openbao-env.sh` itself and fetches the token via
  `parzival exec --as ai youtrack-claude-code`. There is no vault token on disk to supply —
  PARZIVAL-2 revoked and removed `~/.environment/.vault-token`, and PARZIVAL-12 was filed
  because this skill broke when it did.
- YouTrack API token in OpenBao at mount `app`, secret `YouTrack-Claude-Code`, field `token` — **not** `app/YouTrack` (that path is reserved for Kevin's own human-run scripts) and **not** `app/YouTrack-backups`
- The `Claude_Code` YouTrack user must already be on the target project's team, or the create call 404s
- Network access to `https://youtrack.kevininscoe.com` (or `$YOUTRACK_BASE_URL` if overridden)

## Instructions

1. Run the skill from this directory:

   ```sh
   ./run.sh
   ```

2. The script will:
   1. Prompt for the alert(s) — paste the block, then type a line containing only `END` and press Enter to finish. Re-run if nothing was pasted (the script refuses an empty block).
   2. Fetch and display every YouTrack project (short name, name, `[archived]` tag), in the same format as `~/Projects/private/youtrack.kevininscoe.com/scripts/list-all-projects/list_projects.py`. Prompt for the target project by short name (case-insensitive), re-prompting on an unknown or archived short name.
   3. Resolve the project's live custom-field names for `Type` (`157-1`), `Status` (`157-2`), `Assignee` (`157-3`), and `Date time entered` (`157-15`) by prototype ID, per `~/ai/directives/when-creating-a-youtrack-ticket.md`. This reads the schema off one existing issue in the project (`GET /api/issues?query=project: <X>`) rather than the admin `customFields` endpoint — the `Claude_Code` token gets a silent `200 {}` from that admin endpoint (a permissions truncation, not "no fields attached"; confirmed 2026-09-02). A project with no issues yet to sample falls back to the known stock name/`$type` for these four fields. If a prototype still can't be resolved, it stops and says which.
   4. Resolve the `Claude_Code` user's internal ID via `GET /api/users`.
   5. Create the issue:
      - `Type` = `Problem`
      - `Status` = `To do`
      - `Assignee` = `Claude_Code`
      - `Date time entered` = now, epoch milliseconds
      - `summary` derived from the first non-blank line of the pasted alert text (truncated to 120 chars)
      - `description` = `Resolve and prevent re-occurence of alert(s): ` followed by a blank line and the full pasted alert text, unmodified
   6. Print `CREATED: <issue-key> in <project>` and the full issue URL.
3. **Report the full URL back to Kevin as bare text** (`https://youtrack.kevininscoe.com/issue/<KEY>`), never as a Markdown link and never the bare key alone, per the directive's URL-reporting rule.

## Success Criteria

- A new issue exists in the selected project with `Type = Problem`, `Status = To do`, `Assignee = Claude_Code`, `Date time entered` populated, and a description starting with `Resolve and prevent re-occurence of alert(s): ` followed by the pasted text.
- Script output ends with `CREATED: <issue-key> in <project>` and the issue's full URL, and exits `0`.

## Notes

- This skill only files the ticket — per `~/ai/directives/when-creating-a-youtrack-ticket.md` §11, filing an issue never touches the one-ticket-at-a-time lock, so `Status` is left at `To do` rather than moved to `In Progress`, and there is no worktree, `CHECKPOINT.md`, or terminal-tab rename involved.
- A `404` on create almost always means `Claude_Code` has not been added to the chosen project's team yet — that is a per-project grant Kevin makes, not something this skill can fix.
- If the paste needs to be abandoned mid-entry, `Ctrl-D` also ends input, but do so only as a last resort — it closes stdin, so the project-selection prompt that follows will fail too and the script must be re-run.
- **Related skill** — `../youtrack-report-a-problem` is the closer analog for a live service/infrastructure symptom Kevin is experiencing directly and wants corroborated before filing; this skill is for capturing an already-fired alert (from monitoring, email, etc.) with no corroboration step.
