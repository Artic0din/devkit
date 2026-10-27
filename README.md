# DevKit

Global agent environment for Claude Code, Codex, Cursor, GitHub Copilot and Antigravity.
One source of rules, skills, agents, hooks and MCP config, linked into each tool.
Canonical repository: [Artic0din/devkit](https://github.com/Artic0din/devkit).

## Layout

The audit script named under Install reports whether a machine's rules pointers and its Claude and Codex skill mirrors are in place; the hook merges, agent links and Antigravity steps are not audited yet.

| Path | Purpose |
| --- | --- |
| `AGENTS.MD` | Global hard rules, linked into Claude, Codex, Copilot CLI and Antigravity; Cursor reads it through `config/cursor.rules.mdc`. |
| `skills/` | Skills, one folder each with `SKILL.md`. Personal and vendored skills are committed here. |
| `skills.sh.json` | Curated routing catalogue; additional imported skill directories may be present. |
| `skills.lock.json` | Third-party skills that `install.sh` will fetch into `skills/.external/` (gitignored). |
| `.github/instructions/` | GitHub Copilot custom instructions, scoped by `applyTo`. |
| `hooks/` | Repository hook scripts. The tool configs under `config/` currently reference `~/.claude/hooks/`. |
| `agents/` | Subagent definitions per tool format. |
| `config/` | Per-tool settings, hooks and MCP files that get linked into place. |
| `docs/` | Engineering standards referenced from `AGENTS.MD`. |
| `templates/github/` | Default issue forms, PR templates, triage playbook and triage workflow caller; see `docs/github-intake.md`. |
| `scripts/` | Dependency-light helpers: skill sync and audit, validation, docs listing, browser tooling. |

## Install

The GitHub rename keeps the local `~/Metisary/Enviroment/config` directory and installed `agent-scripts` skill link unchanged.
The sync, audit and canonical instructions continue to use those installed paths.

`install.sh` is the intended installer and is not written yet. Until it exists, `scripts/sync-skills`
builds the per-machine skill mirror and instruction pointers:

- Codex scans nested directories, so it gets a whole-root link: `~/.codex/skills/agent-scripts -> ~/Metisary/Enviroment/config/skills`.
- Claude Code loads only `~/.claude/skills/<name>/SKILL.md` (one level deep; per-entry symlinks are followed, category folders are not scanned). It gets a flat per-skill link mirror.
- Name collisions resolve agent-scripts > codex-local; the script prints skipped duplicates and prunes broken or stale managed links, and never clobbers real files.
- `sync-skills` and `skills/fleet-maintenance/scripts/agent-skill-links-audit.sh` share `scripts/canonical-paths.sh`, so the sync and the audit cannot disagree about where the repo lives.

On an activated machine, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, `~/.claude/AGENTS.md` and
`~/.gemini/GEMINI.md` resolve to this repo's `AGENTS.MD`, `~/.codex/skills/agent-scripts` links to
`skills/`, and every skill here is mirrored into `~/.claude/skills` and `~/.gemini/skills`. Check a
machine rather than assuming; the audit exits non-zero and lists each drifted link:

The existing Metisary activation also links `~/.agents/skills` to this repository's `skills/`, `~/.copilot/copilot-instructions.md` to `AGENTS.MD`, and `~/.cursor/rules/metisary.mdc` to `config/cursor.rules.mdc`.
Antigravity uses `config/antigravity.skills.json` and the named `metisary` hook group.
The nested synced-skill path in that manifest is a local import; it is not provided by a fresh checkout.
The audit below covers its documented Claude/Codex pointers, not all application integrations.
These activation files target Ryan's existing canonical checkout; adjust their paths before activating a different machine layout.

```bash
bash ~/Metisary/Enviroment/config/skills/fleet-maintenance/scripts/agent-skill-links-audit.sh
```

The sync does not cover the rest of an install, which is currently done by hand and is what
`install.sh` should automate: merging the `config/` hook and permission entries into each tool's live
settings (additive only), linking `agents/` into `~/.claude/agents` and `~/.codex/agents`, and the
Antigravity rules link and skills mirror. Before activating a machine, copy every file those steps
touch to `~/Metisary/Enviroment/backups/activation-YYYY-MM-DD-<host>/`; existing snapshots are listed by
`ls ~/Metisary/Enviroment/backups/`, and the activation entries in `CHANGELOG.md` name each one. Done once by hand, not linkable: `claude mcp add`,
`codex mcp add`, the optional web UI paste in `config/ui-paste.md`, and exporting
`GITHUB_PERSONAL_ACCESS_TOKEN` in the shell that launches Codex. The Codex MCP template inherits that
variable by exact name (`env_vars`) because Codex does not expand `${VAR}` in `env`; source the value
from the Keychain via `$keychain`, and if it is unset the GitHub server starts with no token.

Run `scripts/test-sync-skills` for isolated fixture coverage of the sync and audit.

## Rules

Rules live once. `AGENTS.MD` holds only rules that apply on every request in every tool.
Path-scoped and on-demand content belongs in project rules, `.github/instructions/`, and skills.
Keep `AGENTS.MD` under 200 lines.

Downstream repos use a pointer-style `AGENTS.MD`, with repo-specific rules below it and no copied blocks:

```text
READ ~/Metisary/Enviroment/config/AGENTS.MD BEFORE ANYTHING (skip if missing).
```

## Skills

The [curated Pstack skills](docs/curated-pstack.md) provide automatic plain-language writing and explicitly requested project verification workflows.

The [vendored tstack skills](docs/curated-tstack.md) file, babysit, review, modernize, and take over pull requests.

`skills/retro` contains [Matt Pocock's session retrospective](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/in-progress/retro/SKILL.md).
It is invoked explicitly to review a coding session and suggest improvements to the agent environment.
For Claude, the selected `~/.claude/skills/retro` link points to this folder.
`skills/gstack-retro` registers the distinct, manually invoked weekly review and reads the installed Gstack instructions without editing generated files.
Point the Claude and Codex `gstack-retro` links to that wrapper.
In Codex's user skill settings, disable the original `skills/gstack/retro/SKILL.md` and `skills/gstack/.agents/skills/gstack-retro/SKILL.md` entries so only Matt's skill registers as `retro`.

Each `skills/<name>/SKILL.md` has YAML front matter with a quoted `description`:

```yaml
---
name: skill-name
description: "Short generic trigger phrase."
---
```

- Keep descriptions short and generic; optimize for routing, not documentation.
- Keep skill bodies terse and operational; put repeatable commands in `skills/<name>/scripts/`.
- Validate after edits with `scripts/validate-skills`. To run it as a pre-commit hook, opt in once with `git config core.hooksPath hooks`.
- `skills.sh.json` is the curated catalogue; review imported skills before adding routing entries.
- `skill-cleaner` audits prompt budget and duplicates; run it after adding a batch of skills.

`autoreview` is maintained in `skills/autoreview` with its review helper and acceptance harness.
`python3 skills/autoreview/scripts/test-autoreview.py` runs the offline checks;
`skills/autoreview/scripts/test-review-harness --engine codex --fixture malicious` (and `benign`) runs the live acceptance checks.

## Helpers

- `scripts/sync-skills`: builds the mirror described above; idempotent; prints changes only. No arguments runs the ordinary sync; `--help` prints usage. Only the scoped `--repair-nested-self-links` mode accepts `--dry-run`.
- `scripts/validate-skills`: checks every `skills/*/SKILL.md` for front matter, `name`, and `description`.
- `scripts/docs-list.ts`: walks `docs/`, enforces `summary` and `read_when` front matter, prints onboarding summaries.
- `scripts/browser-tools.ts`: standalone Chrome DevTools helper (`start --profile`, `nav`, `eval`, `screenshot`, `console`, `network`, `search --content`, `content`, `inspect`, `kill --all --force`); build a binary with `bun build scripts/browser-tools.ts --compile --target bun --outfile bin/browser-tools`.

### Repairing nested self-links

For the specific legacy topology `~/.claude/skills/NAME/NAME -> ~/.codex/skills/NAME -> ~/.claude/skills/NAME`, invoke the sync owner directly with an explicit allowlist, dry run first:

```bash
/absolute/path/to/config/scripts/sync-skills --repair-nested-self-links --dry-run -- skill-one skill-two
```

```bash
/absolute/path/to/config/scripts/sync-skills --repair-nested-self-links -- skill-one skill-two
```

This mode validates every candidate before unlinking only the extra nested leaves. It preserves the real skill directories, assets, and valid Codex backlinks, and exits before creating roots, building mirrors, pruning, or touching instruction pointers. Names must start with an ASCII letter or digit and contain only letters, digits, `.`, `_`, or `-`; duplicates, missing names, and unknown arguments are rejected. A missing nested leaf is a no-op only with the expected surrounding topology. Redirected or inaccessible roots, unexpected objects or literal targets, and changed directory or link identities cause refusal. Rechecks before each unlink are not atomic concurrency protection: a later error stops the batch and reports removals already completed, without rollback.

## Reusable workflows

DevKit hosts the repository baseline check; [its contract and adoption guide](docs/reusable-workflows.md) describe inputs, permissions, validation, and rollback.
Other workflows remain in `Artic0din/reusable-workflows` until their independently validated migration under [#33](https://github.com/Artic0din/devkit/issues/33).

## Repository rename and rollback

Update an existing checkout's `origin` to `https://github.com/Artic0din/devkit.git`; keep its local directory in place.
For a reusable workflow caller, change `Artic0din/agent-scripts/.github/workflows/` to `Artic0din/devkit/.github/workflows/` explicitly.
GitHub does not redirect reusable workflow calls after a rename.
Keep the reviewed commit SHA and the matching `agent-scripts-ref` value unchanged for an address-only migration.
The input name and `.agent-scripts` checkout directory are retained for existing callers.
New callers follow the adoption steps in [GitHub intake](docs/github-intake.md).

The 2026-10-10 inventory inspected 208 workflow files on the default branches of all 46 active repositories visible under `Artic0din` and `Plaintext-Lab`, including forks.
It found the old address in this repository's reusable triage workflow and in `Artic0din/unshackled`'s triage caller.
Track downstream adoption and machine validation in [#46](https://github.com/Artic0din/devkit/issues/46).
The installed instruction and skill root links resolved correctly on this Mac, but the broader skill-link audit reported 55 existing discrepancies before this patch; that audit remains a separate validation gap.

To roll back a caller update, restore its previous reviewed SHA and matching `agent-scripts-ref`, keeping the current `Artic0din/devkit` address.
To roll back local remote configuration, restore the recorded previous URL; GitHub currently redirects the old Git URL.
Do not recreate a repository at `Artic0din/agent-scripts`, because that would remove the redirect.
A GitHub name rollback must be coordinated with every migrated caller; reverting code alone does not restore the repository name.

## Syncing downstream

Treat this repo as canonical for shared rules and portable helpers. When syncing a downstream repo: pull here first; ensure it starts with the pointer-style `AGENTS.MD`; preserve its local rules; copy helper changes in both directions only when a helper is meant to stay byte-identical; keep scripts dependency-free. For submodules, repeat the pointer check inside each subrepo, push, then bump the submodule SHAs in the parent.
