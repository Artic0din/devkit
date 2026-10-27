---
summary: Timeline of guardrail helper changes mirrored from Sweetistics and related repos.
---

# Changelog

## Unreleased

- Updated fleet maintenance for the current fleet: it now covers the iMac, lists the Intel Mac mini and Windows PC as joining, and explains how to run it from a Mac other than the Air.
- Removed the `gstack-retro` weekly review and its setup notes, because Gstack is no longer installed.
- Removed the agent host `pre-commit-secrets.sh` hooks and their Claude, Codex, Copilot, Cursor and Antigravity registrations; the opt-in Git `pre-commit` hook still runs the staged-secret scan.
- Fixed skill sync and its audit to preserve existing canonical aliases and variants and allow the retired manager root to be absent.
- Recorded the existing Metisary skill and worktree paths, Cursor and Copilot instruction links, and Antigravity registration files.
- Added Theo Browne's tstack PR-workflow skills (`full-send`, `full-stop`, `council`, `sol-loop`, `file-pr`, `takeover`, `babysit-pr`, `modernize`, `leaving-pr-comments`), so agents can file, review, babysit, and land pull requests end to end.
- Added the `video-analysis` skill: give any agent a video link and get a self-contained HTML brief with a TL;DR, a clickable key-moment timeline, themes, actions tied to Ryan's setup, and a resumable step checklist for tutorials, using only keyless transcript sources.
- Published redacted staged-secret checks with advisory host warnings and opt-in Git commit enforcement, without rejecting ordinary product names or printing staged contents.
- Removed the `/cos` Chief of Staff skill and its local-memory workflow exemption.
- Fixed the repository baseline accepting required paths outside the caller checkout; absolute paths, traversal escapes, and outside symlink targets now fail with an explicit diagnostic.
- Moved the reusable repository baseline check into DevKit, preserving its inputs and check identity and validating it through DevKit's own CI.
- Updated the canonical repository identity to DevKit and pointed shared triage workflows at `Artic0din/devkit`, preserving installed paths and existing workflow inputs.
- Fixed manually dispatched issue triage failing before any job ran: the caller template now converts the dispatch input to a number with `fromJSON`, so `gh workflow run issue-triage.yml -f issue-number=<n>` no longer fails with `Unexpected value '<n>'`.
- Added default issue forms (bug, feature, maintenance, investigated report), PR templates, and an issue triage playbook under `templates/github/`, with repository-first precedence documented in `docs/github-intake.md`.
- Added a reusable issue triage workflow that labels every new issue in an adopting repository `needs-triage`, has Claude investigate it read-only, and records one outcome label and one comment; failures stay visibly pending with a retry link.
- Updated plain-language writing guidance and added portable, manually invoked Pstack verification skills with complete behavior coverage, read-only audits unless corrections are authorized, and action-specific authorization with safe downstream targets during skill maintenance.
- Made MVP scope the default, added YAGNI/KISS/DRY guidance, and improved ADHD-friendly explanations across unfamiliar technical stacks.
- Made the retrospective writing-guide step portable and preserved standards until reviewers load their destination.
- Updated Matt Pocock's session retrospective to favour automated checks for mechanical mistakes.
- Separated the manually invoked Gstack weekly retrospective from Matt's session retrospective with a distinct `gstack-retro` command.
- Removed the dangerous-Git blocker from the default Claude, Codex, Cursor, Copilot, and Antigravity hook registrations while retaining their pre-commit secret checks.
- Removed stale filesystem references from `AGENTS.MD`: the active-repos table, whose eight paths all pointed at
  directories that no longer exist and which had to be edited each time a checkout moved, and a knowledge rule
  citing `workspace-index.yaml`, which exists nowhere on disk. Locating repositories rather than assuming a fixed
  path is already stated once in `docs/agent-operations.md`, so nothing replaces the table.
- Reconciled the split rules: autoreview is stated as required before every commit and landing with no single
  provider required, the ops doc's push rule names `AGENTS.MD` instead of "a rule above", and four bullets it
  duplicated from the global rules are removed so each rule lives once.
- Activated the environment on the MacBook Air on 2026-09-18: rules pointers for Claude, Codex and
  Antigravity, the Codex whole-root skills link, per-skill mirrors for Claude and Antigravity, agent links,
  and additive hook and permission merges. Pre-activation copies of every touched file are under
  `~/Metisary/Enviroment/backups/activation-2026-09-18-macbook-air/`.
- Documented the activated state: what an installed machine's pointers and mirrors look like, the audit
  that reports whether a given machine matches (rules pointers and skill mirrors only), the hand steps
  `install.sh` should automate, and the backup convention.
- Adopted Ryan's global rules file as `AGENTS.MD`, verbatim apart from its own canonical-path header and one
  link line, so the rules every tool reads are now versioned here. The fork's operational rules moved to
  `docs/agent-operations.md`, linked from `AGENTS.MD` and from `tools.md`.
- Adopted the rebuilt environment layout: `agents/` definitions for Claude, Codex, and Antigravity;
  per-tool hook, settings, and MCP files under `config/`; the engineering constitution and PR standards
  under `docs/`; a baseline `checks.yml` workflow; and `skills.lock.json` for install-managed externals.
  Added 36 skills — 28 Firecrawl, four writing skills, `i-have-adhd`, and `nas-portainer-runtime` — and
  grouped them in the catalogue. Moved the Copilot instruction files to `.github/instructions/`, where
  Copilot reads them. Merged the two READMEs into one that describes the target layout and the sync
  mechanism that exists today. The LICENSE keeps the original copyright notice alongside Ryan's.
  Removed `docs/windows.md`. Pinned the lockfile's one external skill to a commit, and allowlisted two
  fake keys used as bad examples in the security instructions so the secret scan stays strict elsewhere.
- Removed the last 1Password routes outside the `keychain` skill. `ssh-doctor` lost its "OP Profile Block",
  which copied a service-account token into `~/.profile` across hosts — the pattern `keychain` forbids and
  nothing here can use. `fleet-profile.mjs` no longer validates an `onepassword_item_id` field for an
  inventory that does not exist. `things-todo` now routes its auth token toward `$keychain` without
  inventing an item name.
- Removed `docs/npm-publish-with-1password.md`, the last file still routing through the deleted `npm` and
  `one-password` skills, and dropped the `op` reference it left in `docs/RELEASING.md`.
- Final sweep of everything outside `skills/`. Rewrote `tools.md` around the CLIs actually installed here
  (`gh`, `repobar`, `mcporter`, `gitleaks`, `xcodes`, `yt-dlp`, `imsg`) instead of the fork author's `bird`,
  `sonoscli`, and Sweetistics; Sonos is reached through the Claude connector, not a CLI. The repo-sync audit
  and update scripts now require an explicit root rather than defaulting to `~/Projects`, which is empty
  here, and `fleet-maintenance` says so. Made the README's sync examples and the sectriage `package`
  line generic. Removed three empty, untracked skill directories left behind by earlier deletions.
- Reconciled `skills.sh.json` with the skills that exist: dropped four catalogue entries for removed
  skills and added five that were never listed. All 31 skills are now grouped, and every grouped name
  resolves to a real `SKILL.md`.
- Cleared the remaining upstream identity from every skill. `wrangler` carried two Cloudflare account IDs
  belonging to the fork author and now defers to `$domain-dns-ops` for the canonical account; `skill-cleaner`
  dropped its OpenClaw log roots, Dropbox skill root, and a `~/.openclaw` probe; the fleet collector now
  looks for Ryan's fifteen installed CLIs rather than the fork's crawlers; `xurl` lost its upstream plugin
  metadata; `project-structure` and `things-todo` lost their last named references.
- Removed `speaking`. It was the fork author's conference workflow end to end, including a live Google Sheet
  identifier and his own travel decisions, and the `gog` CLI every command depends on is not installed.
- Removed `maintainer-orchestrator`, its 214-line openclaw authorship reference, the 53-line policy test,
  and its CI step. The skill coordinated a multi-repository OSS maintainer queue, and its reference file was
  a dated commit-count audit of 24 `openclaw/*` repositories used to decide what fell outside the fork
  author's responsibility. Ryan has eight repositories across two owners, authored by himself and two bots.
- Recorded the Xcode prerequisite on the three Apple skills that need it — `instruments-profiling`,
  `native-app-performance`, and `swiftui-performance-audit`. The note states the requirement and gives a
  check to run rather than asserting what is currently installed, so it cannot go stale once Xcode is
  added. None of the six Apple skills carried upstream contamination, and the three needing no Xcode are
  unchanged.
- Extracted the canonical environment paths into `scripts/canonical-paths.sh`, sourced by both
  `sync-skills` and the skill-link audit, so the two can no longer disagree about where the repo lives.
- CI now runs on every branch push, not only `main` and pull requests, so a broken suite is caught at the
  first push instead of surviving several commits on a feature branch.
- Removed the `release-mac-app` skill and its Sparkle release machinery: 2,968 lines across six files,
  plus `docs/RELEASING-MAC.md`, `docs/mac-app.md`, the `release/sparkle_lib.sh` compatibility shim, and the
  CI step covering its three credential-boundary suites. No repository of Ryan's uses Sparkle, nothing
  sourced the shim, and the skill carried most of the remaining 1Password coupling.
- Removed the tracked `tmp/` scratch files left by the fork's pr474 chunking commits.
- Fixed `sync-skills` and its test fixture, which were left on the old `~/Projects/agent-scripts` layout
  when the skill-link audit moved to `~/Metisary/Enviroment/config`, breaking `test-sync-skills`.
- Updated `AGENTS.MD` for the renamed skills: `$codex-huge-context` is now `$codex-config`,
  `$one-password` is now `$keychain`, and the `op` service-account and `op-work` tmux rule is replaced by
  the `security` rule, which requires scoped reads and a non-empty value because a locked keychain or
  missing item returns empty rather than failing.
- Removed Peekaboo everywhere at Ryan's request: dropped the `vm-lab` skill, whose purpose was Peekaboo
  validation inside Parallels and whose Parallels, Ghostty, and Peekaboo-checkout dependencies are all
  absent; removed it from `fleet-profile.mjs`'s detected-CLI list, from `github-project-triage`'s UI proof
  path, and as the Swift size example in `project-structure`. The Homebrew formula was uninstalled too.
- Restored `preflight.rb` and its test into `codex-config/scripts/` after removing them without naming
  them first, and restored the CI step at the new path. The skill now records what the preflight covers
  and that it fails by design against the current ChatGPT-auth setup, which has no direct provider.
- Removed the `hopper-debugger` and `oracle` skills at Ryan's request, and dropped both from the
  catalogue. This also retires four of the unmapped upstream directories: `~/Projects/oracle`,
  `~/Projects/oracle/dist/scripts`, `~/Projects/Peekaboo`, and the Dropbox Hopper path.
- Renamed `codex-huge-context` to `codex-config` and rewrote it around the setup Ryan actually runs. His
  Codex authenticates with ChatGPT OAuth (`auth_mode = "chatgpt"`, `OPENAI_API_KEY` null) and has no
  provider table or custom catalogue, so the direct-API route, its Keychain auth helper, and the 245-line
  preflight with its tests were removed. The 922K/700K override is now documented as a thing not to add:
  on the ChatGPT route it yields `context_length_exceeded` with a compaction request too large to succeed.
  Kept the provider-independent parts: model and reasoning settings, the shared app-server restart rule,
  login handling, fleet rollout, and verification. Repointed `codex-first`, `project-structure`, and
  `keychain`, whose example cited an auth helper that was never configured here.
- Replaced the `one-password` skill with `keychain`, built on `/usr/bin/security`, because Ryan uses the
  macOS Keychain and Apple Passwords rather than 1Password, which is installed on none of his Macs. The
  guard shape is preserved and the tmux credential sandbox is gone: a Keychain secret pipes straight into
  one command, so there is no environment to contain. Documents the empty-output trap, where a locked
  keychain or missing item returns nothing rather than failing, and gives a verified guard for it.
- Removed the `npm` skill and its eight scripts. Its pipeline required `op`, `tmux`, and an npm login that
  do not exist here, and Ryan publishes no packages; the one publishable package in his repos is another
  maintainer's. Repointed `codex-huge-context`, `oracle`, `twilio-sms`, and `hopper-debugger` at `$keychain`
  without inventing Keychain item names, which each skill's own pass will confirm.
- Made `global-gitignore-audit.sh` report a missing fleet inventory instead of dying with a Node stack
  trace, matching the script's existing prerequisite messages and pointing at `--fleet PATH`.
- Remapped the manager and Codex paths Ryan confirmed: the fleet inventory and manager skills now live
  under `~/Metisary/Enviroment/manager/`, conference strategy under the same root, and the Codex catalogue,
  auth command, and keychain point at his own home. The two `config.toml` values stay absolute because TOML
  does not expand `~`; the keychain path inside the zsh auth script does expand and is left as `~`.
- Restored four `fleet-maintenance` scripts removed earlier on a bad availability check:
  `agent-cli-audit.sh` (Codex 0.155.0 and Claude 2.1.276 are installed in `~/.local/bin`, not Homebrew),
  `fleet-profile.mjs` (its `collect` needs no inventory), `agent-skill-links-audit.sh` (124 Claude and
  94 Codex skills are mirrored), and both test suites, which pass. Repointed the skill-link audit at
  `~/Metisary/Enviroment/config`; it now independently reports the same install drift as a manual check.
- Adapted `github-project-triage` to Ryan's GitHub: owners `Artic0din` and `Plaintext-Lab` (several repos
  were transferred to the org and now redirect), and a project-board pass over the `Development` board,
  which the skill's name implied but never used. Kept RepoBar as the broad-discovery pass and documented
  its installed path, with `gh repo list --json issues,pullRequests` as the fallback; those counts are
  open items only, verified against a live repo. Kept `peekaboo` as the live UI proof path. Removed the
  clawdbot, clawtributors, gitcrawl, and browser-use routes, none of which are installed. The bundled
  activity helper no longer defaults to `openclaw/openclaw` and now requires `--repo` with a clear error.
- Adapted `github-deep-review` to Ryan's review rules: classify the terminal action up front, stay
  report-only by default, deliver findings inline as each is verified, tag them
  `[CRITICAL|PROBLEM|SUGGESTION] file:line` with a verdict, and route pre-existing problems to an issue
  rather than the diff under review. Author context now routes through `$github-author-context` and is
  skipped for Ryan and for bot authors. The evidence, provenance, and fix-quality sections are unchanged.
- Relocated every self-reference after the repo moved to `~/Metisary/Enviroment/config`, replacing 18
  `~/Projects/agent-scripts` and `/Users/steipete/Projects/agent-scripts` paths across the README, docs, and
  skills; each relocated path was checked to resolve. Recorded that the global symlinks are not installed:
  `~/.claude/CLAUDE.md` still resolves to `~/Development/Workspace/Codex/AGENTS.md`, a different file.
  Left `skill-cleaner`'s TypeScript path matching and `release-mac-app`'s in-progress edits alone.
- Adapted `github-author-context` to Ryan's GitHub use: skip himself and bot authors, drop the private
  OpenClaw maintainer tooling and contributor-note helper, and route durable findings to `ryan-knowledge`.
  Corrected two inherited command bugs found by running them — `gh search prs` has no `--state merged`
  (merged is its own flag), and on a private repository search is unavailable while `gh pr list --author`
  returns an empty list instead of failing, so author activity must be filtered client-side.
- Refreshed the vendored `frontend-design` skill from the installed Anthropic plugin revision
  `ea0a38e1d671`, picking up the design-process, AI-default calibration, restraint, and writing-in-design
  sections the old snapshot predated. The copy stays in this repo because Codex cannot load Claude plugins.
  Kept the repo's `LICENSE.txt`, which retains the Anthropic copyright notice the plugin's copy omits.
- Re-enabled `fleet-maintenance` for Ryan's verified three-Mac LAN fleet: host table with SSH reach and
  the non-interactive PATH gotcha, explicit repository roots, and health, Homebrew, npm, repo, macOS, and
  Xcode passes. Removed the upstream Tailscale mesh, inventory profiles, Octopool, 1Password escrow, and
  attribution-stripping requirements, none of which exist in Ryan's environment.
- Repointed `codex-huge-context` and `xcode-sync` host resolution at `fleet-maintenance` instead of the
  absent `computers.yaml` and Tailscale state, and dropped the deleted skill-link audit from the README.
- Fixed `mac-maintenance` scanning the empty `~/Projects`, so its repository pass now reaches Ryan's real
  checkouts instead of silently doing nothing.
- Hardened autoreview against untracked-file disclosure, out-of-checkout Codex reads, project-controlled Claude execution, stale-ref mutation, oversized prompts, and non-UTF-8 paths; disabled the unadapted upstream fleet workflow, restored a truthful 1Password guard route, and aligned release credential routing.
- Tailored domain-dns-ops to Ryan's verified Cloudflare zones, Worker and Pages domains, mail routing, and tunnel-aware DNS workflow.
- Made create-cli's bundled guidelines link independent of checkout location.
- Removed unused messaging, browser, and external-repository skills, and aligned the catalogue and README with the retained local skills.
- Simplified codexbar around installed CLI capabilities and provider-scoped usage checks, removing account-switching and speculative failure assumptions.
- Adapted codex-debugging to installed-version diagnosis, discoverable source checkouts, scoped configuration inspection, and available browser tools.
- Removed the Cloudflare Registrar skill; retained Cloudflare deployment and DNS skills for later customisation.
- Removed the agent-transcript skill and its local transcript-export helper.
- Simplified codex-first for native Claude delegation, inherited Codex model/execution settings, portable skill links, isolated autoreview, and evidence-based worker recovery.
- Restored the local autoreview helper and acceptance harness with executable paths, portable skill instructions, and Codex reasoning/service-tier options.
- Fixed autoreview following untracked symlinks, mishandling quoted Git filenames, and relying on Claude tool preapproval instead of restricting tool availability.
- Fixed autoreview omitting landed changes from merge commits and made it reject oversized inputs.
- Restricted autoreview to Codex and Claude, removed unused engine adapters and JSONL parsing, and disabled inherited Codex integrations and web search when requested.

- Removed OpenClaw relay, ClickClack operations, Peter's remote Mac and Birdclaw routes, Octopool cache guidance, and Obsidian skills; removed the stale ClawSweeper CI step.

- Route intentional Team restarts through one coordinator session on Stable, preserving explicit deployment approval and holding restarts while the coordinator is unidentified or unavailable.

- Require Peter's explicit approval for each Team server deployment and keep automatic deployment disabled, preserving scoped incident repair without an automatic follow-up upgrade.

- Correct the OpenClaw deployment account to `services@openclaw.org`.

- Corrected browser relay timeout recovery to persist canonical controls, distinguish per-step and total startup deadlines, require HTTP base URLs for explicit overrides, explain the 0.13.10 discovery fallback, and verify saved relay-only policy across daemon respawns.

- Pin macOS release credential runners to system Bash so the shared tmux server's PATH cannot select an incompatible shell.

- Fixed false macOS signing-canary failures on long signature reports while preserving Apple trust and Developer ID authority checks.

- Run the Codex direct-route preflight regression suite in CI with a clean environment and temporary HOME, covering private-home auth delivery and secret-safe failures without live credentials.

- Make Codex Keychain helper guidance independent of private reviewer HOME paths and add a secret-safe `--private-home` delivery diagnostic without changing reviewer isolation or provider selection.

- Align shared Codex routing rules with the canonical `codex-first` skill and its launch recipe instead of stale saved-defaults guidance; preserve the model gate and isolated review workflow.

- Added vm-lab bootstrap diagnostics for empty Apple-VZ clone disks and pre-output Bash heredoc stalls, with immutable-source safeguards and invocation-local shell fallback.

- Simplified requested agent transcripts and require scope trimming before previews or publication; helpers that rerender sessions cannot reuse approval of edited Markdown.

- Set `codex-first` workers and Codex-backed reviews to GPT-6 Astra with high reasoning and Fast service, including fresh, resumed, and watchdog launches.

- Removed the retired private launch-skill dependency from shared instructions and Claude routing; Codex workers now inherit saved model, reasoning, and service-tier defaults.

- Scoped release-time-only changelog generation to `openclaw/openclaw`; restored changelog updates at landing and post-release `Unreleased` sections for every other repository.
- Fixed Bash 3.2 escaping of captured macOS release direct-reference values in the private environment handoff.
- Prevented macOS release credential diagnostics from replaying provider stderr or secret-bearing JSON/parser errors; added synthetic regression coverage.
- Fixed skill sync nesting links inside locally owned directories; added bounded allowlisted self-link repair and read-only audit detection.
- Removed the machine-specific 1Password skill from the public skill set; local discovery now uses its private owner.
- Fixed `clawsweeper-status` aborting before activity sections on large workflow snapshots while preserving row caps and upstream errors.
- Fixed `clawsweeper-status` public queue parsing, preserved optional health fields without shifted columns, and added a separate publication-tail summary.
- Added headless Sparkle signing through scoped 1Password references, with public-key validation, mode-0600 temporary files, and cleanup on success or failure.
- Corrected GitHub secret provisioning to omit `--body` for stdin and added a skill validation guard against the literal-dash trap.
- Taught the `clawsweeper-status` snapshot to report queue handoff health, the ready/admissible split, backoff and parked reasons, and shed-since-reset, so exact-review items parked on retry exhaustion are no longer invisible behind a `healthy` verdict.
- Added the `project-structure` skill: a TypeScript symbol-map generator that compresses a repository into one context-loadable file with dense/skeleton/exports tiers, plugin-boundary listings, and measured token budgets.
- Removed the obsolete scoped-commit helper and returned commit recipes to standard Git now that agent work uses isolated worktrees.
- Made the million-token Codex provider and context settings an explicit atomic invariant, with a fatal preflight diagnostic for the unrecoverable `openai` plus 922K/700K split configuration.
- Added a fleet audit and repair action that disables Claude commit, pull-request, and session-link attribution while preserving unrelated settings and detecting higher-precedence overrides.
- Added narrow Homebrew 6 trust handling for exact third-party formulae already declared in a fleet profile.
- Made Apple-classified outdated/unusable Xcode runtimes and unavailable simulator devices required fleet drift, with a booted-device-safe audit and repair action.
- Established the SF Mini's classic OpenSSH fleet path, documented symmetric tailnet TCP 22 policy and proof rules, and recorded the MiniClaw duplicate-daemon regression and public-SSH fallback.
- Added the separately owned SF Mac Mini and distinguished its local/Tailscale names from FoundationClaw while its trusted SSH path remains pending.
- Verified FoundationClaw's provider identity, installed Tailscale and Jump Desktop Connect v10, and documented its data-preserving credential-reset escalation before GUI activation.
- Added ClawMac provider-outage triage that escalates console, NIC-link, and switch-port inspection without repeated power cycles or data-affecting recovery.
- Restored MiniClaw's canonical Homebrew Tailscale node and removed its duplicate GUI identity from fleet guidance.
- Removed obsolete Mac identities from remote fleet discovery guidance after pruning them from Tailscale.
- Reconciled the remote-Mac topology with provider purchases, including FoundationClaw's MacStadium identity and MiniClaw's canonical Tailscale identity.
- Reserved GPT-5.6's maximum output budget in `codex-huge-context` and moved fleet compaction to a verified 922K input window with a 700K safety threshold.
- Made `codex-first` treat the Gorilla-backed Clawdex endpoint as already model-routed, preventing recursive Codex delegation after the fleet proxy migration.
- Added a secret-safe Codex direct-API preflight so million-token launches fail before an unauthenticated Responses request when a machine is missing its Keychain delivery copy.
- Generalized interactive 1Password routing to select the active approval workstation within the matching personal or work-managed environment while preserving service-account isolation and safe offline fallback.

## 2026-07-17 — 0.12.0

### Highlights
- Turned `maintainer-orchestrator` into a long-running control plane for autonomous queue triage, proof-driven changes, dependency maintenance, and release proposals across Peter's repositories.
- Added fleet maintenance, safe repository synchronization, package ownership audits, and Xcode fleet management for Peter's Macs.
- Replaced the old Codex review path with isolated structured autoreview and added Claude Code-only `codex-first` delegation for implementation-heavy work.
- Added `scripts/sync-skills` so Codex and Claude share one canonical skill and instruction mirror across agent-scripts, manager, and repo-owned skills.
- Hardened 1Password, npm, and macOS release workflows around scoped service access, stable tool identities, noninteractive signing, and verified publication boundaries.

### Maintainer Orchestration
- Expanded `maintainer-orchestrator` with one tracked Codex thread per repository, 30-lane scheduling, durable status, forgotten-work preservation, exact-head landing, dependency sweeps, VISION capture, and release-readiness proposals.
- Added a dedicated OpenClaw mode with root-owned discovery, qualified execution lanes, contributor routing, live permission checks, serialized landing, and OpenClaw-specific proof and changelog rules.
- Added autonomous GitHub queue triage with URL-first item briefs, maintainer-comment routing, author context, live proof requirements, safe spam closure, and explicit Peter decision briefs.
- Added the non-majority repository ledger, owner-maintained crawl-family overrides, and clearer root ownership for orchestration policy and worker titles.
- Made dependency updates, internal operating repositories, bounded cleanup, safe dirty fast-forwards, and candidate-scoped release blockers autonomous.
- Improved ClawSweeper status reporting for worker capacity, exact-review occupancy, workflow waiters, bounded API reads, and accurate failure and closure counts.
- Tightened shared agent policy around exact-head proof, contributor credit, screenshot safety, post-merge recaps, background-task visibility, public mutation, and release authority.

### Review and Agent Workflows
- Replaced `codex-review` with structured `autoreview`, adding isolated Codex, Claude, and Pi review, safe bundle validation, regression provenance, security checks, parallel tests, and bounded multi-pass review.
- Added Claude Code-only `codex-first` routing for implementation, fixing, exploration, rebasing, and landing mechanics, including safe use of the ChatGPT app-bundled Codex CLI. Thanks @notorious-d-e-v.
- Added current model, effort, fast-mode, liveness, deterministic resume, and self-delegation guardrails to the Codex workflow.
- Made GitHub deep review and project triage prefer current source, real behavior reproduction, exact PR heads, and factual contributor trust signals.
- Routed screenshot and login-dependent browser work through existing Chrome state, with safe attach recovery and no silent isolated-browser fallback.
- Added explicit compatibility contracts, clean bounded-refactor guidance, generated-code skepticism, and scoped opportunistic cleanup rules.

### Fleet, Release, and Remote Operations
- Added `fleet-maintenance` for host health, package updates, repository synchronization, ownership collisions, disk cleanup, and service-impact reporting.
- Added `xcode-sync` for signed Xcode inventory, stable and prerelease slot management, build-identity checks, platform compatibility, and verified installation.
- Added dependency-light fleet repo audit and update helpers with batched snapshots, clean fast paths, dirty-work preservation, collision checks, and safe fast-forwards.
- Added `release-mac-app` and shared macOS release helpers for changelog notes, Sparkle appcasts, signing, notarization, GitHub assets, and post-release verification.
- Hardened macOS releases for passwordless isolated keychains, preloaded secrets, modern distribution validation, Bash 3.2, lightweight tags, bracketed changelog versions, and archive version parsing.
- Refreshed remote-Mac topology and network-boundary guidance, signed local app testing, locked-Mac Git fallback, and Cloudflare-only ClickClack deployment.
- Kept GitHub reads on the Octopool shim and added cache-health recovery before live GitHub fallback.

### Credentials and Safety
- Unified 1Password work on one tracked tmux session with scoped service-account access first, consent-gated desktop fallback, exact-field reads, known-item routing, and TCC-safe `~/bin/op` updates.
- Unified npm authentication around reusable service sessions, safe field selection, token caching, login fallback, package reservation, publication verification, and a generic authenticated command wrapper.
- Added internal-information, confidentiality, device-aware image upload, API-key storage, and approved-destination guardrails without blocking authorized private research.
- Standardized the canonical test Gmail account, OpenClaw deployment account, personal versus corporate Mac routing, and pre-approved Gmail service login behavior.

### Skills and Tools
- Added `scripts/sync-skills` to build Codex whole-root links, Claude's flat skill mirror, shared instruction pointers, deterministic collision handling, and stale-link pruning.
- Added skills for fleet maintenance, Xcode sync, Codex delegation, Twilio SMS, Wrangler, Things, Reminders, SSH diagnosis, agent transcripts, and shared macOS releases.
- Added `skill-cleaner` inventory, duplicate, usage, and prompt-budget audits plus isolated `--root-only` scans. Thanks @its-How.
- Added browser-tools network capture with filtering and follow mode. Thanks @mvanhorn.
- Hardened browser-tools startup, profile copying, symlink handling, and console flags. Thanks @ShiroKSH.
- Fixed xurl's OpenClaw npm installer metadata. Thanks @not-stbenjam.
- Made skill validation explicitly UTF-8-safe under C locales. Thanks @chaochaoweb3.
- Added skills.sh grouping metadata for shared skills. Thanks @vyctorbrzezowski.
- Exposed shared behavior validation, session viewing, crabbox, and crawl-family skills through the canonical mirror while removing duplicated bundled copies.

## 2026-05-14 — Video Transcript Dependency Update
- Updated `video-transcript-downloader` to `youtube-transcript-plus` 2.0.0.

## 2026-05-14 — Codex Review Finding Detection
- Updated `codex-review` to capture review output, report elapsed time, fail on reported P0-P3 findings, and treat empty review output as non-clean.

## 2026-05-14 — Codex Review Full Access
- Added `codex-review --full-access` for nested review runs that need localhost bind/listen tests without sandbox noise.

## 2026-05-14 — GitHub Search Shim Guidance
- Added AGENTS guidance to prefer shimmed `gh` / `gitcrawl gh` for broad reads and avoid raw Search API POST mistakes.

## 2026-05-14 — Codex Review Base Caveat
- Documented that `codex review --base` must not include an inline prompt; use a separate follow-up pass for custom instructions.
- Clarified that committed or PR branch review must use branch/base mode, not `--uncommitted` / local mode.

## 2026-05-14 — Codex Review Loop Guidance
- Clarified that `codex-review` should iterate until no accepted findings remain and document intentional rejections with useful inline comments when warranted.

## 2026-05-14 — README Skills Overview
- Rewrote the README around agent instructions, skills, helper scripts, and sync expectations; removed stale copied-origin notes.

## 2026-05-14 — Codex Review Skill
- Added a `codex-review` skill and helper for closeout reviews, with stdout-only default output and subagent filtering guidance for noisy review output.

## 2026-05-13 — Checkout Discipline
- Added CLI checkout/worktree guardrails: stay in repo cwd by default, never create worktrees unless asked, and treat sibling checkouts under `~/Projects` as user-managed.

## 2026-05-13 — Skill Metadata Guardrails
- Added generic skill-description guidance and quieter browser recovery notes to reduce noisy auth prompts and token-heavy skill metadata.

## 2026-05-11 — clawmac GUI Access Note
- Documented the Peekaboo through Jump Desktop workflow for clawmac GUI prompts and Chrome Safe Storage verification.
- Documented `crabmac` as Peter's typo/alias for `clawmac`.

## 2025-12-22 — Remove Custom rm Shim
- Dropped `bin/rm` and `scripts/trash.ts`; rely on the system `trash` command for recoverable deletes.

## 2025-12-17 — Remove Runner; Keep Guardrails
- Removed the `runner` wrapper and `scripts/runner.ts` now that modern Codex sessions handle long-running/background work directly.
- Kept the safety-critical bits as standalone shims: `bin/rm` (moves deletes to Trash via `scripts/trash.ts`).
- Dropped the `find -delete` interception and the `bin/sleep` shim.

## 2025-12-02 — Release Preflight Helpers
- Added shared release helpers in `release/sparkle_lib.sh`: clean working-tree check, Sparkle key probe, changelog finalization/notes extraction, and appcast monotonicity guard for version/build.
- Documented the helper functions in `docs/RELEASING-MAC.md` so Trimmy/CodexBar-style release scripts can reuse them.

## 2025-11-18 — Console Log Capture
- Added `console` command to `scripts/browser-tools.ts` for capturing and monitoring Chrome DevTools console output with real-time formatting, type filtering (log, error, warn, etc.), continuous follow mode, and configurable timeouts with automatic object serialization.

## 2025-11-22 — Search & Content Extraction
- Added `search` and `content` commands to `scripts/browser-tools.ts` for Google SERP scraping with optional readable markdown extraction and single-URL readability output, leveraging the existing DevTools-connected Chrome instance.
- `eval` now supports `--pretty-print` to inspect complex objects with indentation and colors.

## 2025-11-15 — Chrome Browser Tools
- Added `scripts/browser-tools.ts`, a DevTools-ready Chrome helper copied from the Oracle repo so agents can inspect, screenshot, and terminate sessions without dragging in the full CLI. The workflow is inspired by Mario Zechner’s [“What if you don’t need MCP?”](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/).
- Documented the new helper in the README so downstream repos know how to run `pnpm tsx scripts/browser-tools.ts --help`.

## 2025-11-16 — Browser Tools Pipe Detection
- Updated `scripts/browser-tools.ts` to enumerate and kill Chrome instances started with `--remote-debugging-pipe` (the default for Peekaboo/Tachikoma) in addition to the classic `--remote-debugging-port`. List/kill now show “debugging pipe” when no port exists and still fetch tab metadata when it does.
- README now notes the optional `NODE_PATH=$(npm root -g)` trick so the helper can run from bare copies of the repo without a local `package.json`.

## 2025-11-14 — Compact Runner Summaries
- The runner's completion log now defaults to a compact `exit <code> in <time>` format so long commands don't repeat the entire input line.
- Added the `RUNNER_SUMMARY_STYLE` env var with `compact` (default), `minimal`, and `verbose` options so agents can pick how much detail they want without editing the script.
- Timeout heuristics now understand both `pnpm` and `bun` invocations automatically, so long-running Bun scripts/tests get the same guardrails without repo-specific patches.
- `sleep` invocations longer than 30 seconds are clamped to the 30s ceiling instead of erroring, which keeps wait hacks working while still honoring the AGENTS.MD limit.

## 2025-11-08 — Sleep Guardrail & Git Shim Refresh
- Runner now rejects any `sleep` argument longer than 30 seconds, mirroring the AGENTS rule and preventing long blocking waits.
- Added `bin/sleep` so plain `sleep` calls automatically route through the runner and inherit the enforcement without extra flags.
- Simplified `bin/git` to delegate directly to the runner + system git, eliminating the bespoke policy checker while keeping consent gates identical.

## 2025-11-08 — Guardrail Sync & Docs Hardening
- Synced guardrail helpers with Sweetistics so downstream repos share the same runner, docs-list helper, and supporting scripts.
- Expanded README guidance around runner usage, portability, and multi-repo sync expectations.
- Tightened path ignores and refreshed misc. helper utilities (e.g., `toArray`) to reduce drift across repos.

## 2025-11-08 — Initial Toolkit Import
- Established the repo with the Sweetistics guardrail toolkit (runner, git policy enforcement, docs-list helper, etc.).
- Ported documentation from the main product repo so other projects inherit the identical safety rails and onboarding notes.
