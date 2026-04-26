---
name: check-for-or-upgrade-docker-containers-on-this-system
description: Checks the current version or SHA of Docker images in the containers I have setup and reports if an upgrade can be performed and what version going to what upgrade version
---

# Check for and Upgrade Docker Container Images

> Run the container update check script, report which images have updates available, ask the user which containers to update, then apply the selected updates following each container's documented procedure.

## Prerequisites

- `skopeo` installed (`skopeo --version`)
- Docker Engine running (`sudo docker ps`)
- `/usr/local/sbin/automation/check-container-updates.sh` present and executable
- `/opt/containers/UPDATE.md` present (per-container update procedures)
- `sudo` access (required to restart systemd services and run Docker commands)

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `CONTAINERS` | Comma-separated list of container names to check/update, or `all` | `all` |

_Omit CONTAINERS to check and offer updates for all containers._

## Instructions

1. Run the update check script and capture its output:
   ```bash
   sudo bash /usr/local/sbin/automation/check-container-updates.sh 2>&1
   ```

2. Parse the output. Collect every line tagged `[UPDATE]` — these are containers where the remote digest differs from the local image. Also note any `[NEW]` lines (image exists remotely but not pulled locally). Ignore `[OK]` and `[SKIP]` lines.

3. If no `[UPDATE]` or `[NEW]` lines exist, report "All containers are up to date." and stop.

4. For each container with an `[UPDATE]` or `[NEW]`, look up the current and available versions:
   ```bash
   # Current local image reference and version label
   sudo docker inspect <name> --format '{{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.version"}}'
   # Remote image version (use the image reference from above)
   skopeo inspect docker://<image-ref> | python3 -c "import json,sys; d=json.load(sys.stdin); v=d.get('Labels',{}).get('org.opencontainers.image.version','') or d.get('Labels',{}).get('build_version','') or d['Digest'][:19]; print(v)"
   ```
   Use whatever version info is available — OCI version label preferred, short digest as fallback.

5. Present the results to the user in a clear table with columns: **Container**, **Current Version**, **New Version**, **Notes**:
   - Populate Current Version and New Version from step 4 (show short digest if no version label is available)
   - Add a note in the Notes column if the container has special post-update requirements (see Notes section)
   - Ask: "Which containers would you like to update? Reply with a comma-separated list of names, `all`, or `none`."

6. Wait for the user's reply. If the user says `none`, stop.

7. For each container the user selected, apply the update using the procedure in `/opt/containers/UPDATE.md`. Read that file first, then follow the container's specific section. The general pattern for most containers is:
   ```bash
   cd /opt/containers/<name>
   sudo docker compose pull
   sudo systemctl restart <name>
   ```

8. For containers with special post-update requirements, perform the additional steps documented below **after** restarting the service:

   **openbao** — The container starts sealed after every restart. After `systemctl restart openbao`, unseal manually with 3 of the 5 unseal keys. Ask the user to provide 3 unseal keys, then run:
   ```bash
   docker exec -e BAO_ADDR=http://127.0.0.1:8200 openbao bao operator unseal <key-1>
   docker exec -e BAO_ADDR=http://127.0.0.1:8200 openbao bao operator unseal <key-2>
   docker exec -e BAO_ADDR=http://127.0.0.1:8200 openbao bao operator unseal <key-3>
   curl -s https://openbao.kevininscoe.com/v1/sys/health | python3 -m json.tool
   ```
   Confirm `"sealed": false` before proceeding.

   **youtrack** — After restart, wait for the migration to complete before declaring success. Poll until ready:
   ```bash
   sudo docker logs youtrack --tail 20 -f
   ```
   Wait until the log contains "YouTrack is ready" (can take 60–90 seconds, longer after a version upgrade with DB migration).

   **wikijs** — After restart, wait ~60 seconds before health-checking. Wiki.js runs a DB migration on first start of a new version.

   **woodpecker-server / woodpecker-agent** — Both are managed as one unit (`woodpecker-ci`). **Do not use the `v3` rolling tag** — it can point to a broken `next` dev build. Before pulling, check the latest stable release at https://github.com/woodpecker-ci/woodpecker/releases and pin both images to the specific `vX.Y.Z` tag in `/opt/containers/woodpecker-ci/docker-compose.yml`. Then:
   ```bash
   cd /opt/containers/woodpecker-ci
   sudo docker compose pull
   sudo systemctl restart woodpecker-ci
   ```

9. After each container update, verify the service is healthy:
   - Check `sudo docker ps --filter name=<container> --format 'table {{.Names}}\t{{.Status}}'` — status should be `Up ... (healthy)` or `Up ...`
   - Run the health check for that container as documented in its `RUNBOOK.md` or `UPDATE.md`

10. Report a final summary table: **Container**, **From Version**, **To Version**, **Status** (Updated / Failed / Skipped).

11. Re-run the update check script to confirm all updated containers are now current:
    ```bash
    sudo bash /usr/local/sbin/automation/check-container-updates.sh 2>&1
    ```
    All previously-updated containers should now show `[OK]`. If any still show `[UPDATE]`, flag them for the user.

## Success Criteria

- The check script runs without error and produces output for all containers
- Each selected container shows `Up` status in `docker ps` after the update
- No container health check returns an error or non-200 HTTP status
- openbao (if updated) shows `"sealed": false` after unsealing
- youtrack (if updated) shows "YouTrack is ready" in logs before the skill completes

## Notes

- **Kasm** is not managed by Docker Compose and is not included in the check script. Kasm upgrade requires running its own installer (`sudo bash kasm/install.sh --upgrade`). See `/opt/kasm/RUNBOOK.md` for the full procedure — do not attempt it as part of this skill.
- **Pinned containers** (youtrack, woodpecker) require manual tag updates in `docker-compose.yml` before pulling. The check script marks these `[SKIP]` by default — if you want to upgrade them, update the tag first, then re-run.
- **SELinux**: After a Fedora major upgrade, containers using `security_opt: label:disable` (karakeep, n8n, openbao, woodpecker-agent) may need revalidation. If a container fails to start after an update, check `sudo ausearch -m avc -ts today`.
- **backup.sh SELinux labels**: If container backup timers fail after a system upgrade, re-apply `bin_t` label: `sudo chcon -t bin_t /opt/containers/<name>/backup.sh`
- Read `/opt/containers/UPDATE.md` for the full per-container update procedures, release page URLs, and notes on containers with special requirements.
