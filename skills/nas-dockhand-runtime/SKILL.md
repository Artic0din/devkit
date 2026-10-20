---
name: nas-dockhand-runtime
description: Use when checking, deploying, restarting, updating, or debugging apps running on Ryan's Synology NAS through Dockhand, especially stacks, container health, runtime parity, logs, ports, and volumes.
---

# NAS Dockhand Runtime

Use live Dockhand and Docker state as the source of truth for NAS work.
Repository files and local Docker are supporting evidence only.

Resolve the Dockhand API URL and environment ID from local NAS configuration; do not publish machine-specific addresses in shared configuration.
Read the Dockhand API token from macOS Keychain service `dockhand-api`, account `ryan`.
Never print, log, copy into files, or commit the token.
Portainer has been retired from this NAS; do not rely on its endpoint or credentials.

## Workflow

1. **Identify the target.** Confirm the app, stack, container names, repo path, branch, and whether the request authorizes a write such as restart, redeploy, or configuration change.
   Read the repo `AGENTS.md`, deployment docs, Compose files, `.env.example`, `git status`, and recent commits when a repo is involved.

2. **Check the control path.** Request Dockhand health, then authenticate with its Keychain token and query the environment/container inventory.
   If the token is unavailable, check local environment and configuration files before asking for access.
   Do not fall back to the removed Portainer service.

3. **Inspect live state.** Read the target container and stack details, including image IDs, Compose source type and path, mounts, ports, restart policy, health checks, and recent logs.
   Confirm the target environment ID before making changes.
   Local Docker is NAS evidence only after proving its context points at this NAS.

4. **Diagnose before changing anything.** Use the evidence to distinguish a wrong stack, stale image, environment drift, missing volume, failed health check, port conflict, or application error.
   For a read-only audit, stop after reporting findings and the recommended next action.

5. **Make one requested change at a time.** Save the current stack/container state, image ID, mount list, and a rollback path first.
   Prefer Dockhand stack operations over ad hoc container recreation.
   If a write request times out, read live state before retrying; the action may have completed despite the timeout.
   Change one stack or service at a time.

6. **Verify end to end.** Confirm the container is running or healthy, logs show no new errors, expected ports respond, and the user-facing route returns plausible data.
   Check persistent data and downstream effects when the change touches them.

## Stop Conditions

- Complete only after live runtime evidence proves the requested state, not after a successful local build alone.
- If the Dockhand token or API is unavailable after checking local configuration, report exactly what was checked and the access path that failed.
- After three failed attempts against the same failure mode, stop and recommend a reset or rollback point with the exact commit, image, or stack snapshot if known.
