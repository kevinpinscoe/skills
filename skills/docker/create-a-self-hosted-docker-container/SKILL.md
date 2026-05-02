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
- Linode DNS API key at `~/.secrets/linode.ini`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `SERVICE_NAME` | Name of the new service — used as container directory name, DNS subdomain (`<name>.kevininscoe.com`), and backup path | _(required — ask the user)_ |
| `DOCS_URL` | URL of the official documentation for the software being installed (e.g. Docker Hub page, project README, or official install guide) — used when writing RUNBOOK.md and configuring the container | _(required — ask the user)_ |

## Instructions

1. Read `~/ai/directives/when-creating-a-docker-container-for-self-hosting.md` in full before taking any action.

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

## Success Criteria

- Service is reachable at `https://<service-name>.kevininscoe.com` and returns a non-error HTTP response (verified with `curl` from the Apache host)
- No unresolved SELinux AVC denials related to the new container (per directive Step 11)
- `RUNBOOK.md` and `AGENTS.md` created in `/opt/containers/<service-name>/`
- Backup job runs successfully at least once manually and is added to `~/admin/check-all-backups.sh` (if the container holds persistent data)
- DNS CNAME `<service-name>.kevininscoe.com` resolves correctly

## Notes

- The directive at `~/ai/directives/when-creating-a-docker-container-for-self-hosting.md` is the authoritative source for all creation steps and standards. Always read it in full before starting.
- Use `sudo -A` (not plain `sudo`) for all file operations under `/opt/containers/`, which is root-owned.
- Docker Compose only — no bare `docker run` commands.
- Secrets and credentials go in `.env` files. Never hardcode them.
