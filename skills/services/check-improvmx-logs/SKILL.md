---
name: check-improvmx-logs
description: Queries the ImprovMX API for email delivery logs for a domain and displays status, sender, recipient, and timestamps.
---

# Check ImprovMX Email Logs

> Query the ImprovMX API for recent email delivery logs for a domain and report delivery status, sender, recipient, and any errors.

## Prerequisites

- `bao` CLI accessible and authenticated (`bao kv get -mount=app unclutter-smtp-creds` must succeed)
- `curl` and `python3` available on this host
- ImprovMX API key stored in OpenBao at `app/improvmx-api-key` field `key`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `DOMAIN` | Domain to query logs for | `getunclutter.com` |
| `PAGE` | Page number for pagination | `1` |

## Instructions

1. **Retrieve API key** — read the key field from OpenBao:
   ```bash
   bao kv get -field=key -mount=app improvmx-api-key
   ```
   Store as `API_KEY`.

2. **Query the logs API** — call ImprovMX using Basic auth (`api` as username, `API_KEY` as password):
   ```bash
   curl -s -u "api:${API_KEY}" \
     "https://api.improvmx.com/v3/domains/${DOMAIN}/logs?page=${PAGE}" \
     | python3 -m json.tool
   ```

3. **Parse and display results** — from the JSON response extract each log entry and present a table with columns:
   - **Time** — human-readable local time from the `created` timestamp (milliseconds — divide by 1000)
   - **From** — sender address (`email.from` or `alias`)
   - **To** — recipient (`forward`)
   - **Status** — delivery status (`status` field)
   - **Events** — last event type/message from the `events` array (if present)

   If `logs` is empty, report "No logs found for `{DOMAIN}` — ImprovMX has not received any messages."

4. **Report totals** — show `total` count and which page was returned. If `total > 25` (default page size), offer to fetch the next page.

5. **Flag delivery failures** — if any entry has a status other than `DELIVERED`, highlight it and show the full `events` array for that entry to expose error details.

## Success Criteria

- API call returns HTTP 200 with a `logs` array (even if empty)
- Table is printed with at least Time, From, To, and Status columns
- Any non-DELIVERED entries are clearly flagged

## Notes

- ImprovMX API base URL: `https://api.improvmx.com/v3/`
- Logs endpoint: `GET /domains/{domain}/logs?page={n}`
- Auth: HTTP Basic, username `api`, password = ImprovMX API key
- ImprovMX API key is stored at `app/improvmx-api-key` field `key` in OpenBao
- Default page size is 25 entries; use `?page=N` to paginate
- If the API returns 401, the API key may be wrong or the domain may not be on this ImprovMX account
