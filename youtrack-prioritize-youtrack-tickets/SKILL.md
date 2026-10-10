---
name: youtrack-prioritize-youtrack-tickets
category: youtrack
description: Review a YouTrack project backlog, assess dependencies and urgency, and maintain a ranked backlog refinement epic with human-confirmed field changes.
disable-model-invocation: true
---

# Prioritize YouTrack Tickets

> Review a YouTrack project backlog, assess dependencies and urgency, and maintain a ranked backlog refinement epic with human-confirmed field changes.

The skill works on **one project per run**. It reads every ticket in that project, works out which are open, evaluates each open ticket, and keeps one epic named `<PROJECT>-backlog-refinement` in that project. The epic's description holds a numbered ranked backlog, and every open ticket becomes a child of the epic.

The run has a fixed shape. Nothing is written until the last two steps:

```text
resolve project -> collect (read-only) -> evaluate -> plan file -> review with Kevin
  -> record decisions -> dry run -> apply (recheck, write, read back) -> report
```

Two ideas are kept apart throughout:

| Idea | What it means | Where it lives |
| --- | --- | --- |
| **Priority** | Urgency and impact of the ticket | The `Priority` field, changed only with approval |
| **Backlog rank** | The order to do the work in, given dependencies and readiness | The numbered table in the epic description |

A blocker for urgent work may rank first without getting the same `Priority` as its dependent.

## Prerequisites

- **A Home host with `parzival`: the FLDW or `core`.** API calls use Claude Code's brokered path, `parzival exec --as ai youtrack-claude-code`, wrapped by `scripts/yt-backlog`. On a Work host the `Claude_Code` identity is not provisioned. Stop and tell Kevin.
- `Claude_Code` is on the team of the project being reviewed. A `404` on the project or its issues means a team grant is missing, which only Kevin can add. Issues in projects that identity cannot see are unreadable, and are reported as gaps.
- `python3` (standard library only) and `curl`.
- Read access to the service catalog (`~/Projects/private/fedora-dashboard/kevins-federated-unix-universe-services.md`) and the host registry (`~/ai/directives/kevins-federated-unix-universe.md`), for the `Affected host` suggestions.

## Parameters

| Name      | Description                                                                | Default                     |
| --------- | -------------------------------------------------------------------------- | --------------------------- |
| `PROJECT` | The project's short name or name, e.g. `GLASS` (a project URL is accepted) | _(required — ask the user)_ |

Take `PROJECT` from the invocation when one was given (`/youtrack-prioritize-youtrack-tickets GLASS`). Otherwise ask.

## Instructions

`H` below is `~/.claude/skills/youtrack-prioritize-youtrack-tickets/scripts`. Use `bash $H/yt-backlog <cmd>` for the API subcommands (`resolve-project`, `collect`, `read-issue`, `apply`) and `python3 $H/yt_backlog.py <cmd>` for the offline ones (`validate-plan`, `review-table`, `render-section`).

`A` below is `~/archives/youtrack/backlog-refinement`. The snapshot, the plan and the journal of every run are kept there for audit. Name them `A/<SHORT>-<YYYYMMDD-HHMM>.snapshot.json`, `.plan.json` and `.journal.jsonl`, using the time the run started.

### Hard limits

- **`apply` is the only thing that writes.** Never write to YouTrack by hand in this skill: no `curl` of your own, no `POST /api/commands`, no MCP tool. If the helper cannot do something, stop and report it.
- **Never print or echo a token, and never write one to a file.** Never use `parzival get`, `yt-export`, a raw `bao kv get`, `app/YouTrack`, Kevin's credentials, or `bao-breakglass`. If a brokered call is refused, troubleshoot with `~/ai/directives/when-creating-a-youtrack-ticket.md` §14 and stop on anything it does not explain.
- **This skill never changes `Status` or `Assignee` on a reviewed ticket, and never starts work on one.** Prioritizing a ticket is not working it: no start comment, no tab rename, no `In Progress`.
- **It never closes, merges, deletes, or moves a ticket,** and never creates a dependency link. Those are recommendations for Kevin.
- **It never creates or renames a `Status`, `Priority` or `Affected host` value.** Those are admin changes, and Kevin makes them.

### Steps

1. **Resolve the project.** Run `bash $H/yt-backlog resolve-project "<PROJECT>"`. It returns exactly one live project, or fails and lists the candidates. On a failure, show Kevin the candidates and ask which he means. Never pick one. Call the exact short name `SHORT`. Template projects are refused.

2. **Collect the project. This is read-only.** Run `bash $H/yt-backlog collect SHORT A/<run>.snapshot.json`. It reads every ticket with complete pagination, then, for each open ticket, its links and comments. It is also the connection check: it proves the brokered identity can read the project, its field values, its link types and its issues. If it fails, stop. Tell Kevin, from its output and the snapshot's `analysis`:
   - how many tickets there are, and how many are open, excluded, or have no readable `Status`;
   - the eligibility rule it resolved from the live `Status` values (`status_mapping.rule`), for example "Open means Status is not Done, Wont do". If more than one do-not-do value exists, all are excluded, and the rule names them;
   - every entry in `gaps`. **A gap is an unread ticket, link list or comment stream. It is never an empty one.** Carry each gap into the review as an open question on that ticket;
   - the tickets in `status_unknown`. They are not ranked and not dropped: list them for Kevin to fix;
   - the epic state: `none`, `one`, or `multiple`.

   Open is decided from the `Status` field. The helper never uses `resolved`, `#Unresolved` or `#Resolved`, because on this instance a set `Category` keeps `Done` tickets unresolved and `Wont do` is not a resolved state. `analysis.resolved_flag_disagrees` lists the tickets where the flag would have given the wrong answer.

3. **Evaluate every eligible ticket.** For each entry in `analysis.eligible`, read its summary, description, comments, fields and links from the snapshot. Assess:
   - **The work:** what is required, the acceptance criteria, and whether the scope is unclear, duplicated, obsolete, or apparently already implemented.
   - **Dependencies:** `analysis.dependencies` holds the explicit `depends on` links. Add prerequisites named in descriptions or comments. A `relates to` link is not a dependency.
   - **Blockers in other projects:** read each one you need with `bash $H/yt-backlog read-issue <ID>`, and follow a prerequisite chain only far enough to explain what prevents completion. Do not crawl other projects. A `404` is an inaccessible reference: record it as a gap.
   - **External blockers:** approvals, access, hardware, decisions, third-party work.
   - **Urgency:** outages, security exposure, data-loss risk, deadlines, operational impact, and the cost of delay. Ticket age, the existing `Priority`, and emphatic wording are not evidence of urgency on their own.

   Keep three lists apart for each ticket, and keep them apart when you report: **confirmed facts** (a link, a field, a quoted comment), **inferred dependencies**, and **questions for Kevin**. A prerequisite whose `Status` is the do-not-do value is not satisfied: say whether the dependent needs an alternative or a scope change. Report `analysis.cycles`, contradictory links, and unresolved assumptions.

   For duplicate, obsolete, or apparently finished work, recommend the follow-up and leave the ticket alone. It stays eligible until its `Status` actually changes.

4. **Suggest `Affected host` values.** The field means the host the work is about. It is not the host the commands run from, not `Edit host`, and not a service's public hostname. Resolve the host from the ticket's evidence, the service catalog and the host registry, then pick the exact value from `bundles.affected_host` in the snapshot.
   - Work about exactly one host: propose that value, with a one-line reason. The FLDW's value is `FLDW`, not `kevin`.
   - Work about several hosts, no host, or an unclear scope: propose nothing, and say so in the item's `note`. The existing value stays.
   - An existing value that looks misleading: flag it for Kevin. Never clear it and never pick an arbitrary host. The helper refuses to clear the field.

5. **Rank the backlog.** Produce one order, `1..N`, covering every eligible ticket.
   - Confirmed prerequisites come before their dependents.
   - Among ready work, order by urgency and impact, then deadlines, then how much downstream work a ticket unlocks.
   - Blocked tickets are ranked too, with the reason they cannot proceed. Show an external blocker beside its dependent.
   - For a cycle or an uncertain prerequisite, set readiness to `needs-clarification` and say the order needs Kevin. Do not invent one.
   - Break ties by the previous rank when the evidence is unchanged (`epic_candidates[].previous_ranks` in the snapshot), then by issue ID.

   Recommend `Priority` from this table, and from nothing else. Apply a more specific local definition if Kevin has documented one.

   | Priority     | Guideline                                                                                    |
   | ------------ | -------------------------------------------------------------------------------------------- |
   | Show-stopper | A critical service or essential activity cannot proceed, and there is no viable workaround.  |
   | Critical     | Severe impact, security exposure, data risk, or a pressing deadline needing prompt action.   |
   | Major        | Significant impact, or important enabling work that deserves attention before routine tasks. |
   | Normal       | Routine planned work with ordinary urgency.                                                  |
   | Minor        | Low-impact improvements, convenience, or cosmetic work.                                      |

   Being blocked does not make a ticket a Show-stopper.

6. **Write the plan file** to `A/<run>.plan.json`. Every field decision starts as `pending` or `unchanged`.

   ```json
   {
     "project": "GLASS",
     "snapshot_collected_at": "<collected_at from the snapshot, copied exactly>",
     "epic": {"action": "create", "status": "Not yet started", "assignee": "Claude_Code", "approval": ""},
     "items": [
       {
         "issue": "GLASS-12", "rank": 1,
         "readiness": "ready",
         "blockers": "",
         "reason": "Unblocks GLASS-14 and GLASS-20; restore path is untested",
         "after": ["GLASS-3"],
         "priority": {"proposed": "Major", "decision": "pending"},
         "affected_host": {"proposed": "web1", "decision": "pending"},
         "parent": {"decision": "keep"}
       }
     ],
     "membership_removals": [{"issue": "OTHER-5", "decision": "pending", "approval": ""}],
     "next_actionable": ["GLASS-12"],
     "cross_project_prerequisites": ["GLASS-14 waits on https://youtrack.kevininscoe.com/issue/KHC-9 (In Progress)"],
     "cycles": [],
     "questions": [],
     "changes_since_last": ["GLASS-12 moved from 4 to 1: GLASS-3 closed"]
   }
   ```

   | Key | Rule |
   | --- | --- |
   | `readiness` | `ready`, `blocked`, or `needs-clarification` |
   | `after` | Prerequisites you confirmed from prose. Link-based ones are added by the helper. Omit when there are none |
   | `priority`, `affected_host` | `decision` is `approved`, `rejected`, `pending`, or `unchanged`. Leave the key out when you propose no change |
   | `approved_value` | Set when Kevin amends your proposal. It is what gets written |
   | `approval` | Required on every `approved` decision: who approved, when, and which batch |
   | `parent` | Required only for a ticket in `analysis.parent_conflicts`: `keep` or `replace` |
   | `membership_removals` | Exactly one entry per child of the epic that belongs to another project, and no other issue. `decision` is `approved`, `rejected`, or `pending`. `approved` needs an `approval` record, like any other write |
   | `epic` | `create` when no epic exists, otherwise `{"action": "update", "idReadable": "<ID>"}` |

   Then run `python3 $H/yt_backlog.py validate-plan A/<run>.snapshot.json A/<run>.plan.json` and fix every `FAIL`. It checks that every eligible ticket has exactly one rank, that prerequisites rank first, that every proposed value is a live allowed value, and that every write has an approval record. That includes each approved field change, parent replacement, cross-project removal, and the creation or correction of the epic.

7. **Present the review and get decisions.** Run `python3 $H/yt_backlog.py review-table A/<run>.snapshot.json A/<run>.plan.json` and show its output. It is a numbered table of every evaluated ticket, in batches, with full issue URLs, including the tickets where you propose no change. Below it show the existing-parent conflicts, the epic state, the gaps, and your questions.

   Ask Kevin to approve, reject, or amend each proposed `Priority` and `Affected host` change. He may answer for a clearly identified batch ("approve batch 1 except rank 4"). One prompt per ticket is not required. **Silence is not approval**, and neither is approval of something else. Also get an explicit decision for:
   - each existing-parent conflict: `replace` the parent, or `keep` it. Where replacing would create a hierarchy cycle, propose a cross-reference instead;
   - each child of the epic that belongs to another project, or was moved out: remove its membership, or leave it. Record his answer as `approved` with the `approval` text, or as `rejected` or `pending`. Only an approved removal with a record is carried out;
   - the epic, as step 8 describes.

   Record every decision in the plan file, with its `approval` text, and run `validate-plan` again. Leave rejected and undecided fields `rejected` or `pending`. They are not written.

8. **Settle the epic.** Its summary is exactly `<SHORT>-backlog-refinement`, for example `GLASS-backlog-refinement`. That is the summary. YouTrack assigns the issue ID.

   | `analysis.epic_state` | What to do |
   | --- | --- |
   | `none` | Confirm with Kevin that the epic may be created in `SHORT`, and which open `Status` it starts at (`Not yet started`, the instance default, unless he says otherwise). Set `epic.action` to `create` and record the `approval`. It is created with `Type = Epic`, `Date time entered` set to now, and `Assignee` `Claude_Code` unless Kevin names someone else |
   | `one` | Set `epic.action` to `update` with its ID. If its `Type` is not `Epic`, or its `Status` is `Done` or the do-not-do value, show Kevin the correction and record his approval under `epic.corrections` (`{"type": {"approval": "…"}, "status": {"to": "Not yet started", "approval": "…"}}`). Never reopen it silently and never create a replacement |
   | `multiple` | Show Kevin every candidate with its full URL and ask which is canonical. Record it as `idReadable` with `canonical_approval`. Never create another and never choose one yourself |

   Filing the epic is not starting it: no start comment and no tab rename.

9. **Dry run, then confirm.** Run `bash $H/yt-backlog apply A/<run>.snapshot.json A/<run>.plan.json --journal A/<run>.journal.jsonl --dry-run`. It rechecks live state and lists what a real run would do, and writes nothing. Show Kevin the field changes, the children to add and remove, the tickets whose membership will stay incomplete, and any drift. Wait for an explicit yes.

10. **Apply.** Run the same command without `--dry-run`. In order, it:
    - **rechecks first.** It re-reads the whole project and compares it with the snapshot. A ticket whose `Status`, `Priority`, `Affected host` or parent changed since the review is left alone: none of its operations run. Any such change, a new eligible ticket, or a change to the epic candidates also stops the description being rewritten, because the ranked list no longer describes what is there;
    - **checks the existing epic's description before it writes anything.** Malformed or duplicated section markers refuse the whole run at this point, so a description problem never leaves fields or links half changed;
    - writes only the `approved` field changes, and skips a value that is already in place;
    - creates the epic only when a fresh read shows none, or applies the approved corrections to the existing one. **A newly created epic is verified before anything depends on it:** its project, exact summary, `Type`, the approved `Status`, the requested `Assignee`, and that `Date time entered` is set. A workflow can rewrite fields on create. If any of them differs, the epic is reported with the mismatches, no child is attached, no description is written, and nothing is corrected. Fixing it is step 8's `one` row on the next run, with Kevin's approval;
    - removes the parent link of each child whose `Status` is now `Done` or the do-not-do value, and of each cross-project child whose removal was approved with a record. The tickets and their other links are untouched;
    - adds each eligible ticket as a child, using the parent/subtask link type and direction it read from the instance. It skips a ticket that is already a child, a ticket whose existing parent was kept, and any link that would create a hierarchy cycle;
    - **reconciles before it publishes.** After its own writes it reads the project again and compares the eligible tickets, their reviewed values, and the epic with the plan, allowing only for the changes this run itself made and verified. If a ticket was filed, reopened, closed or moved meanwhile, or a reviewed value or parent changed outside the run, or a second epic appeared, the description is **not** written, the differences are listed under `final_differences`, and the run exits `3`. An out-of-date plan is never published as the current backlog;
    - replaces only the generated section of the epic description, between its two marker lines. An epic with no section gets one appended after its existing text, which is kept exactly as it is, trailing whitespace included. Only the blank-line separator is added;
    - **guards the description against concurrent edits, as far as the API allows.** Immediately before posting, it reads the description again and compares the whole text with the text the replacement was built from. If someone edited it in between, the replacement is rebuilt from the new text, up to three times, and an old payload is never resent. If it keeps changing, the description is not written and the outcome is `conflict`. See the note on the remaining race below;
    - **reads every write back.** A write counts only when the read-back shows it. After an error or a timeout it reads live state before deciding anything, so a write that landed is not repeated and a `200` that changed nothing is reported as a failure. Read-back proves the write landed. It does not prove nothing else was overwritten.

    | `apply` exit | Meaning | Next |
    | --- | --- | --- |
    | `0` | Everything in the plan is applied and verified | Step 11 |
    | `3` | Partly applied: drift before or during the run, a kept parent, a blocked or mismatched epic, a description conflict, or a failed write | Read the report. For drift, go back to step 2 for a fresh snapshot, replan the affected tickets, and get fresh approval where a reviewed value changed. An approval carries over only for a ticket whose reviewed values are unchanged |
    | `2` | Refused before any write, or an API error | Report the message. Do not work around it |

    **Never retry a write by hand, and never trust the journal alone.** The journal records what was attempted. Only a fresh `collect` says what is true. Running the skill again is always safe: it reuses the same epic, repeats no field write, and adds no duplicate link.

11. **Report and end.** From the `apply` report, tell Kevin:

    ```text
    Epic: https://youtrack.kevininscoe.com/issue/<ID>
    Tickets reviewed: <N>
    Next actionable: <full URLs>
    Field changes applied: <ticket, field, value> (or "none")
    Children added: <list>   Children removed: <list>
    Membership incomplete: <ticket and reason> (or "none")
    Description: <written | blocked: reason>
    Outstanding: <pending decisions, drift, gaps, failures>
    Files: A/<run>.snapshot.json, .plan.json, .journal.jsonl
    ```

    Give every issue as its full URL in bare text. State incomplete reads, pending approvals, hierarchy conflicts, concurrent changes and partial writes plainly. Never summarise a run that exited `3` as complete. **The skill is then done.**

## Success Criteria

- One project was resolved, and every ticket in it was read with complete pagination. Open tickets were chosen from the live `Status` values, with `Done` and every do-not-do value excluded.
- Every eligible ticket has exactly one rank, a reason, and a recorded decision for `Priority` and `Affected host`, including "no change".
- No `Priority` or `Affected host` value changed without an `approval` record in the plan, and no rejected or pending change was written.
- Exactly one issue named `<SHORT>-backlog-refinement` is the epic in use, it has `Type = Epic`, and its description holds one generated section with the numbered ranked backlog. Text outside that section is unchanged.
- Every eligible ticket is a verified child of the epic, or is listed with the conflict that prevents it. Children that are now `Done` or do-not-do are unlinked from the epic and still exist.
- `apply` exited `0`, or it exited `3` and every skipped, blocked, conflicting and failed operation, and every entry in `final_differences`, was reported to Kevin.
- The snapshot, plan and journal are in `~/archives/youtrack/backlog-refinement/`, and the epic's full URL was reported.

## Notes

- **The generated section** starts at the line beginning `[backlog-refinement:begin]` and ends at the line `[backlog-refinement:end]`. Kevin can write anything above or below it. Deleting one marker, or pasting a second section, makes the next run stop and ask rather than guess.
- **The description update is not atomic, and one race remains.** YouTrack 2026.2 gives this API no conditional update: issue responses carry no `ETag` or `Last-Modified`, `If-Match` and `If-None-Match` are ignored on reads, and the `X-Version` header is the same for every resource, so it is not a per-issue version. Whether a write would honour a precondition was not tested, because that needs a live write. So the helper compares and then writes, as two separate calls. An edit that lands in the moment between its last read and its POST is overwritten, and the read-back cannot detect that. The window is one request wide. Avoid editing the epic description while `apply` is running, and if a note goes missing, the issue's history in the YouTrack UI still holds it.
- **The ranked table in the description is the authoritative order.** YouTrack's parent link carries no ordering this skill can set and verify, so the order in which children appear under the epic means nothing. Do not claim it does.
- **Cross-project blockers stay where they are.** They are listed and linked in the description. They are never made children of this epic and never moved.
- **Field IDs are read from a live issue on every run.** The helper finds `Status`, `Priority`, `Type` and `Affected host` by name and confirms each against its prototype ID, then writes with the project-scoped ID and `$type` the issue itself reports. If a name and its prototype disagree, it stops: the schema changed, and a human must say which field is meant. It never reads `api/admin/projects/<id>/customFields`, which returns an empty list to the `Claude_Code` token.
- **What was and was not exercised when this skill was written (AI-82, 2026-10-10).** The helper's logic is covered by offline tests against an in-memory model of the API. Against the live instance, only read calls were probed. The link add and remove calls, the epic creation, and the field writes had not been run live. The read-back rule is the safeguard: a write this instance ignores shows up as a failed operation, not as success. Treat the first real run as the proving run, and prefer a small project for it.
- **`Claude_Code` cannot see everything.** A ticket in a project that identity is not on the team of reads as `404`. Report it as inaccessible. Never infer that it does not exist.
- **Filing versus working.** This skill creates and maintains an epic and edits two classification fields. It works no ticket, so the one-ticket-at-a-time policy, start and stop comments, and `Spent time` do not apply to the reviewed tickets.
- Test the helper with `python3 $H/test_yt_backlog.py`. It is offline, needs no credentials, and never writes to YouTrack. It covers pagination, `Done` and `Wont do` filtering against contradictory resolution flags, cross-project blockers, dependency cycles, existing-parent conflicts, duplicate epics, partial field approval, removal approvals, drift between review and apply, changes made while `apply` is writing, first-time insertion beside human notes, concurrent description edits, a workflow rewriting a newly created epic, ambiguous write responses, and an unchanged rerun.
- Related skills: `youtrack-check-for-duplicate-tickets-and-tag` for duplicate detection, and `youtrack-move-a-youtrack-ticket` when the review finds a ticket in the wrong project.
