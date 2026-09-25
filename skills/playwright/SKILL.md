---
name: "playwright"
description: "Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script."
---


# Playwright CLI Skill

> Modified by Artic0din/agent-scripts for canonical skill paths, pinned runtime and browser setup, trusted configuration, and artifact handling.

Drive a real browser from the terminal using `playwright-cli`. Prefer the bundled wrapper script so the CLI works even when it is not globally installed.
Treat this skill as CLI-first automation. Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite check (required)

The wrapper uses a locked CLI installation inside this trusted skill directory, never a project's local executables.
Check Node.js and npm before setup:

```bash
node -e 'if (Number(process.versions.node.split(".")[0]) < 20) { console.error("Node.js 20 or newer is required"); process.exit(1); }'
npm --version
```

If unavailable, install through the host's supported Node.js setup before continuing.

## Skill path (set once)

```bash
export PWCLI="${CODEX_HOME:-$HOME/.codex}/skills/agent-scripts/playwright/scripts/playwright_cli.sh"
(cd "$(dirname "$PWCLI")/runtime" && npm ci --ignore-scripts --no-audit --no-fund)
node "$(dirname "$PWCLI")/runtime/node_modules/playwright/cli.js" install chromium
```

This path matches the repository's Codex mirror.
For another host, resolve `scripts/playwright_cli.sh` relative to this loaded `SKILL.md` instead.
Run setup from the trusted skill's runtime directory; the lockfile pins versions and package integrity, and installation scripts are disabled.
The browser install uses that pinned Playwright version.
On Linux, install missing operating-system browser dependencies through the host's supported package manager before opening a browser.
The wrapper requires Node.js 20 or newer and forces its bundled trusted browser configuration.
It ignores project-local configuration and rejects `--config` overrides; review any necessary settings in the trusted configuration before use.

## Quick start

Use the wrapper script:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug a UI flow with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Multi-tab work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper script

The wrapper invokes the locked CLI by absolute path, retaining the caller's working directory for browser sessions and artifacts:

```bash
"$PWCLI" --help
```

Use the wrapper after setup; do not substitute project-local `npx` execution.

## References

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and say why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use the ignored `output/playwright/` directory.
  In other repositories, choose an ignored or temporary location before capturing.
- Default to CLI commands and workflows, not Playwright test specs.
