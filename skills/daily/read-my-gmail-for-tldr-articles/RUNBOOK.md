# Runbook: read-my-gmail-for-tldr-articles

## Purpose

Runs the `read-my-gmail-for-tldr-articles` skill daily at 10:30am. Searches Gmail for TLDR newsletter emails from that day, extracts non-sponsored articles (including Quick Links), deduplicates across all editions, and writes a dated Markdown file with read-tracking checkboxes to `~/Journal/Personal Journal/DAILY/TLDR-MM-DD-YYYY.md`.

## Stack

- **Runtime**: Bash (`run.sh`) invoking Claude Code CLI (`~/.local/bin/claude`)
- **Skill prompt**: `SKILL.md` in this directory
- **Gmail access**: Gmail MCP (`mcp__claude_ai_Gmail__*`) — credentials managed by the MCP server
- **Output**: Obsidian vault at `~/Journal/Personal Journal/DAILY/`

## Unit file locations

| File | Installed path | Collection point copy |
|---|---|---|
| Service | `~/.config/systemd/user/read-my-gmail-for-tldr-articles.service` | `./read-my-gmail-for-tldr-articles.service` |
| Timer | `~/.config/systemd/user/read-my-gmail-for-tldr-articles.timer` | `./read-my-gmail-for-tldr-articles.timer` |

## Timer schedule

`OnCalendar=*-*-* 10:30:00` — every day at 10:30am local time. `Persistent=true` means if the machine was off at 10:30am, the job will run once on next boot.

## User

Runs as `kinscoe` (user service). The Claude Code CLI and Gmail MCP credentials are scoped to this user.

> **Note:** This must be a user service (`~/.config/systemd/user/`), not a system service (`/etc/systemd/system/`). A system service with `User=kinscoe` cannot execute scripts from `/home/` under SELinux enforcing mode — the `user_home_t` context is silently denied by a `dontaudit` rule with no AVC logged.

## WorkingDirectory

Not set. `run.sh` derives its own path via `${BASH_SOURCE[0]}`, so it works regardless of working directory.

## Environment / secrets

No `EnvironmentFile`. Gmail MCP credentials are managed by the MCP server and stored in the user's MCP configuration — do not hardcode tokens in the unit file or `run.sh`.

## Installation (first-time setup)

```sh
SKILL_DIR=/home/kinscoe/skills/skills/daily/read-my-gmail-for-tldr-articles

chmod +x "$SKILL_DIR/run.sh"

cp "$SKILL_DIR/read-my-gmail-for-tldr-articles.service" ~/.config/systemd/user/
cp "$SKILL_DIR/read-my-gmail-for-tldr-articles.timer"   ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now read-my-gmail-for-tldr-articles.timer
```

After any change to the unit files in this directory, re-copy and reload:

```sh
cp "$SKILL_DIR/read-my-gmail-for-tldr-articles.service" ~/.config/systemd/user/
cp "$SKILL_DIR/read-my-gmail-for-tldr-articles.timer"   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart read-my-gmail-for-tldr-articles.timer
```

## Enable / disable

```sh
# Enable (start on boot)
systemctl --user enable --now read-my-gmail-for-tldr-articles.timer

# Disable (stop scheduled runs)
systemctl --user disable --now read-my-gmail-for-tldr-articles.timer
```

## Start / stop

```sh
# Run immediately without waiting for 10:30am
systemctl --user start read-my-gmail-for-tldr-articles.service

# Stop a currently running job
systemctl --user stop read-my-gmail-for-tldr-articles.service
```

## Next trigger

```sh
systemctl --user list-timers read-my-gmail-for-tldr-articles.timer
```

## Health check

After the job runs, verify the output file exists and contains articles:

```sh
ls -lh ~/Journal/Personal\ Journal/DAILY/TLDR-$(date +%m-%d-%Y).md
grep -c '^## ' ~/Journal/Personal\ Journal/DAILY/TLDR-$(date +%m-%d-%Y).md
```

The article count should be 40–60 on a normal day across all TLDR editions.

## Logs

```sh
# Most recent run
journalctl --user -u read-my-gmail-for-tldr-articles.service -n 100

# Follow in real time
journalctl --user -u read-my-gmail-for-tldr-articles.service -f

# All historical runs
journalctl --user -u read-my-gmail-for-tldr-articles.service
```

## Monitoring

No external monitoring configured. Check logs and output file after the first few automated runs to confirm correct behavior.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No output file created | Gmail MCP auth expired | Re-authenticate Gmail MCP interactively, then restart the service |
| Output file has 0 articles | TLDR emails not yet delivered at 10:30am | Run manually later in the day; emails typically arrive 11am–2pm |
| Timer not firing | Machine was off; `Persistent=true` will catch up on next boot | Check `systemctl --user list-timers` |
| Permission denied on run.sh | Installed as system service instead of user service | Remove from `/etc/systemd/system/`, install to `~/.config/systemd/user/`, reload with `systemctl --user` |
| Claude CLI not found | Path issue in non-interactive shell | Confirm `~/.local/bin/claude` exists; update `run.sh` if path changed |

## Additional notes

- The skill uses `LOOKBACK_DAYS=1` by default — it only processes that day's emails. To backfill missing days run the service manually after temporarily editing `run.sh` to pass a larger lookback value to the `-p` prompt.
- Re-running for the same day is safe — existing article headings are used as the deduplication seed, so no duplicate sections are created.
