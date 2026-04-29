---
name: read-my-gmail-for-tldr-articles
description: Scans Gmail for TLDR newsletter emails and saves non-sponsored articles to the daily journal file.
---

# Read My Gmail for TLDR Articles

> Scans the Gmail inbox for TLDR newsletter emails from the last day, extracts non-sponsored article paragraphs (including Quick Links), deduplicates across all emails, and writes them to a dated Markdown file in the Personal Journal with read-tracking checkboxes.

## Prerequisites

- Gmail MCP (`mcp__claude_ai_Gmail__*`) must be authenticated
- Journal directory `~/Journal/Personal Journal/DAILY/` must exist (create it if not)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `LOOKBACK_DAYS` | How many days back to search Gmail for TLDR emails | `1` |

## Instructions

1. **Search Gmail for TLDR emails** — call `mcp__claude_ai_Gmail__search_threads` with query:
   ```
   from:@tldrnewsletter.com newer_than:{LOOKBACK_DAYS}d
   ```
   Expect 5–8 threads per day covered. If none are found, report "No TLDR emails found in the last {LOOKBACK_DAYS} day(s)" and stop.

2. **Group threads by received date** — use each message's received date (not today's date) to determine which daily file it belongs to. Group all thread IDs by their `MM-DD-YYYY` received date. Each date will produce one output file: `~/Journal/Personal Journal/DAILY/TLDR-<MM-DD-YYYY>.md`.

3. **Process each date group independently** — for each date, work through steps 4–8 below. This means a 7-day lookback produces up to 7 separate files, one per day.

4. **Set output path for the current date** — the output file is `~/Journal/Personal Journal/DAILY/TLDR-<MM-DD-YYYY>.md` where the date matches the emails' received date. If the file already exists, read its existing `##`-level headings to seed the deduplication set for this date. If it does not exist, create it with a single `# TLDR <MM-DD-YYYY>` heading line, then proceed.

5. **Fetch each thread** — for each thread ID in the current date group, call `mcp__claude_ai_Gmail__get_thread` to retrieve the full message body. Use the `plaintextBody` field — these emails always have a usable plaintext body.

6. **Parse the link reference table** — at the bottom of each email body is a `Links:` block in the form:
   ```
   Links:
   ------
   [1] https://...
   [2] https://...
   ```
   Parse this into a map of `N → URL` before processing articles. You will use this map to resolve article links in step 7.

7. **Extract non-sponsored articles** — scan the body for article entries. Each entry follows this pattern:
   - **Title line**: ALL-CAPS text (possibly with leading whitespace), ending with `[N]` where N is the link reference number. May include a descriptor like `(4 MINUTE READ)`, `(WEBSITE)`, or `(GITHUB REPO)` before `[N]`.
   - **Body**: one or more lines of descriptive text immediately following a blank line after the title line, ending at the next blank line.

   **Skip these entries:**
   - Any title that contains `(SPONSOR)` — this marks paid sponsor content.
   - The `TOGETHER WITH [sponsor]` block near the top of the email — skip it entirely.
   - Navigation lines: `Sign Up`, `Advertise`, `View Online`, `Love TLDR?`, `Want to advertise`, `Want to work at TLDR?`, referral links, and unsubscribe footers.

   **Include** articles from all named sections: `HEADLINES & LAUNCHES`, `ARTICLES & TUTORIALS`, `DEEP DIVES & ANALYSIS`, `ENGINEERING & RESEARCH`, `OPINIONS & ADVICE`, `LAUNCHES & TOOLS`, `MISCELLANEOUS`, and `QUICK LINKS`.

   For each qualifying article, capture:
   - **Title**: the ALL-CAPS title text, stripped of the descriptor suffix (e.g. `(4 MINUTE READ)`) and `[N]`, converted to sentence case (capitalize only the first word and proper nouns).
   - **URL**: resolved from the link reference map using N.
   - **Body**: the descriptive paragraph text.

8. **Deduplicate** — maintain a set of article titles seen so far for the current date (seeded from any `##` headings already in the output file from step 4). If the same article title appears in multiple emails for the same day, keep only the first occurrence and skip all subsequent ones silently.

9. **Append articles to journal file** — for each qualifying, non-duplicate article, append to the current date's output file:
   ```markdown
   ## <Article Title>

   - [ ] [<Article Title>](<URL>)

   <Article body text>
   ```
   Separate each article block with a blank line. The `- [ ]` checkbox lets you mark articles as read throughout the day.

10. **Append run summary** — at the end of each day's output file, append a horizontal rule and a summary section:
    ```markdown
    ---

    ## Run summary

    | | Count |
    |---|---|
    | Editions scanned | N (e.g. TLDR, TLDR Dev, TLDR AI) |
    | Non-sponsored articles found | N |
    | Articles written | N |
    | Duplicates skipped | N (list titles if any) |
    ```
    Also print this summary to the console after each file is written.

11. **Label all processed threads** — after all date groups have been processed (all output files written), ensure the Gmail labels `claude` and `tldr` exist by calling `mcp__claude_ai_Gmail__list_labels` and creating any that are missing with `mcp__claude_ai_Gmail__create_label`. Then call `mcp__claude_ai_Gmail__label_thread` for every thread ID found in step 1, applying both labels to each thread.

12. **Archive all processed threads** — for each thread ID found in step 1, call `mcp__claude_ai_Gmail__unlabel_thread` with label name `INBOX` to remove it from the inbox (this is the Gmail archive action). Do this after labeling in step 11.

## Success Criteria

- One `TLDR-<MM-DD-YYYY>.md` file exists per day of emails found within the lookback window.
- Each file's date matches the received date of the emails it was built from, not the date the skill was run.
- Each file contains one `##`-level section per qualifying article.
- Each section has a `- [ ]` checkbox line with a clickable Markdown link, followed by the article body text.
- Article headings are sentence-cased and do not include read-time or format descriptors.
- No `(SPONSOR)` articles or `TOGETHER WITH` sponsor blocks appear in any output file.
- No duplicate article sections exist within a single day's file.
- Each output file ends with a `## Run summary` section showing editions scanned, articles written, and duplicates skipped.
- The same summary is printed to the console.
- All processed threads have both the `claude` and `tldr` Gmail labels applied.
- All processed threads are archived (removed from inbox).

## Notes

- This skill is safe to re-run for the same day — articles already present in the file are detected via heading deduplication and skipped, so no duplicates are created.
- Running with `LOOKBACK_DAYS=7` will create up to 7 daily files, one per day of emails found. Each file is only written once per day; re-running just fills in any gaps.
- TLDR publishes several topic-specific newsletters (TLDR AI, TLDR Dev, TLDR DevOps, etc.); all share the `tldrnewsletter.com` sender domain and are combined into a single flat file per day.
- If the `DAILY/` directory does not exist, create it before writing any output file.
- Quick Links section items are shorter (1–3 sentences) but are included — they are real articles, just briefer.
