---
name: create-a-self-hosted-docker-container
description: Creates a new self-hosted Docker container service under /opt/containers, including DNS record, TLS certificate, Apache proxy, optional backup job, SELinux audit, and full documentation.
---

# Create a Self-Hosted Docker Container

> Follow the container creation directive to set up a new Docker-based service on this host end-to-end: directory, DNS, TLS, Apache proxy, optional backup job, SELinux audit, and RUNBOOK.md + AGENTS.md documentation.

## Prerequisites

- Docker Engine running (`sudo docker ps`)
- `sudo -A` access configured (stored askpass in place)
- `~/tools/free-port` present and executable
- `~/admin/create-kevin-dns-alias.sh` present
- `~/admin/certbot-request.sh` present
- Linode DNS API key (certbot-dns-linode format) at `~/.secrets/certbot.ini`
- Linode Personal Access Token at `~/.secrets/kevin-linode.pat`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SERVICE_NAME` | Name of the new service — used as container directory name, DNS subdomain (`<name>.kevininscoe.com`), and backup path | _(required — ask the user)_ |
| `DOCS_URL` | URL of the official documentation for the software being installed (e.g. Docker Hub page, project README, or official install guide) — used when writing RUNBOOK.md and configuring the container | _(required — ask the user)_ |

## Instructions

1. Read `~/ai/directives/when-self-hosting-a-docker-container.md` in full before taking any action.

2. Ask the user for the service name if not already provided. Then ask for the documentation URL. Confirm both before proceeding.

3. Follow the directive's Steps 1–13 in order. Do not skip steps or deviate from any practice without flagging it to the user and getting explicit approval first.

4. After all files under `/opt/containers/<service-name>/` have been created or modified, ensure the `/opt/containers` repo git-tracks them:
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
     cd /opt/containers
     git add <service-name>/*.md <service-name>/*.yml <service-name>/*.sh \
             <service-name>/*.service <service-name>/*.timer \
             <service-name>/scripts/ 2>/dev/null || true
     git commit -m "chore(<service-name>): track config, scripts, and docs"
     git push
     ```
   - Confirm the push succeeded and the files appear in `git log --stat HEAD`.

5. **Register the FQDN on the tool-shed dashboard** (`~/Projects/private/tool-shed`). Only do this once the service is verified reachable at `https://<service-name>.kevininscoe.com` and has been tested.
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

6. **Add the FQDN to Uptime Kuma monitoring** (`~/Projects/private/observability`). Default to an `http`-type monitor.
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

- Service is reachable at `https://<service-name>.kevininscoe.com` and returns a non-error HTTP response (verified with `curl` from the Apache host)
- No unresolved SELinux AVC denials related to the new container (per directive Step 11)
- `RUNBOOK.md` and `AGENTS.md` created in `/opt/containers/<service-name>/`
- Backup job runs successfully at least once manually and is added to `~/admin/check-all-backups.sh` (if the container holds persistent data)
- DNS CNAME `<service-name>.kevininscoe.com` resolves correctly
- A tile for the service appears in `~/Projects/private/tool-shed/src/services.ts`, `pnpm build` passes, and the change is pushed to `main` and tagged with the next semver patch (tag pushed to origin)
- An `http` monitor for the FQDN exists in `~/Projects/private/observability/configs/central-stack/uptime-kuma/monitors.yaml`, has been applied live to `uptime.kevininscoe.com` (green in the Kuma UI), and the YAML is committed and pushed

## Notes

- The directive at `~/ai/directives/when-self-hosting-a-docker-container.md` is the authoritative source for all creation steps and standards. Always read it in full before starting.
- Use `sudo -A` (not plain `sudo`) for all file operations under `/opt/containers/`, which is root-owned.
- Docker Compose only — no bare `docker run` commands.
- Secrets and credentials go in `.env` files. Never hardcode them.
- Steps 5 and 6 touch two separate repos outside `/opt/containers`: the dashboard is `~/Projects/private/tool-shed` (data-driven from `src/services.ts`; see its CLAUDE.md), and the monitoring source of truth is `~/Projects/private/observability` (`configs/central-stack/uptime-kuma/monitors.yaml`; sync procedure in `runbooks/uptime-kuma/RUNBOOK.md`). Only run these two steps after the container is up, has its FQDN, and has been tested.
