# Put Email Offers on My Calendar

> Scans the Gmail inbox for promotional offers and deal emails, then creates all-day Google Calendar events on Kevin's personal calendar covering the offer's validity window.

## Prerequisites

- Gmail MCP (`mcp__claude_ai_Gmail__authenticate`) must be authenticated
- Google Calendar MCP (`mcp__claude_ai_Google_Calendar__*`) must be authenticated
- Target calendar ID: read from `~/.config/skills/google/calendar/personal`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `LOOKBACK_DAYS` | How many days back to search Gmail for offer emails | `3` |

## Instructions

1. **Authenticate** — call `mcp__claude_ai_Gmail__authenticate` and `mcp__claude_ai_Google_Calendar__gcal_list_calendars` to confirm both connections are live. If either fails, stop and report the error.

2. **Fetch offer emails** — search Gmail for messages received within the last `LOOKBACK_DAYS` days that look like promotional offers. Use **two** searches and combine the results (deduplicating by thread ID):
   - **Subject search**: `subject:(sale OR offer OR discount OR coupon OR savings OR deal OR "valid until" OR expires OR "limited time" OR rebate OR refund OR tires OR tyre OR auto OR clearance OR "free item" OR "buy one" OR financing OR "special financing" OR fest OR springfest OR fallfest OR summerfest)`
   - **Body search**: `(sale OR offer OR discount OR coupon OR savings OR "valid until" OR "offer valid till" OR expires OR "limited time" OR rebate OR financing) newer_than:{LOOKBACK_DAYS}d` — this catches promotional emails whose subject lines don't contain obvious offer keywords but whose bodies do
   - **HTML-only emails**: some emails have no usable plaintext body (the body contains only a "view in browser" link). For these, evaluate the subject line alone using the expanded keyword list above — do not skip them just because the body is empty.
   - Focus on retail/service offers: store credit, percentage-off discounts, dollar-off discounts, free items, parking-lot sales, in-store clearance events, ITC sales, Harbor Freight sales, tire/auto deals, tax-season savings, etc.
   - Exclude purely transactional emails (order confirmations, shipping notices, receipts) unless they contain a separate promotional offer.

3. **Extract offer details** from each qualifying email. For each offer, identify:
   - **Title** — short, human-readable name (e.g. "Harbor Freight ITC Sale", "Firestone Tire Savings up to $300")
   - **Start date** — the first day the offer is valid. If not explicitly stated, use the email's received date.
   - **End date** — the last day the offer is valid (the "valid until" / expiry date). If no explicit end date is stated in the email, you MUST default to exactly 7 days after the email's received date — do not infer end dates from context clues like "end of month", "April savings", or similar phrasing. Note this assumption in the event description.
   - **Description** — a concise summary of what the offer includes (bullet points are fine), plus the sender/brand name and any promo codes.

4. **Deduplicate** — before creating any event, call `mcp__claude_ai_Google_Calendar__gcal_list_events` on the target calendar for the relevant date range and check whether an event with the same title already exists. If a matching event is found, report it as Skipped-duplicate in the summary and do nothing — do not update, modify, or delete the existing event.

5. **Create calendar events** — for each new offer, call `mcp__claude_ai_Google_Calendar__gcal_create_event` with:
   - `calendarId`: read from `~/.config/skills/google/calendar/personal`
   - `summary`: the offer title from step 3
   - `start`: `{ "date": "<YYYY-MM-DD>" }` (all-day, no time)
   - `end`: `{ "date": "<YYYY-MM-DD>" }` — Google Calendar all-day end dates are **exclusive**, so use the day *after* the last valid day (e.g. if valid until 4/19/2026, set end to 4/20/2026)
   - `description`: the offer description from step 3, including any promo codes and the assumption note if the end date was inferred

6. **Report results** — after processing all emails, output a summary table:
   - Columns: Email Sender | Offer Title | Start | End | Status (Created / Skipped-duplicate / Skipped-no-dates)
   - Note any emails that appeared promotional but could not be parsed reliably.

## Success Criteria

- All qualifying offer emails within the lookback window have a corresponding all-day event on the target calendar (or are listed as Skipped-duplicate).
- Each event spans the correct validity window (start → day-after-end for Google's exclusive-end convention).
- No duplicate events are created for offers already on the calendar.
- A summary table is printed at the end of the run.

## Notes

- **Offer types to recognize**: store credit offers, percentage/dollar-off discounts, free item with purchase, parking lot sales, ITC (Inside Track Club) sales at Harbor Freight, limited-time price drops, auto/tire rebate offers, and similar retail promotions.
- **Ambiguous end dates**: if no explicit expiry date is found, always default to exactly 7 days after the email's received date — never infer an end date from the offer's name, month name, season, or any other contextual clue. Document the assumption in the event description.
- **Forwarded accounts**: multiple people's email accounts are forwarded to this inbox. Process offer emails regardless of who the original recipient was — do not filter or skip based on the `to:` address.
- **Refinement expected**: the extraction heuristics will need tuning over time as new offer formats appear. When an email is skipped due to parse failure, include enough detail in the report so the skill can be improved.
- This skill is intended to be run periodically (e.g. weekly). Consider pairing it with the `schedule` or `loop` skills for automation.
