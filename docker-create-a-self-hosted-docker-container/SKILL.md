---
name: docker-create-a-self-hosted-docker-container
category: docker
description: Creates a new self-hosted Docker container service under /home/containers, including DNS record, TLS certificate, Apache proxy, optional backup job, SELinux audit, and full documentation.
disable-model-invocation: true
---

# Create a Self-Hosted Docker Container

> Follow the container creation directive to set up a new Docker-based service on this host end-to-end: directory, DNS, TLS, Apache proxy, optional backup job, SELinux audit, and RUNBOOK.md + AGENTS.md documentation.

## Prerequisites

- Docker Engine running (`sudo docker ps`)
- `sudo -A` access configured (stored askpass in place)
- `~/tools/free-port` present and executable
- `~/admin/create-kevin-dns-alias.sh` present
- `~/admin/certbot-request.sh` present
- Linode DNS API key in OpenBao at `linode/api/dns-key`, readable through `parzival`. Neither DNS nor TLS needs a file on disk: `create-kevin-dns-alias.sh` reads the key with `parzival get --as ansible`, and certbot's `linode-creds` pre and post hooks write it to a tmpfs INI and shred it afterwards. `~/.secrets/certbot.ini` and `~/.secrets/kevin-linode.pat` no longer exist.
- On the FLDW only: the YouTrack issue helper `~/Projects/private/youtrack.kevininscoe.com/scripts/yt-issue/run.sh`, `parzival`, and `yt-elapsed`, for the FC issue in Step 3

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SERVICE_NAME` | Name of the new service — used as container directory name, DNS subdomain (`<name>.kevininscoe.com`), and backup path | _(required — ask the user)_ |
| `DOCS_URL` | URL of the official documentation for the software being installed (e.g. Docker Hub page, project README, or official install guide) — used when writing RUNBOOK.md and configuring the container | _(required — ask the user)_ |

## Instructions

1. Read `~/ai/directives/when-self-hosting-a-docker-container.md` in full before taking any action.

2. Ask the user for the service name if not already provided. Then ask for the documentation URL. Confirm both before proceeding.

3. **On the FLDW, file and start an FC issue for the container before any other work.** Run `hostname`. If it does not read `kevin`, skip this step. Otherwise, do this before the directive's Step 1 and before any directory, port, DNS, TLS, proxy, backup, or documentation change:
   - Ask the user whether a YouTrack issue already exists for this container. If they name one, use it and do not create another.
   - Otherwise create one in project **FC** (FLDW - Containers). FC is a standing assignment for this work (`~/ai/directives/when-creating-a-youtrack-ticket.md` §1), so do not ask which project, and running this skill is the user's direction to file it. Follow that directive's §2–§6:
     ```bash
     ~/Projects/private/youtrack.kevininscoe.com/scripts/yt-issue/run.sh create FC \
       --summary "Create self-hosted container <service-name>" --file <description-file> \
       --set "Status=To do" --set Type=Task --set Priority=Normal \
       --set Assignee=Claude_Code --set "Affected host=FLDW" --set "Issue domain=Personal"
     ```
     The description names the service, `DOCS_URL`, and `https://<service-name>.kevininscoe.com`. The helper sets `Date time entered` itself.
   - Hand back the issue's full URL as bare text.
   - Start it now with the directive's §7 start transaction: `yt-elapsed doctor` first, then `Status` to `In Progress`, `yt-elapsed start` with this session's id, the terminal tab and `Ghostty tab name`. If `doctor` refuses, stop and tell the user. Do not create the container without a started issue.
   - Do every later step under this issue. Log each commit made in any repo to it, and write the stop comment (`yt-elapsed stop`) when the work stops.

4. Follow the directive's Steps 1–13 in order. Do not skip steps or deviate from any practice without flagging it to the user and getting explicit approval first.

5. After all files under `/home/containers/<service-name>/` have been created or modified, ensure the `/home/containers` repo git-tracks them:
   - Inspect the repo's `.gitignore` (if it exists). For each of the following patterns that is not already whitelisted, add a negation entry:
     ```
     !*.md
     !*.yml
     !*.sh
     !*.service
     !*.timer
     !scripts/**
     ```
   - Stage, commit, and push all new or modified files matching those patterns in the service subdirectory:
     ```bash
     cd /home/containers
     git add <service-name>/*.md <service-name>/*.yml <service-name>/*.sh \
             <service-name>/*.service <service-name>/*.timer \
             <service-name>/scripts/ 2>/dev/null || true
     git commit -m "chore(<service-name>): track config, scripts, and docs"
     git push
     ```
   - Confirm the push succeeded and the files appear in `git log --stat HEAD`.

6. **Register the FQDN on the tool-shed dashboard** (`~/Projects/private/tool-shed`). Only do this once the service is verified reachable at `https://<service-name>.kevininscoe.com` and has been tested.
   - Ask the user for the card `icon` (emoji), `category`, and a one-sentence `description`. Do not guess these — ask directly.
   - Append a `Service` entry to the `services` array in `src/services.ts`:
     ```ts
     { name: '<Service Name>', description: '<description>', url: 'https://<service-name>.kevininscoe.com', icon: '<emoji>', category: '<category>' },
     ```
     Confirm `<category>` already exists in the `categoryOrder` array; if not, add it there too — a card whose category is missing from `categoryOrder` will not render.
   - Bump the `version` field in `package.json` by one patch level (repo convention: every tile change bumps the version; keep it in lockstep with the tag below).
   - Type-check the build — this is the only gate: `pnpm build` (fails on any `vue-tsc` error).
   - Commit only the changed files and push to `main`:
     ```bash
     cd ~/Projects/private/tool-shed
     git add src/services.ts package.json
     git commit -m "feat(services): add <Service Name> tile; bump <version>"
     git push
     ```
   - Tag the **next available semver patch** and push the tag:
     ```bash
     cd ~/Projects/private/tool-shed
     latest=$(git tag --sort=-v:refname | head -1)   # e.g. v1.1.5
     # Increment ONLY the final (patch) number, keeping the v prefix -> e.g. v1.1.6
     git tag <next-tag>
     git push origin <next-tag>
     ```
     Compute `<next-tag>` from `$latest`. Confirm it does not already exist (`git tag | grep -Fx <next-tag>` returns nothing) before creating it.

7. **Add the FQDN to Uptime Kuma monitoring** (`~/Projects/private/observability`). Default to an `http`-type monitor.
   - Add a monitor entry to the `monitors:` list in `configs/central-stack/uptime-kuma/monitors.yaml`, placing it in the "tool-shed FQDN sites" section to match its dashboard grouping:
     ```yaml
     - name: <service-name>
       type: http
       url: https://<service-name>.kevininscoe.com
     ```
     The shared `defaults:` (interval, `accepted_statuscodes` of 200–399, `telegram-kevin` notification) apply automatically. If the site returns a strict `200` only, add `accepted_statuscodes: ["200-299"]` to the entry.
   - Sync the YAML to `uptime.kevininscoe.com`. Dry-run is the default and changes nothing; `--apply` is what pushes the monitor live (requires OpenBao unsealed and Tailscale up — creds come from OpenBao `observability/uptime-kuma/admin`):
     ```bash
     cd ~/Projects/private/observability
     # One-time only, if .venv is missing:
     # python3 -m venv .venv && ./.venv/bin/pip install -r configs/central-stack/uptime-kuma/requirements.txt
     ./.venv/bin/python scripts/sync-kuma-monitors.py            # preview (dry-run)
     ./.venv/bin/python scripts/sync-kuma-monitors.py --apply    # create the monitor live
     ```
   - Confirm the new monitor goes green in the Kuma UI, then commit and push the YAML so git matches Kuma:
     ```bash
     git add configs/central-stack/uptime-kuma/monitors.yaml
     git commit -m "feat(uptime-kuma): monitor <service-name>.kevininscoe.com"
     git push
     ```

## Success Criteria

- On the FLDW: an FC issue for the container exists, was started (`In Progress`, `yt-elapsed start`) before any container work, and has every commit logged to it
- Service is reachable at `https://<service-name>.kevininscoe.com` and returns a non-error HTTP response (verified with `curl` from the Apache host)
- No unresolved SELinux AVC denials related to the new container (per directive Step 11)
- `RUNBOOK.md` and `AGENTS.md` created in `/home/containers/<service-name>/`
- Backup job runs successfully at least once manually and is added to `~/admin/check-all-backups.sh` (if the container holds persistent data)
- DNS CNAME `<service-name>.kevininscoe.com` resolves correctly
- A tile for the service appears in `~/Projects/private/tool-shed/src/services.ts`, `pnpm build` passes, and the change is pushed to `main` and tagged with the next semver patch (tag pushed to origin)
- An `http` monitor for the FQDN exists in `~/Projects/private/observability/configs/central-stack/uptime-kuma/monitors.yaml`, has been applied live to `uptime.kevininscoe.com` (green in the Kuma UI), and the YAML is committed and pushed

## Notes

- The directive at `~/ai/directives/when-self-hosting-a-docker-container.md` is the authoritative source for all creation steps and standards. Always read it in full before starting.
- `/home/containers` is on the shared `containers` group and setgid, so files and directories are created and committed as `kinscoe` with no `sudo` (directive Step 6). Use `sudo -A` (never plain `sudo`) only where root is genuinely needed: a root-owned directory the service requires, root-owned container volumes, `docker` commands, the backup job (which runs as root), and system files such as systemd units and Apache config.
- Docker Compose only — no bare `docker run` commands.
- Secrets and credentials go in `.env` files. Never hardcode them.
- Steps 6 and 7 touch two separate repos outside `/home/containers`: the dashboard is `~/Projects/private/tool-shed` (data-driven from `src/services.ts`; see its CLAUDE.md), and the monitoring source of truth is `~/Projects/private/observability` (`configs/central-stack/uptime-kuma/monitors.yaml`; sync procedure in `runbooks/uptime-kuma/RUNBOOK.md`). Only run these two steps after the container is up, has its FQDN, and has been tested.
