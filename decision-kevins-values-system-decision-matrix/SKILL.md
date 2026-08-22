---
name: decision-kevins-values-system-decision-matrix
category: decision
description: Walks the human through Kevin's Values System Decision Matrix — the quadrant filter first, then weighted values scoring — and writes the result as a durable decision record in the journal vault.
---

# Kevin's Values System Decision Matrix

> Runs a decision through Kevin's four-quadrant values filter, scores anything that lands in the **Values** quadrant against his weighted life values, and writes a dated decision record to `~/Journal/personal-journal/DECISIONS/`.

## Scope

This skill implements the framework published at
<https://old-public-wiki.kevininscoe.com/index.php/Kevins_Values_System_Decision_Matrix>.
That page is the source of truth for the **filter**. It is explicitly *not* the source of truth
for the **math** — the page says verbatim: *"I am still working out the math I use to arrive at
exactly how I prioritize these tasks (weighted values come to mind)."* The scoring model in the
**Weighted Values Scoring** section below is this skill's implementation of that missing piece.
If Kevin later publishes the math on the wiki, the wiki wins and this section is updated to match.

This is a **decision** matrix, not a priority matrix. Its purpose is to *remove* unnecessary
tasks. A legitimate outcome of this skill is **"drop it."** Do not assume the thing being
decided has to get done.

## Prerequisites

- The human is present and able to answer questions one at a time
- `~/Journal/personal-journal/` exists and is a git repository (the Obsidian journal vault)
- `~/ai/` exists and is a git repository (holds the values file)
- Network access, only if re-fetching the wiki page (optional — the framework is embedded below)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `DECISION` | Plain-English description of what needs to be decided | _(required — ask the human)_ |
| `OPTIONS` | The competing options. A single task is modelled as one option ("do it") | _(asked)_ |
| `VALUES_FILE` | Where the life values and their weights live | `~/ai/kevins-values.md` |
| `RECORD_DIR` | Where the decision record is written | `~/Journal/personal-journal/DECISIONS/` |
| `FUN_BUDGET` | Daily time budget for the Fun and Fulfilling quadrant | `2 hours` |

## Background

### The filter quadrants

Two columns and four quadrants. Everything is run through this filter **before** any priority
letter or scoring is applied.

| | **Required** — someone else told you, or someone needs it done. Not based on your values. **Not negotiable.** | **Your Decisions** — tied to your values and needs. Negotiable, and can be ignored at varying consequence. |
|---|---|---|
| **Row 1** | **Urgent** — the "swallow the live frog" quadrant. Do the thing you least want to do first each day, but **only** if it is *truly* urgent. If it isn't, move it to Non-Urgent. | **Values** — did **not** fit any of the other three quadrants. Re-evaluate against your life values, and filter out anything that costs more than it adds. |
| **Row 2** | **Non-Urgent** — the usual trap. It must be done but has no obvious due date. Do resource, time, effort and dependency analysis and give it a working due date. If it is truly required, a date exists somewhere — find it by asking what the consequence is if it isn't done by a given time. | **Fun and Fulfilling** — unwind time. Necessary, not optional, and it eases stress. But it gets a **daily time budget** (`FUN_BUDGET`). Once that is exhausted, this category is closed for the day. |

### Covey priority, applied afterwards

The classic Covey/Franklin A1, B2, C6 priority scheme still applies — but **only after** the item
has passed the filter above. Letter = importance, number = sequence within that letter.

### Weighted values scoring

Applies to the **Values** quadrant only.

**Value Score** — for each life value in `VALUES_FILE`, rate how much the option advances that
value, then weight it:

```
Value Score = Σ(weight_i × score_i) / 100
```

| Score | Meaning |
|---|---|
| `+5` | Directly serves this value — this is what the value is *for* |
| `+4` | Strongly advances it |
| `+3` | Meaningfully advances it |
| `+2` | Minor gain |
| `+1` | Trivial gain |
| `0` | Neutral — no bearing on this value |
| `-1` to `-5` | Actively *harms* this value, on the same scale |

Weights come from `VALUES_FILE` and sum to 100, so `Value Score` lands in the range `-5` to `+5`.

**Cost Score** — one rating, `0` to `5`, covering time, money, and energy together:

| Cost | Meaning |
|---|---|
| `0` | Free — no meaningful time, money, or energy |
| `1` | An hour or two, trivial cost |
| `2` | A day of effort, or a small purchase |
| `3` | Several days, or a purchase that needs thinking about |
| `4` | Weeks of sustained effort, or real money |
| `5` | Months, or money that displaces something else |

**Net Value = Value Score − Cost Score.** This is the wiki's rule — *"get RID of tasks that cost
more than they add to the value I appreciate"* — expressed as arithmetic.

**Verdict thresholds:**

| Net Value | Verdict | What happens |
|---|---|---|
| `≥ +1.5` | **Commit** | Hard due date. Covey priority `B`. |
| `+0.5` to `+1.4` | **Commit, scheduled behind Required** | Hard due date, but nothing Required waits on it. Covey priority `C`. |
| `-0.4` to `+0.4` | **Park** | Not committed. Gets an explicit re-evaluation date, not a due date. |
| `≤ -0.5` | **Drop** | Costs more than it adds. Remove it. This is the filter working correctly. |

Anything not dropped or parked **must** get a hard due date. Per the wiki: *"the dreamed task is
the wont ever get done task. If you love it put a due date on it!"*

## Instructions

1. **Read required directives** — before writing anything, read and follow:
   - `~/ai/directives/root-directive.md` (dispatcher — follow anything it points to that applies)
   - `~/ai/directives/when-making-changes-in-a-directory-that-is-also-a-git-repo.md`
   - `~/ai/directives/project-planning-with-ai.md` (for its `CHECKPOINT.md` collision check)

   Run the `CHECKPOINT.md` collision check in `~/Journal/personal-journal/` and `~/ai/` before
   any file is created or modified.

2. **Ask what needs deciding** — ask exactly this and wait:

   > "What do you need to decide? Describe it in plain English — one or two sentences is fine."

   Record it as `DECISION`. **Challenge any spelling or grammar problems** in what the human typed
   and propose a corrected wording before continuing; the human may override. Read the corrected
   version back and confirm it is what they meant.

3. **Ask for the options** — ask:

   > "Are you choosing between competing options, or deciding whether to do one thing at all?
   > If there are options, list them."

   If it is a single thing, model it as one option named after the task. If there are competing
   options, record each one — every stage below runs per option.

4. **Load the values file** — read `VALUES_FILE` (`~/ai/kevins-values.md`).

   - **If it exists:** show the values and weights as a table and ask:

     > "These are your current life values and weights. Use them as they are, or adjust them for
     > this decision?"

     If the human adjusts them, apply the change to the file (see step 10).

   - **If it does not exist:** build it now. Tell the human the wiki says to keep life values to
     between **3 and 6** major headings, and that the page names *Family, Faith, Health, Career,
     Quality of Life,* and *Education/Self-Improvement* as its own example. Ask, one question at a
     time and waiting for each answer:

     1. "What are your life values for this system? Give me between 3 and 6."
     2. "Now weight them. They must add up to 100. What weight does each one get?"

     Do not suggest values or weights on the human's behalf — ask, and wait. Validate that the
     weights sum to exactly 100; if they do not, say by how much they are off and ask again. Write
     the file per step 10.

5. **Run the quadrant filter** — for each option, ask one question at a time and wait for each
   answer. Do not infer the answers.

   a. > "Is this **Required** — someone else told you to do it, or someone needs it done
      > regardless of your values — or is it **Your Decision**?"

   b. **If Required:**

      > "Is it *truly* urgent? Urgent means there is a real consequence to not doing it now, not
      > that it merely feels pressing."

      - **Urgent** → quadrant `Required / Urgent`. This is the swallow-the-frog quadrant. Covey
        priority `A`. Skip scoring entirely — it is not negotiable. Go to step 7 for the due date.
      - **Non-Urgent** → quadrant `Required / Non-Urgent`. Skip scoring. Do the analysis in
        step 6, then go to step 7. Covey priority `B`.

   c. **If Your Decision:**

      > "Is this about your **values** — something you want because it advances your life — or is
      > it **fun and fulfilling** — unwind, rest, stress relief?"

      - **Fun and Fulfilling** → quadrant `Decisions / Fun and Fulfilling`. Do not score it. Ask:

        > "How much of today's `FUN_BUDGET` budget is already spent, and how long would this take?"

        If it fits the remaining budget, the verdict is **Do it, within budget**, Covey priority
        `C`. If it does not fit, the verdict is **Not today — the budget is busted**. Go to step 8.

      - **Values** → quadrant `Decisions / Values`. Go to step 6 for the scoring.

6. **Analysis** — what happens here depends on the quadrant.

   - **Required / Non-Urgent** — do the resource, time, effort and dependency analysis the wiki
     calls for. Ask:

     > "What is the consequence if this isn't done by a given date, and what does it depend on?"

     Use the answer to derive a working due date in step 7. It is required, so a real date exists
     somewhere — the job here is to find it.

   - **Decisions / Values** — run the weighted scoring. For each option, walk the values **one at
     a time**, asking:

     > "On a scale of `-5` to `+5`, how much does *[option]* advance **[value]**? Use `0` if it
     > has no bearing, and a negative number if it actively harms that value."

     Then ask once per option:

     > "On a scale of `0` to `5`, what does *[option]* cost you in time, money, and energy
     > together?"

     Compute `Value Score`, `Cost Score`, and `Net Value` per the Background section. Show the
     working as a table — value, weight, score, weighted contribution — so the human can see
     where the number came from. Apply the verdict thresholds.

     Then run a **sensitivity check** and report it: name the single value contributing the most
     to the result, and state whether changing that one score by ±1 would move the option across a
     verdict threshold. If it would, say so plainly — the decision is close and rests on one
     judgement call.

     If there are competing options, rank them by `Net Value`. If the top two are within `0.3` of
     each other, call it a tie and break it in this order: (1) the option scoring higher on the
     highest-weighted value, then (2) the option with the lower `Cost Score`. Say which tie-break
     was used.

7. **Set a hard due date** — for anything not dropped and not parked, ask:

   > "When does this need to be done? Give me a hard date — based on anticipated effort,
   > resources, availability, and time constraints."

   Wait for the answer. Do not invent a date. If the human resists giving one, say so directly:
   the wiki's rule is that a task without a date does not get done.

   For a **parked** item, ask for a re-evaluation date instead, and label it as such — it is not
   a commitment.

8. **Assign the Covey priority** — letter from the quadrant and verdict, number for sequence
   within that letter:

   | Quadrant / verdict | Letter |
   |---|---|
   | `Required / Urgent` | `A` |
   | `Required / Non-Urgent` | `B` |
   | `Decisions / Values`, Net Value `≥ +1.5` | `B` |
   | `Decisions / Values`, Net Value `+0.5` to `+1.4` | `C` |
   | `Decisions / Fun and Fulfilling`, within budget | `C` |
   | Parked or Dropped | _(none — it is not on the list)_ |

   Ask the human for the sequence number if there are other items already carrying that letter;
   otherwise use `1`.

9. **Present the result before writing anything** — show the human, in this order:

   1. One or two sentences saying what the verdict is and why.
   2. The quadrant it landed in.
   3. The scoring table, if scoring was run.
   4. The verdict, the Covey priority, and the hard due date.
   5. The sensitivity check, if scoring was run.

   Then ask:

   > "Write this to a decision record?"

   Wait for confirmation before creating any file.

10. **Write the files** — get today's date with `date +%Y-%m-%d`.

    a. **Values file** (`~/ai/kevins-values.md`) — write it only if it was created or changed in
       step 4:

       ```markdown
       # Kevin's Life Values

       The weighted life values used by the `kevins-values-system-decision-matrix` skill.
       Weights must sum to 100. Between 3 and 6 values, per the wiki.

       Source framework: https://old-public-wiki.kevininscoe.com/index.php/Kevins_Values_System_Decision_Matrix

       | Value | Weight |
       |---|---|
       | <value> | <weight> |
       | **Total** | **100** |

       Last updated: YYYY-MM-DD
       ```

    b. **Decision record** — create `~/Journal/personal-journal/DECISIONS/` if it does not exist,
       along with a short `README.md` in it saying what the folder holds and naming this skill.
       Then write `DECISIONS/YYYY-MM-DD-<slug>.md`, where `<slug>` is the decision description
       lowercased, spaces and punctuation replaced with hyphens, hyphens collapsed:

       ```markdown
       ---
       title: "<DECISION>"
       type: decision
       tags: [decision, values-filter]
       quadrant: <required-urgent | required-non-urgent | values | fun-and-fulfilling>
       verdict: <commit | commit-behind-required | park | drop | do-within-budget | not-today>
       covey_priority: <e.g. B1, or omit>
       value_score: <number, or omit>
       cost_score: <number, or omit>
       net_value: <number, or omit>
       due: YYYY-MM-DD
       date_created: YYYY-MM-DD
       date_last_edited: YYYY-MM-DD
       ---

       # <DECISION>

       ## What was being decided

       <the corrected description from step 2, and the options from step 3>

       ## Quadrant

       <which quadrant, and the reasoning that put it there>

       ## Scoring

       <the weighted table — value, weight, score, weighted contribution — then Value Score,
       Cost Score, and Net Value. Omit this section entirely for Required quadrants.>

       ## Verdict

       <the verdict, the Covey priority, and the hard due date>

       ## Sensitivity

       <which value drives the result, and whether ±1 on it flips the verdict. Omit if unscored.>

       ## Review

       <re-evaluation date, for parked items only>
       ```

    c. If the verdict is a commitment, offer to add a matching Obsidian Tasks line to the vault's
       `TODO/todo-today.md` in the plugin's format, e.g.
       `- [ ] <task> ➕ YYYY-MM-DD 📅 <due date>`. Ask first; do not add it unprompted.

11. **Commit** — commit the two repos separately, and **ask before each**:

    - `~/Journal/personal-journal/` — stage only the decision record, the `DECISIONS/README.md`
      if newly created, and `TODO/todo-today.md` if step 10c was accepted. Never `git add -A`.
      Commit as `docs: add decision record <slug>` and push.
    - `~/ai/` — only if the values file changed. `~/ai` is on the confirm-before-commit list in
      `~/skills/CLAUDE.md`, so **ask the human explicitly** before staging. Stage only
      `kevins-values.md`. Commit as `docs: update life values weights` and push.

    Report both commit hashes.

12. **Report** — lead with what was decided and why, then give the record path, the verdict, the
    Covey priority, the due date, and the commit hashes.

## Success Criteria

- The human was asked to describe the decision in their own words, and any spelling or grammar
  problems were challenged before proceeding
- Every question in steps 4–7 was asked **one at a time**, with an answer received before the next
- The item was placed in exactly one of the four quadrants, and the placement was justified
- Weighted scoring ran if — and only if — the item landed in `Decisions / Values`
- Weights in `VALUES_FILE` sum to exactly 100, across 3 to 6 values
- The scoring table is shown to the human, not just the final number
- Anything not dropped or parked carries a **hard due date** supplied by the human
- The decision record exists at `~/Journal/personal-journal/DECISIONS/YYYY-MM-DD-<slug>.md` with
  complete frontmatter
- Nothing was committed in `~/ai/` without explicit confirmation

## Notes

- **"Drop it" is a success, not a failure.** The wiki is explicit that this system exists to
  remove tasks: *"Unlike Covey I am not assuming everything must get done here, even eventually."*
  Do not soften a `Drop` verdict into a `Park` to be agreeable.
- **Required means required.** If the human says something is Required, do not score it against
  their values and do not argue it down. The wiki calls it *"not negotiable."* Scoring a Required
  task is a misuse of the filter.
- **The Values quadrant is the leftovers.** By construction, something reaches it only because it
  fit none of the other three. If an item looks like it belongs in two quadrants, work through the
  columns in order — Required beats Your Decision, and Urgent beats Non-Urgent.
- **Fun and Fulfilling is necessary, not indulgent.** The wiki is clear it is needed time. The
  only constraint on it is the daily budget.
- The framework is embedded in this file so the skill works offline. To check the wiki for
  changes: `curl -sL "https://old-public-wiki.kevininscoe.com/index.php?title=Kevins_Values_System_Decision_Matrix&action=raw"`
- Related wiki pages: *Time Management*, *How I work*, *Life Plan*.
- Source books behind the framework: *Getting Things Done* (David Allen), *The 7 Habits of Highly
  Effective People* and *First Things First* (Stephen Covey), *The One Minute Manager*
  (Ken Blanchard).
- Related skills: `human-todos` and `os-todo` (where a committed decision ends up as a task),
  `today` (the daily walkthrough that will surface the due date).
