---
name: parzival-maintain-k-fed-config
category: parzival
description: Provisions and maintains Kevin's private parzival-k-fed-config Gitea repo — the git-tracked deployment/policy/broker configuration for Parzival across k-fed — via branch-and-PR changes only, never a direct push or merge.
---

# Maintain the Parzival k-fed Config Repo

> Provisions and maintains `git.kevininscoe.com/kinscoe/parzival-k-fed-config` — Parzival's
> private deployment/policy/broker/host configuration repo — through issue-tracked
> branch-and-PR changes that Kevin reviews and merges himself.

## Prerequisites

- `tea` CLI authenticated via OpenBao (`app/gitea`) — see `~/ai/directives/gitea.md`
- SSH access to `git.kevininscoe.com:2223`
- `git.kevininscoe.com/kinscoe/parzival-k-fed-config` already exists and is cloned to
  `~/Projects/private/parzival-k-fed-config`
- `parzival` CLI on `PATH`, for `parzival policy check` validation when a policy file is touched
- A YouTrack issue for the requested change (PCT is mandatory for every non-work project touch —
  see `~/ai/directives/project-operations-ecosystem.md`). If one does not already exist, ask
  Kevin which project it belongs in; never default to one.
- Read in full before taking any action: `~/ai/directives/root-directive.md`,
  `~/ai/directives/project-operations-ecosystem.md`,
  `~/ai/directives/when-creating-a-youtrack-ticket.md`,
  `~/ai/directives/when-working-in-a-git-tracked-repo.md`, `~/ai/directives/gitea.md`,
  `~/ai/directives/storing-secrets.md`, `~/ai/directives/gitignore.md`

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `CHANGE_DESCRIPTION` | What Kevin wants changed — a policy rule, a broker consumer/profile, a host deployment file, or (first run only) the repo's initial content | _(required — ask the user)_ |
| `YOUTRACK_ISSUE` | An existing issue key to work under | _(optional — ask which project if none is named)_ |

## Instructions

1. **Read the directives** listed above in full. This is mandatory on every invocation, not
   only the first.

2. **Determine the mode.** Check whether the repo already has real content:
   `git -C ~/Projects/private/parzival-k-fed-config ls-tree -r main --name-only | grep -q
   policy/policy.json`. No match means this is the **first run** — the repo is still a bare
   scaffold or `tea --init` stub.

3. **Confirm the YouTrack issue.** Do not begin implementation without one. If Kevin has not
   named it, ask which project — never guess, never default to `KEVIN`.

4. **First run only** — perform the initial-creation task in this order:
   - Directory scaffold (`policy/`, `broker/{consumers,profiles}`, `hosts/<host>/` per k-fed's
     current host roster, `provisioning/`, `tests/`, `docs/`), `README.md`, `RUNBOOK.md`,
     `mise.toml`.
   - The `.gitignore` hygiene commit, pushed directly to `main` in the _primary_ clone — the one
     carve-out allowed before any worktree or branch protection exists (per
     `~/ai/directives/gitignore.md`).
   - Gitea branch protection on `main` via the Gitea API (`branch_protections`): direct push
     blocked for everyone, merge restricted to `kinscoe`. Document in `RUNBOOK.md` whatever
     Gitea's model cannot express.
   - Migration of the live `~/.config/parzival/policy.json` into `policy/policy.json` — read it,
     scan for resolved secret values (not just `bao:`/path references), copy (never move) it,
     validate, and leave the live file untouched.
   - All of the above except the `.gitignore` commit happens in the issue-named worktree from
     step 6, not on `main` directly.

5. **Every other run — read the repo's own `RUNBOOK.md` first.** It is the authoritative,
   living procedure for this repo's workflow and authority model. This skill orchestrates; the
   target repo's `RUNBOOK.md` governs. Re-read it every time rather than trusting memory of an
   earlier run.

6. **Create or reuse the issue-named worktree and branch:**

   ```bash
   git -C ~/Projects/private/parzival-k-fed-config worktree add -b <ISSUE> ai-wt/<ISSUE>/ main
   ```

   Record the worktree-creation comment on the YouTrack issue (branch name, worktree path, date
   and time) per `~/ai/directives/when-creating-a-youtrack-ticket.md` — it doubles as that
   directive's start comment.

7. **Make the requested change** inside the worktree: a policy rule under `policy/`, a broker
   consumer or profile under `broker/consumers/` or `broker/profiles/`, or a host deployment file
   under `hosts/<host>/`.

8. **Validate before committing, every time:**
   - `parzival policy check` against any touched policy file, if `parzival` is on `PATH`.
   - JSON syntax validation for every touched `.json` file.
   - A plain-text scan of the diff for anything that looks like a resolved secret value —
     a real token, password, or key — as opposed to a `bao:<path>#<field>` reference. Refuse to
     commit if anything matches.

9. **Commit, log the commit to the YouTrack issue**, and push the branch:

   ```bash
   git -C ~/Projects/private/parzival-k-fed-config/ai-wt/<ISSUE> push -u origin <ISSUE>
   ```

   Open a PR against `main`:

   ```bash
   tea pr create --repo kinscoe/parzival-k-fed-config --base main --head <ISSUE> \
     --title "<summary>" --description "<what changed and why>"
   ```

10. **Stop.** Hand Kevin the PR's full FQDN URL as bare text
    (`https://git.kevininscoe.com/kinscoe/parzival-k-fed-config/pulls/<n>`). Never merge, never
    push to `main` directly — branch protection blocks it regardless — and never deploy.
    "Deploy" means copying merged content from this repo back onto `~/.config/parzival/` on a
    live host, and only Kevin does that.

## Success Criteria

- The requested change exists on an issue-named branch with an open, unmerged pull request.
- Validation (`parzival policy check`, JSON syntax, secret-value scan) ran and passed before the
  commit that introduced the change.
- No resolved secret value appears anywhere in the diff — only `bao:<path>#<field>` references,
  if any.
- `main` on `git.kevininscoe.com/kinscoe/parzival-k-fed-config` is unchanged by this run (except
  the one-time `.gitignore` hygiene commit on a first run), and branch protection still blocks
  direct pushes and unauthorized merges.
- The YouTrack issue carries the worktree-creation, commit, and PR-opened comments.

## Notes

- **Authority model.** `github.com/kevinpinscoe/parzival` is the public product source.
  `git.kevininscoe.com/kinscoe/parzival-k-fed-config` is the private deployment/configuration
  authority. The archived `git.kevininscoe.com/kinscoe/parzival` mirror is historical only.
  Nothing is deployed from an unmerged branch — only configuration merged to this repo's `main`
  is authoritative.
- **No AI service-account Gitea identities exist yet.** Until Kevin creates them, this skill
  authenticates as his own `kinscoe` credentials via `tea`/OpenBao, so the real backstop against
  an unreviewed merge is Gitea's branch protection plus this skill's own behavior (steps 9–10),
  not a separate account boundary. Record any such identity as TBD rather than inventing one.
- The target repo's own `RUNBOOK.md` is the living source of procedure for ongoing maintenance —
  this file orchestrates around it and should not be treated as a substitute for re-reading it.
- Related skill: `git-create-a-repo` — general-purpose repo creation; this skill is specific to
  `parzival-k-fed-config`'s own branch/PR/validation workflow.
