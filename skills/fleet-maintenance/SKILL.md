---
name: fleet-maintenance
description: "Maintain Ryan's three Macs over LAN SSH: audit host health and disk, update Homebrew and global npm packages, fast-forward clean repos, route Xcode through $xcode-sync, and report per-host state including unreachable hosts."
---

# Fleet Maintenance

Use when Ryan asks to maintain, update, or audit more than one of his Macs.
For a single explicitly chosen Mac, use `$mac-maintenance` instead.

## Hosts

| Host | Reach | Notes |
| --- | --- | --- |
| `Ryans-MacBook-Air` | local | Daily driver. Homebrew at `/opt/homebrew`. |
| `MacBook-Pro` | `ssh mbp` (192.168.1.9) | Homebrew at `/opt/homebrew`. Key `~/.ssh/id_ed25519_migrate` via the `mbp` alias in `~/.ssh/config`. |
| iMac | `ssh imac` (192.168.1.210) | Alias resolves, but Remote Login was still off on 2026-09-18 and port 22 timed out. Report `pending`; do not attempt repair. |

Confirm identity before mutating any host:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 mbp 'scutil --get LocalHostName; sw_vers; uname -m'
```

An unreachable host is `pending`, never `current`. Do not wake, power on, or enable
Remote Login on a host during maintenance; report it and let Ryan decide.

### Remote PATH

Non-interactive SSH does not load `/opt/homebrew/bin`, so `brew`, `node`, `npm`, `gh`,
and `xcodes` all appear missing on `mbp`. The bundled scripts find Homebrew themselves;
every ad-hoc remote command must export PATH or it will report a false absence:

```bash
ssh -o BatchMode=yes -o RequestTTY=no mbp \
  'export PATH=/opt/homebrew/bin:$PATH; brew --prefix; node --version'
```

## Repository roots

The audit and update scripts take the root as a required first argument and refuse to
run without one, so a scan can never silently target an empty default. Discover what
exists on each host before scanning, and never assume a root is populated:

- Air: `~/Developer` and `~/Development/projects`. The audit recurses, so `~/Developer`
  already covers `~/Developer/projects` and `~/Developer/copilot-worktrees`.
- `~/Metisary/Projects` is the migration target. Scan it once it holds repos.
- `mbp`: discover with `find ~ -maxdepth 4 -name .git -not -path '*/node_modules/*'`.

A missing root exits 2 without scanning, so passing a root that does not exist yet is
safe. An empty root is not an error and not proof that a host has no repos.

Each visible checkout is user-managed. Do not infer that a stale checkout should match
its sibling on another host.

## Safety contract

- Audit hosts in parallel; mutate one host at a time.
- Skip a repository with a user process cwd inside it or a Git lock. Recent file
  modification is audit signal, not a blocker.
- Never reset, clean, stash, rebase, switch branches, push, install macOS updates, or
  reboot during routine maintenance. Never pass `--autostash`.
- Homebrew and npm updates are allowed while agents are running. This can mix old
  in-memory code with replaced files and let Homebrew quit and reopen cask GUI apps.
  Accept that risk; report interruptions. Never manually restart services.
- Keep a per-host action log.

## Run order

1. Health and disk audit on every reachable host.
2. Fast-forward eligible repos.
3. Homebrew update and upgrade.
4. Global npm package updates.
5. Report the macOS track; do not install or reboot.
6. Xcode through `$xcode-sync`.
7. Empty Trash only when this run explicitly asked for it.
8. Re-audit disk and report.

## Health audit

```bash
skills/fleet-maintenance/scripts/host-health-audit.sh 30
ssh -o RequestTTY=no -o RemoteCommand=none mbp 'bash -s -- 30' \
  < skills/fleet-maintenance/scripts/host-health-audit.sh
```

Report every process above 30 GiB resident memory with PID, resident GiB, user,
executable, and whether it stays above the threshold on a second sample. Do not sum
related processes, alert on virtual size, or terminate anything automatically.

The audit also prints `ownership-candidate` rows where a Homebrew formula and an app
bundle ship the same executable name. App-bundled copies of `node`, `rg`, `gh`, and
`ffmpeg` inside Cursor, ChatGPT, Conductor, and StreamFab are normal and are not
conflicts. Never infer a conflict from a shared name: resolve realpaths, receipts, and
running processes first, and change an owner only when the current request authorizes it.

Classify startup-disk space by absolute and relative capacity:

- healthy: at least 100 GiB and 15% free
- warning: 50–100 GiB or 10–15% free
- critical: below 50 GiB or 10% free

Do not start Xcode expansion on warning or critical space.

## Agent tooling audits

Run these on every reachable host; all three are read-only.

Host snapshot — hostname, hardware UUID, architecture, macOS version and build, accounts, and
installed software. It needs no inventory file:

```bash
node skills/fleet-maintenance/scripts/fleet-profile.mjs collect
ssh -o RequestTTY=no -o RemoteCommand=none mbp 'node --input-type=module - collect' \
  < skills/fleet-maintenance/scripts/fleet-profile.mjs
```

Its `plan`, `brewfile`, and `validate` subcommands need a desired-state inventory, which does not
exist yet. Use `collect` until one does.

Codex and Claude CLI versions and non-interactive auth. Both live in `~/.local/bin`, not Homebrew:

```bash
skills/fleet-maintenance/scripts/agent-cli-audit.sh
```

Skill mirror drift between this repo, `~/.codex/skills`, and `~/.claude/skills`:

```bash
skills/fleet-maintenance/scripts/agent-skill-links-audit.sh
```

The active canonical root is `~/Metisary/Enviroment/config`.
Missing instruction or skill links, or links to the retired `~/Development/Workspace/Codex` tree, are drift.
When repair is authorized, use `--repair` to restore the pointers managed by the sync tool.
Existing real files are preserved and reported as conflicts.

## Repository sync

Audit first; it is read-only and marks each repo `candidate` or skipped:

```bash
skills/fleet-maintenance/scripts/repo-sync-audit.sh ~/Developer 3
ssh -o RequestTTY=no -o RemoteCommand=none mbp 'bash -s -- "$HOME/Development" 3' \
  < skills/fleet-maintenance/scripts/repo-sync-audit.sh
```

Apply only to rows marked `candidate`. The updater rechecks safety, fetches
noninteractively, and fast-forwards clean or conflict-free dirty worktrees:

```bash
skills/fleet-maintenance/scripts/repo-sync-update.sh ~/Developer 3
```

Interpret `git rev-list --left-right --count HEAD...@{upstream}` as `ahead behind`:

- `0 0`: current; no action.
- `0 N`: run `git merge --ff-only --no-autostash --no-overwrite-ignore @{upstream}`.
  A dirty worktree advances only when Git can preserve every local change. Git's
  refusal is `skip-local-overlap`, not an error to repair. After a refusal, require
  unchanged `HEAD`, no unmerged entries, and unchanged worktree status.
- `N 0` or `N M`: inspect local commits and `git diff --stat @{upstream}...HEAD`,
  explain the likely intent, and escalate. Never push or rewrite.
- Detached, no upstream, or fetch failure: escalate with the smallest useful decision.

Bound every fetch (five minutes is enough). On timeout or authentication failure, mark
that repo `pending` and continue; never rewrite a remote or prompt for credentials.

## Homebrew

Skip only if Homebrew is absent.

```bash
brew update && brew outdated --json=v2 && brew upgrade && brew services list && brew doctor
```

Treat `brew doctor` as advisory. Compare `brew services list` before and after. Run
`brew cleanup --prune=30` after verification; anything more aggressive needs explicit
approval. Never uninstall packages or change taps automatically.

## Global npm packages

This means registry-backed, top-level global packages only. Never touch a
repository's `package.json` or lockfile here.

1. Record `node --version`, `npm --version`, `npm prefix -g`, `npm ls -g --depth=0 --json`.
2. Run `npm outdated -g --depth=0 --json`; a nonzero exit can mean updates exist.
3. Update each registry package to `name@latest`. Skip and report linked, file, Git,
   and bundled packages.
4. Homebrew owns npm on both Macs, so let `brew upgrade` update npm itself.
5. Re-run the inventory and smoke-test the updated CLIs. Use `$npm` only if a private
   package actually needs registry authentication.

## macOS and Xcode

Record `sw_vers` product and build, then use `softwareupdate --list` to confirm what
each host is offered on its configured track. Resolve the current stable and beta
builds from Apple rather than hardcoding versions. Routine maintenance never switches
tracks, installs updates, or reboots: prepare the exact update and request a window.

Invoke `$xcode-sync` for all Xcode work, including its simulator-hygiene audit. A host
without Xcode or `simctl` is `not-applicable`. Do not duplicate its install logic here.

## Trash and disk

Measure Trash every run, but keep it read-only unless this run explicitly said to empty
it. With that consent, empty only the current user's home-volume Trash after verifying
the path resolves inside `$HOME`:

```bash
trash_real=$(cd "$HOME/.Trash" && pwd -P)
[[ "$trash_real" == "$(cd "$HOME" && pwd -P)/.Trash" ]] || exit 2
find "$trash_real" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
```

Never empty another user's Trash or Trash on an external volume. Recheck capacity
afterwards and escalate unexplained growth instead of deleting caches.

## Baseline checks

Read-only; include in the report:

- available macOS and security updates, and whether a reboot is recommended
- last successful Time Machine backup, when configured
- storage warnings from `diskutil`, uptime, and laptop battery health
- failed Brew services and orphaned LaunchAgents
- FileVault, firewall, Gatekeeper, and SIP status drift
- SSH key and Developer ID certificate expiry dates, never secret values

## Finish

Return a host matrix: reachability, disk before and after, Trash reclaimed, Brew and
npm changes, repos pulled/current/skipped/escalated, Xcode build and track, backup and
update warnings, and every remaining decision for Ryan.
