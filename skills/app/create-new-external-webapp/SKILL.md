---
name: create-new-external-webapp
description: Stands up a brand-new external (public) static brochure website end-to-end on one of Kevin's Linode public web servers — validates DNS, creates the Linode domain + A record, scaffolds a Gitea repo modelled on datagiggle.com, wires Woodpecker CI to build the web-oci-builder OCI image, updates the chosen host's Ansible config, deploys, verifies, and registers the site in the service catalog and Uptime Kuma.
---

# Create a New External Webapp

> Take a new site FQDN from zero to live: confirm the DNS is free, create the Linode domain and A record on the chosen public web server, scaffold a Gitea repo like `datagiggle.com`, wire up Woodpecker CI to build the `web-oci-builder` OCI image and publish it to the Gitea registry, teach the host's `linode-*-config` Ansible about the new site, deploy it, verify it serves over HTTPS, and register it in the service catalog and Uptime Kuma.

## Prerequisites

- `~/ai/directives/root-directive.md` readable — read it first; follow every directive it dispatches that applies to this task (notably `service-catalog.md`, `gitea.md`, `when-building-or-scaffolding-code-in-a-git-repo.md`, `opentofu-iac-standards.md`, `storing-secrets.md`, `when-making-changes-in-a-directory-that-is-also-a-git-repo.md`). **Note:** `portman.md` does **not** apply here — the site's container port lives on the remote Linode web server (e.g. `web1`), not on FLDW, so it is **not** reserved in FLDW's `portman` registry. Derive a free port from the target host's own `linode-<server>-config` Ansible instead (see Step 14).
- `dig` / `host` available (DNS lookups).
- Linode API credentials, located via the **credential map** (`~/.secrets/CREDENTIAL-MAP.md`): the DNS key `~/.secrets/certbot.ini` (`dns_linode_key`, used by the existing `scripts/*dns*.sh` helpers) and/or the account PAT `~/.secrets/kevin-linode.pat` (used by `linode-cli`). **Never read a secret value into a file or the transcript** — pass it through the CLI/API only.
- `tea` CLI authenticated with Gitea (`tea whoami`) and `~/.config/gitea/api` present.
- SSH access to Gitea (`ssh -T git@git.kevininscoe.com -p 2223`) and to the chosen web server over Tailscale.
- The sibling skill `~/skills/skills/git/create-a-repo/SKILL.md` (used verbatim for the repo-creation step).
- Reference project checkouts present locally:
  - `~/Projects/private/datagiggle.com` — the scaffold/brochure/CI template to copy.
  - `~/Projects/private/web-oci-builder` — the buildah-based lighttpd2 OCI builder (the build engine; not modified by this skill).
  - `~/Projects/private/linode-web1-config` and/or `~/Projects/private/linode-mail1-config` — the per-host Ansible config repos.
  - `~/Projects/private/observability/configs/central-stack/uptime-kuma/monitors.yaml` — declarative Uptime Kuma monitors.
- Source-of-truth files (read, never guess around): the **service catalog** `~/Projects/private/fedora-dashboard/kevins-federated-unix-universe-services.md` and the **credential map** `~/.secrets/CREDENTIAL-MAP.md`.
- Woodpecker CI reachable at `https://woodpecker-ci.kevininscoe.com` (repo activation + secrets are done in its UI by the user).

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `FQDN` | Fully-qualified domain of the new external site (e.g. `mynewsite.com`). Becomes the repo name, local clone dir, OCI image basename, and Uptime Kuma monitor name. | _(required — ask the user)_ |
| `WEB_SERVER` | Which public web server hosts the site — one of the Fleet Hosts whose service-catalog **Purpose** is `Linode Public webserver` (currently `web1` or `mail1`). Selects the `linode-<server>-config` repo and the target public IP. | _(required — ask the user)_ |

## Instructions

Follow the global directives: **ask for each required input directly and one at a time**, wait for the answer before the next question, and **confirm before every outward or hard-to-reverse action** (Linode API writes, DNS changes, repo creation, pushes, deploys). Do not infer answers to required inputs.

1. **Read directives** — Read `~/ai/directives/root-directive.md` first and follow what it dispatches. This orchestration touches infra-as-code, Gitea, the service catalog, and secrets, so at minimum honor `service-catalog.md`, `gitea.md`, `when-building-or-scaffolding-code-in-a-git-repo.md`, `opentofu-iac-standards.md`, `storing-secrets.md`, and `when-making-changes-in-a-directory-that-is-also-a-git-repo.md`. Do **not** apply `portman.md`: FLDW's `portman` registry only tracks ports bound on FLDW, and this site's port is bound on the remote Linode web server — pick the port from that host's Ansible config (Step 14), not from `portman`.

2. **Ask for the FQDN** — Ask the user for the FQDN of the new external website. Propose a spelling/grammar correction if the domain looks misspelled (per root-directive), but let the user override. Do not proceed without an explicit FQDN.

3. **Verify the DNS is free** — Look the FQDN up in public DNS:
   ```bash
   dig +short A "$FQDN"; dig +short CNAME "$FQDN"
   ```
   - **No record** → the name is free; continue to Step 4.
   - **A/CNAME exists** → resolve where it points (the A record IP, or the CNAME target and its IP). Compare that IP/host against the **service catalog** (`~/Projects/private/fedora-dashboard/kevins-federated-unix-universe-services.md`) — the `Host FQDN` column and the fleet hosts' public IPs.
     - If the destination **is** a known k-fed host (e.g. it already resolves to `web1`/`mail1`), report this to the user and ask whether to continue (the site may be a re-run/partial state) — do not silently proceed.
     - If the destination is **not** in the service catalog, **STOP**: flag it to the user as an error ("`$FQDN` already resolves to `<ip/host>`, which is not in the service catalog") and **await further instructions**. Do not create anything.

4. **Ask which public web server hosts the site** — Read the **Fleet Hosts** table of the service catalog and list the rows whose **Purpose** column contains `Linode Public webserver` (today: `web1.network.kevininscoe.com` → public `web1.kevininscoe.com`; `mail1.network.kevininscoe.com` → public `mail1.kevininscoe.com`). Present those choices and ask the user to pick exactly one. Capture:
   - `WEB_SERVER` short name (`web1` or `mail1`),
   - its **public IPv4** (derive at runtime — do not hardcode: read it from the host's `linode-<server>-config/tofu/` outputs/tfvars or the existing `scripts/update-<server>-network-dns.sh`, or confirm the current public A record of `<server>.kevininscoe.com`),
   - its **Tailscale IP** (from `linode-<server>-config/ansible/host_vars/<server>.yml`),
   - the config repo path `~/Projects/private/linode-<server>-config`.

5. **Create the Linode domain (zone) for the FQDN** — Using the Linode API and the credential located via the credential map (`~/.secrets/certbot.ini` `dns_linode_key`, as the existing DNS scripts do), check whether the domain/zone already exists in the Linode account (`GET /v4/domains`). If the apex zone for the FQDN does not exist, create it (`POST /v4/domains`, `type=master`, SOA email `kevin.inscoe@gmail.com`). If the FQDN is a subdomain of an existing managed zone (e.g. `*.kevininscoe.com`), no new zone is needed — the record goes in the parent zone. Confirm the plan with the user before any write.

6. **Create the DNS A record** — In the correct Linode zone, upsert an A record for the FQDN (and a `www` A record if the site is an apex domain that should answer on `www`) pointing to the chosen server's **public IPv4** from Step 4. Prefer the repo's idempotent helper where one fits (`linode-<server>-config/scripts/update-<server>-network-dns.sh`), otherwise use the Linode API directly. The record must not be created if an equivalent one already exists (idempotent). Verify with `dig +short A "$FQDN"`.

7. **Register the site in the service catalog** — Following directive `service-catalog.md`, add a row for `$FQDN` to the appropriate HTTPS table in `~/Projects/private/fedora-dashboard/kevins-federated-unix-universe-services.md`: `Endpoint = $FQDN`, `Service Type = HTTPS`, `Host FQDN = <server>.kevininscoe.com`, `Notes = Public website`, `Purpose` per the directive. Keep the table sorted as the file requires.

8. **Create the Gitea repo via the `create-a-repo` skill** — Invoke `~/skills/skills/git/create-a-repo/SKILL.md` to create a **public Gitea** repo named exactly `$FQDN` and clone it to `~/Projects/private/$FQDN`. Follow that skill's steps (it handles `.gitignore`, README/RUNBOOK interview, `mise.toml`, and the parent-README entry). The clone path and repo name are both the FQDN.

9. **Scaffold the repo like `datagiggle.com`** — Copy the structural shape of `~/Projects/private/datagiggle.com` into the new repo (do not blindly copy datagiggle's content):
   - `web/` — `index.html` plus `assets/css/` and `assets/img/`.
   - `.woodpecker/pipeline.yml` — the CI pipeline (Step 11).
   - `scripts/publish.sh` — the manual-fallback publish script (adapted so `SITE=$FQDN`).
   - `AGENTS.md`, `PLAN.md`, `mise.toml`, and an FQDN-specific `RUNBOOK.md` modelled on `datagiggle.com/RUNBOOK.md` (swap in the FQDN, image name, chosen host, and production port).
   Replace every `datagiggle.com` / `datagiggle` / `web1` token with the new FQDN, its OCI image basename, and the chosen host as appropriate.

10. **Create the sample brochure page** — In `web/index.html`, build a single-page brochure-style site with **sample placeholder data** in the same spirit as `datagiggle.com/web/index.html` (hero, a few feature/section blocks, footer), self-contained under `web/assets/`. Make clear in copy/comments that the content is placeholder sample data for the new `$FQDN`. Preview locally per the QA-checks convention (`python3 -m http.server 8000 --directory web`) and report the local URL — do not screenshot.

11. **Create the Woodpecker CI workflow** — Write `.woodpecker/pipeline.yml` in the new repo modelled on `datagiggle.com/.woodpecker/pipeline.yml`. It triggers on semver tags and has three steps:
    - `clone-builder` — clones `web-oci-builder` from Gitea (the build engine).
    - `build-and-push` — runs `web-oci-builder/build/ci/woodpecker/ci-build-and-push.sh` with `SITE=$FQDN`, `GITEA_REGISTRY=git.kevininscoe.com`, `GITEA_OWNER=kinscoe`, `WEB_DIR=$(pwd)/web`. This builds the lighttpd2 OCI image and pushes `:prod`/`:latest` to `git.kevininscoe.com/kinscoe/<image>` (image basename derived from the FQDN, matching datagiggle's `datagiggle-lighttpd2` convention).
    - `deploy-to-<server>` — SSHes to `<server>.network.kevininscoe.com` over Tailscale using the deploy key and runs the per-site image-update script on the host.

    **Woodpecker `${VAR}` gotcha (Woodpecker ≥3.7.0 — REQUIRED):** in `commands:`, Woodpecker substitutes **braced** `${VAR}` itself and replaces unknown names with an empty string *before the shell runs* — so `ssh … "${WEB1_SSH_USER}@${WEB1_SSH_HOST}" …` collapses to `ssh … "@" …` and the deploy fails with SSH exit 255. Use **unbraced** shell vars instead: `ssh … "$WEB1_SSH_USER@$WEB1_SSH_HOST" …` (unbraced `$VAR` is passed through to the shell untouched, exactly like `$WEB1_DEPLOY_KEY` in the key-write step). NOTE: the `datagiggle.com` template still uses the broken braced form, so **do not copy it verbatim** — unbrace the ssh destination when scaffolding.

    Required Woodpecker repo secrets (set by the user in the UI): `gitea_user`, `gitea_token` (PAT with `read:packages`+`write:packages`), and the host deploy key secret (`web1_deploy_key` / equivalent for the chosen host).

12. **Wire Woodpecker to the new repo** — The user activates the `kinscoe/$FQDN` repo and adds the secrets above in the Woodpecker UI at `https://woodpecker-ci.kevininscoe.com` (Settings → Secrets). Provide the exact secret names/scopes and wait for the user to confirm activation before triggering a build.

    **Tell the human these two things explicitly:**

    a. **Scope every secret to `Event: tag`.** The pipeline triggers on `when: event: tag`, so each secret (`gitea_user`, `gitea_token`, `web1_deploy_key`) must have the **`tag`** event enabled in its Events field. A secret restricted to `push` only is invisible to a tag build and the pipeline will fail with a missing-secret error. (Leaving Events empty = "all events" also works, but explicitly selecting just `tag` is cleanest. Do **not** enable `pull_request`.)

    b. **Reuse the shared OpenBao credentials — do not mint a per-repo token.** The values already live in OpenBao; the human pulls them and pastes them into the Woodpecker UI (Woodpecker does not read OpenBao itself). On FLDW, set the env once, then pull each value:
    ```bash
    export BAO_ADDR=https://openbao.kevininscoe.com
    export BAO_TOKEN="$(cat ~/.environment/.vault-token)"

    # → Woodpecker secret  gitea_user   (this is "kinscoe")
    bao kv get -field=user  app/gitea
    # → Woodpecker secret  gitea_token
    bao kv get -field=token app/gitea
    # → Woodpecker secret  web1_deploy_key
    bao kv get -field=private_key -mount=linode-web1 deploy-key
    ```
    **Scope caveat:** `build-and-push` runs `buildah push` to the Gitea registry, which requires the `gitea_token` to carry **`read:packages` + `write:packages`**. If the push 401/403s, that token lacks packages scope — fix by adding those scopes to the `app/gitea` token in Gitea (Settings → Applications), **not** by minting a new per-repo token. (The `~/.config/gitea/api` on-disk token is over-scoped for CI; do not hand it to Woodpecker.)

    c. **Enable repo trust for the privileged buildah step (REQUIRED — easy to miss).** The `build-and-push` step runs `quay.io/buildah/stable` with `privileged: true`, which Woodpecker only permits on a **trusted** repo. A brand-new repo is untrusted, so the pipeline errors at the linter stage with `Insufficient trust level to use 'privileged' mode` **before any step runs** (`woodpecker-cli pipeline ps` shows no steps). Enable trust to match datagiggle — either in the UI (repo → Settings → **Project** → **Trusted** → enable Network/Volumes/Security) or via the admin API:
    ```bash
    # WOODPECKER_SERVER / WOODPECKER_TOKEN are in the env on FLDW; repo id from /api/repos?all=true
    curl -s -X PATCH -H "Authorization: Bearer $WOODPECKER_TOKEN" -H "Content-Type: application/json" \
      -d '{"trusted":{"network":true,"volumes":true,"security":true}}' \
      "$WOODPECKER_SERVER/api/repos/<repo-id>"
    ```
    Privileged mode needs at least `security:true`; datagiggle has all three true.

    d. **Secret-name gotcha.** Woodpecker's UI **trims leading/trailing whitespace when displaying** a secret name, so a secret accidentally saved as `" web1_deploy_key"` (leading space) looks correct on screen but fails at build time with `secret "web1_deploy_key" not found`. Verify the real stored names via the API (`GET /api/repos/<id>/secrets`, inspect with Python `repr()`), not by eye. Fix by deleting and recreating the secret with an exact, space-free name.

13. **Trigger the build and confirm the image in the Gitea registry** — Commit and push the scaffold, then create and push a semver tag to trigger CI:
    ```bash
    git -C ~/Projects/private/$FQDN add -A
    git -C ~/Projects/private/$FQDN commit -m "Initial site scaffold, brochure page, and Woodpecker CI"
    git -C ~/Projects/private/$FQDN push
    git -C ~/Projects/private/$FQDN tag v0.0.1 && git -C ~/Projects/private/$FQDN push origin v0.0.1
    ```
    Monitor the run at `https://woodpecker-ci.kevininscoe.com`. Confirm the OCI image now appears in the **Gitea Packages** registry under `kinscoe/<image>` (publicly pullable, exactly like `datagiggle-lighttpd2`) — verify before deploying. If CI is not yet wired, the manual fallback is `scripts/publish.sh`.

14. **Teach the host's Ansible about the new site** — In `~/Projects/private/linode-<server>-config`, following `opentofu-iac-standards.md` / `when-building-or-scaffolding-code-in-a-git-repo.md`, add the new site by copying the datagiggle pattern:
    - `ansible/roles/containers/defaults/main.yml` — add a `<site>_manage`, `<site>_port`, and `<site>_compose_dir` block. **Assign the port from the target host's own config, not FLDW's `portman`:** enumerate the existing `*_port:` values in `linode-<server>-config` (`grep -rhE '_port:\s*[0-9]+' ansible/`) and pick the next free number in that host's range (on web1 today: 3013–3020 are taken, so 3021 is next free). The port is bound on the remote Linode host, so it must never be reserved in FLDW's `portman`.
    - `ansible/host_vars/<server>.yml` — set `<site>_manage: true`, `<site>_port: <port>`, and add the FQDN (+`www`) to `certbot_extra_certs`.
    - `ansible/roles/containers/tasks/main.yml` and `ansible/roles/apache/tasks/main.yml` — add the compose/vhost tasks that pull `git.kevininscoe.com/kinscoe/<image>:latest`, run it on `<port>:8080`, and front it with an Apache TLS vhost for `$FQDN` — mirroring the existing datagiggle tasks.
    - Add the per-site host-side image-update script referenced by the CI `deploy-to-<server>` step (e.g. `/usr/local/sbin/<site>-image-update.sh`).

15. **Validate the Ansible** — Run a syntax/lint/check pass before converging:
    ```bash
    cd ~/Projects/private/linode-<server>-config
    ansible-playbook -i ansible/inventory.ini ansible/playbook.yml --syntax-check
    ansible-lint ansible/            # if available
    ansible-playbook -i ansible/inventory.ini ansible/playbook.yml --check --diff --limit <server>
    ```
    Resolve any errors and show the check/diff to the user. Commit the config-repo changes (only the relevant files; confirm before committing/pushing per `~/skills/CLAUDE.md`).

16. **Deploy to the chosen host** — Only after confirming (Step 13) the OCI image is present and publicly pullable from `git.kevininscoe.com/kinscoe/<image>`, converge Ansible on the host:
    ```bash
    cd ~/Projects/private/linode-<server>-config
    scripts/ansible-converge.sh        # (limits to the chosen host as configured)
    ```
    This provisions the container, Apache vhost, TLS cert, and update script on `<server>`. Confirm with the user before running (it changes production host state).

17. **Verify the site is live** — Confirm the FQDN serves over HTTPS end-to-end:
    ```bash
    dig +short A "$FQDN"
    curl -I "https://$FQDN"
    ```
    Success is `HTTP/2 200` serving the brochure `web/index.html`. If it fails, consult the new repo's RUNBOOK troubleshooting table and the host container logs (`podman logs <site>`).

18. **Add the site to Uptime Kuma** — Append a monitor block to `~/Projects/private/observability/configs/central-stack/uptime-kuma/monitors.yaml` (model on the existing `datagiggle` entry), then apply it:
    ```yaml
      - name: <fqdn-slug>
        type: http
        url: https://$FQDN
    ```
    ```bash
    cd ~/Projects/private/observability/configs/central-stack/uptime-kuma
    ../../..//scripts/sync-kuma-monitors.py            # dry-run preview first
    ../../..//scripts/sync-kuma-monitors.py --apply    # after confirming the diff
    ```
    (Use the repo's actual `sync-kuma-monitors.py` path.) Confirm the new monitor shows the site as UP.

19. **Report** — Summarize what was created: DNS record + Linode zone, service-catalog row, Gitea repo + clone path, published OCI image, Woodpecker pipeline status, Ansible changes + deploy result, live-site verification, and the Uptime Kuma monitor. List anything the user must still do by hand (Woodpecker UI activation/secrets, `gitme --rebuild-cache`, any config-repo push awaiting confirmation).

## Success Criteria

- `dig +short A $FQDN` returns the chosen server's public IP, and `curl -I https://$FQDN` returns `HTTP/2 200` serving the brochure page.
- The Linode zone/record for `$FQDN` exists (created idempotently, not duplicated).
- A row for `$FQDN` exists in the service catalog HTTPS table with the correct `Host FQDN` and `Purpose`.
- A public Gitea repo named `$FQDN` exists, is cloned to `~/Projects/private/$FQDN`, and is scaffolded like `datagiggle.com` (web/, `.woodpecker/pipeline.yml`, scripts, README/RUNBOOK, mise.toml).
- `web/index.html` is a self-contained sample brochure page for `$FQDN`.
- The OCI image is published and publicly pullable at `git.kevininscoe.com/kinscoe/<image>` (visible in Gitea Packages, same as `datagiggle-lighttpd2`).
- Woodpecker CI is activated for `kinscoe/$FQDN` with the required secrets, and a tag build succeeded.
- `linode-<server>-config` Ansible knows the new site (`<site>_manage`, port, compose/vhost/cert tasks), passes `--syntax-check`/`--check`, and the change is committed after user confirmation.
- The site is deployed on `<server>` and an Uptime Kuma monitor for `$FQDN` reports UP.

## Notes

- **Stop-and-flag rule (Step 3):** if the FQDN already resolves to something not in the service catalog, halt and wait for the user — never create infra over an unknown existing destination.
- **Secrets:** locate Linode/Gitea credentials via the credential map and `storing-secrets.md`; never write a secret value to disk or echo it. Woodpecker secrets live only in the Woodpecker UI.
- **Do not hardcode public IPs or ports** — derive the chosen server's public IP at runtime, and assign the container port from the **target host's own** `linode-<server>-config` Ansible (`grep -rhE '_port:\s*[0-9]+' ansible/`), picking the next free number in that host's range. Do **not** use FLDW's `portman` for this: `portman` only tracks ports bound on FLDW, and this port is bound on the remote Linode web server. On web1 today, 3013–3020 are taken (datagiggle=3018, dokoapp=3019, donetick=3020), so 3021 is next free.
- **`web-oci-builder` is the build engine, not a per-site repo** — it is cloned by CI and by `scripts/publish.sh`; this skill does not modify it.
- **Image naming** follows datagiggle's convention (`<site>-lighttpd2`); keep it consistent so the CI script, Ansible pull, and registry path all agree.
- Gitea SSH uses port 2223; the default branch is always `main`; SSH is the only git protocol used here.
- **Confirm before committing/pushing** in `linode-*-config`, `observability`, and any repo outside `~/skills` — commit only the relevant files, never `git add -A` across an unrelated tree (see `~/skills/CLAUDE.md`).
- Related skills: `git/create-a-repo` (Step 8), `docker/create-a-self-hosted-docker-container`. Related runbooks: `datagiggle.com/RUNBOOK.md`, `web-oci-builder/RUNBOOK.md`, `linode-<server>-config/RUNBOOK.md`.
- Consider adding an equivalent action to `~/todo/mac/TODO.md` / `~/todo/rpi/TODO.md` only if it applies to those hosts — ask first (these sites are Linode-hosted, so it usually does not).
