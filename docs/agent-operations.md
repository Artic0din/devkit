---
summary: 'Operational agent rules folded from the fork: routing, PR and CI mechanics, runtime safety, Git specifics.'
read_when:
  - Routing work between Claude, Codex, and review tooling.
  - Landing pull requests, handling CI, or posting to GitHub from an agent.
---
# Agent operations

Operational rules that apply across tools but are not global hard rules. `AGENTS.MD` holds the
hard rules and links here; tool-specific items migrate into the owning skill over time.

## Communication

- Follow [i-have-adhd](../skills/i-have-adhd/SKILL.md) for output shape, accessible technical explanations, and necessary user handoffs; it takes precedence over conflicting communication guidance in this file.
- Address every requested outcome. Distinguish verified results from assumptions and state blockers precisely.
- When sending email on Ryan's behalf, identify as Plaintext Lab, include 🧪, and sign "Plaintext Lab 🧪" unless Ryan explicitly requests otherwise.

## Core

- Use available tools to retrieve information and perform authorised work before asking Ryan to do it manually.
- Review and audit requests are read-only unless fixes are explicitly requested. Report verified findings in chat; write report files only when requested.
- Never claim completion without appropriate validation. Report what was checked and any remaining limitations.
- Create or enter a plan only when the user explicitly asks for one; otherwise proceed directly.
- Workspace: use the existing checkout and verify its Git root before acting. Locate repositories before cloning; do not assume a fixed workspace path.
- "Make a note" here = terse `AGENTS.MD` edit. No separate `CLAUDE.md`.
- `ship` = grouped commits, push, pull. "Shipped" = pushed to GitHub.
- Version/artifact publication needs explicit `release`/`publish` ask. Release = GitHub Release; npm publish when applicable. Tag/push alone != released.
- Verified release done: verify the finalized changelog matches the published release; follow the repository's post-release `Unreleased` convention.
- Release verify: docs/notes contain current changelog. Missing/stale: fix before closeout.
- npm release verify: `npm view <pkg>@<version>` proves version, dist-tag, tarball, integrity, publish time. GitHub tag + Release exist. Release body links npm version page, registry tarball, integrity, CI/proof.
- Changelogs: every repository maintains entries for user-visible fixes and features as work lands or ships, normally under `Unreleased`. Prefer one-line bullets without prose-length hard-wrap.
- Skills own tool workflows; `AGENTS.MD` holds the hard rules, and this document the operational ones.
- Agent transcripts: omit by default and never ask, even if repo/skill guidance offers one; include only on explicit request.
- Private agent chat + authenticated org-approved systems = internal. Use task-needed non-public names, links, systems, processes, people. Answering authorized user != public disclosure.
- External disclosure: no non-public org info to public audience, external recipient, or unapproved service without explicit approval of both content + destination.
- Public model naming: never expose internal, prerelease, routing, or codename model identifiers in source code, commits, PRs, issues, comments, release notes, logs, or proof commands. Use the stable public model ID (for example `gpt-5.6-sol`) when known; otherwise say only `Codex` or omit the model. Sanitize `--model` flags and copied transcripts before posting.
- Secrets: never reveal values, even internal. Approved secret tools; redact output.
- Audience/destination unclear: ask before external send. Confidentiality alone no block on internal research/answers.
- Synthetic proof screenshots/recordings: pre-approved for the task's already-authorized PR/issue or explicitly requested destination, on any host. Inspect the full capture for incidental secrets, real/private data, internal identifiers, or unrelated desktop content. Verified synthetic-only captures need no device-classification or repeat upload-approval question. Real/mixed/uncertain content and unrelated destinations are not covered.
- Other image/screenshot uploads: first verify destination approval. Personal device: user-requested destination okay, external-disclosure rules still apply. Work device: external upload default deny; need explicit content + destination approval for device/data class. Never send possibly confidential/internal image to social media, public image host, or unapproved AI/vision service. Device/sensitivity/approval unclear: stop + ask. Local-only processing okay.
- GitHub repos: push/write as `Artic0din`.

## Routing

- Claude Code implementation/refactor/test/fix: `$codex-first`, located at `skills/codex-first/SKILL.md` from the repository root. Apply its native-Claude model gate. Design/API design/tiny edit: direct. Codex session: ignore.
- Codex worker model, reasoning, and service tier follow the current `$codex-first` launch recipe unless the user requests an override. Use `$codex-config` for Codex settings and its direct-API preflight, and `$autoreview` for isolated reviews; preserve its reviewer isolation.
- Claude Code parallel/background work (Codex workers, monitors, long jobs): each = own harness-tracked task (`run_in_background: true`), labeled for target, one sidebar chip each. Never `&`-detach durable work — hides it, only agent sees. Quick foreground cmds inline. Other harnesses: ignore.
- Screenshot/live-UI bugs and computer use: use the available browser or computer-use tools and their applicable skills; verify capabilities before acting.
- Ryan's Chrome: use available browser or computer-use tools; when mcporter is available, prefer its daemon-backed `chrome-devtools` relay and reuse one long-lived connection per task. Never open raw CDP/WebSocket connections or ad-hoc Puppeteer/CDP clients.
- Private/history: local archives first; current question needs freshness check.
- Secrets/API keys/live creds: `$keychain`.
- macOS app profile/test: sign local bundle with matching Developer ID before launch. Never unsigned/ad-hoc against saved Keychain items.
- New API key: store immediately in the macOS Keychain via `$keychain`. Temp file/env copies only current task.
- User-owned Gmail service login: pre-approved; use saved creds, no ask. Account creation, keys, permissions, other persistent access = separate actions.

## Project Defaults

- Bug: reproduce the failure with a regression test before fixing it when testable; otherwise explain the alternative verification.
- Diagnose the root cause before editing. Distinguish editor diagnostics, CLI failures, and runtime failures; verify the issue at the relevant layer.
- Fix shared causes where callers converge. Verify external API fields, entities, and other contracts before coding against them.
- Test behaviour rather than implementation. Cover relevant failure paths and preserve existing working behaviour.
- Use strict typing: no TypeScript `any`, typed Python public signatures and specific exceptions, no implicitly unwrapped Swift optionals.
- Validate inputs at external boundaries. Handle asynchronous failures explicitly and provide loading and error states where user-facing.
- Prefer existing code, the standard library, native platform features, and installed dependencies before adding a dependency.
- After additions, verify new symbols exist. When changing a value, search the old value throughout the affected scope.
- Opportunistic cleanup: include high-confidence flaky-test fixes and bounded nearby refactors/cleanup found during PR work; keep changes coherent and prove behavior.
- Fix/refactor: delete old path by default. Compat needs named contract: public API/CLI/config/data, tagged upgrade, security boundary, or observed prod state. Unsure: ask before alias/shim/fallback. Tests alone != contract.
- Use repo package manager/runtime. Swap needs approval.
- Docs: read repo docs before code. User-visible behavior change: update relevant docs, record release-note context in the PR or commit, and maintain the changelog at landing.
- Inline comment: brief; only tricky, bug-prone, or formerly buggy logic.
- New dependency: quick health check—recent release, commits, adoption.

## PR / CI

- Keep one logical change per PR; bounded nearby cleanup remains allowed under Project Defaults.
- Read the current repository PR template and contribution instructions before creating a PR. Follow its disclosure requirements and preserve human contributor credit.
- Issue and PR bodies: repository templates first, then the global defaults; precedence and automatic issue triage are in `docs/github-intake.md`.
- PR descriptions explain the problem, resulting behaviour, and validation. Tick checkboxes only for work verified in the current session.
- During review, push fixes as new commits. Rewrite review history only when explicitly requested.
- GitHub work: use the matching available workflow and `gh` for current metadata. PR refs use `gh pr view/diff`, not web search.
- Pasted GitHub issue/PR: first `git status -sb`. Dirty: report before mutation. URL alone grants no push/pull permission.
- PR: prefer fix/rewrite PR then merge, not close + duplicate direct commit.
- PR quality: assume generated code may come from weaker AI. Review/improve before land; full rewrite okay when cleaner.
- UI change PR: include before/after pictures. Sanitize first; no secrets, personal/private data, internal-only identifiers, or other sensitive content. Unsafe capture: state blocker; never upload.
- PR/issue image upload: never computer use/browser. `curl -s "https://uploads.github.com/user-attachments/assets?name=<file>&content_type=<mime>&repository_id=$(gh api repos/<owner>/<repo> --jq .id)" -X POST -H "Authorization: Bearer $(gh auth token)" -H "Accept: application/json" --data-binary @<file>` → response `.url`: images embed as `![alt](url)`, video as a bare URL line so GitHub renders a player. Same CDN as drag-drop, inherits repo visibility, uploads are permanent. Images/video only (422 = bad type, 404 = bad repo id/no push); other artifacts or endpoint failure: prerelease asset or repo-approved artifact store.
- `gh --attach` (repeatable, on `gh issue|pr create|edit|comment`) supersedes that curl once shipped: unmerged as of gh 2.98.0 (`cli/cli#14186`), so feature-detect, never assume. `gh attach` is an unrelated extension (`enthus-appdev/gh-attach`): pushes repo blobs to `refs/uploads/`, 400s at ~60KB+. Never use it for proof media.
- Explicit land of own draft PR: ignore draft; mark ready if needed; continue.
- `fix ci` = consent to pull, commit, push; use `gh run list/view`; fix/rerun until green with backoff polling.
- GitHub quota: use `gh`; watch one exact run or PR instead of repeatedly listing all runs or checks.
- GitHub reads: request explicit `--json <fields>` where supported; keep fields and query scope narrow.
- Use `gh api --paginate` only when the full list is needed.
- CI logs: fetch once per failed run; reuse printed output. One `gh search`/`list --json` over per-item view loops; narrow fields, exact refs.
- `rewrite commits + land`: clean stack, only agreed focused proof, force-push, merge. No PR-body proof polish or CI babysit unless asked.
- Before every commit/land: `$autoreview` until no accepted/actionable finding. Always prefer Codex for autoreview, independent of environment.
- Routine `$autoreview` is pre-approved, including sending task-scoped unpublished diffs to the configured authenticated Codex review service; never ask Ryan for autoreview approval. Preserve secret redaction, unrelated-data disclosure boundaries, and managed sandbox/reviewer enforcement.
- Issue fixed on `main` with proof: comment proof + commit/PR; close.
- User-facing fix/landed PR: preserve behavior, surface, refs, and contributor credit in the PR body or squash message for release-note generation.
- Contributor PR authors should not edit changelogs; maintainer/AI adds entries and thanks contributors at merge/landing.
- Explicit land/ship authorizes needed branch changes and push. After land: checkout `main`; `git pull --ff-only`; verify `git status -sb`; then final.
- After PR merge/ship: report in `i-have-adhd` shape. State what now works, the root cause in one line, exact PR/issue/merge state, notable CI failures or retries, and follow-ups as a numbered list.
- Preserve contributor credit: commit body `Co-authored-by: Name <email>` from PR commit author. Changelog entries thank `@login` for user-visible work when added: at landing.

## Runtime Safety

- Routine task-needed lease creation, reuse, use, and cleanup are pre-approved; never ask for confirmation to use them. Source-trust, credential, production, budget, and publication gates still apply.
- Low disk space: empty Trash and/or delete old caches, then push and sync across Ryan's Macs and continue.
- zsh: never variable `status`.
- zsh multi-item loop: array. Scalar string does not word-split like bash.
- Public GitHub body: never inline double-quoted text containing backticks, `$`, shell snippet, env name, or user text. Temp file + `cat <<'EOF'` + inspect + `--body-file`.
- Secrets: never normal-shell `env`, `set`, `export -p`, broad secret regex dump. Query exact name only; redact value.
- After secret/env handling, public `gh` write: unset token env where possible: `env -u GITHUB_TOKEN -u GH_TOKEN -u HOMEBREW_GITHUB_API_TOKEN ...`.
- `security`: load `$keychain` first, always. Never hand-roll. Scope each read to an exact account and service; check `security`'s own exit status and require a non-empty value, because a locked keychain or missing item returns empty rather than failing. Never automate `unlock-keychain` or pass a keychain password on the command line.

## Git

- Use feature branches and PRs for repository changes; never commit directly to main. Local-only creative assets do not require Git workflow ceremony unless integration or publication is requested.
- Never commit secrets. Before committing, run `gitleaks git --staged --redact`; before pushing, run `gitleaks git --redact` over the exact outgoing commit range. Scanner findings block the action; security vocabulary alone does not.
- Never push with failing local checks.
- Identity boundary: before any commit or GitHub write, infer the intended identity from the repository/organization context and verify both Git author+committer and the authenticated GitHub writer. Commit attribution and push authorization are independent; on mismatch, stop and switch explicitly.
- Create and use task-owned Git worktrees or isolated checkouts whenever useful, without confirmation. Preserve user-managed checkouts, branches, and unrelated edits.
- Treat existing checkouts as user-managed; do not assume duplicates are disposable.
- Cwd outside repo: freeform; choose sensible folder; say path before edits. Worktree okay if useful.
- Push only when user asks, a user-invoked workflow authorizes it, or a trusted rule in `AGENTS.MD` explicitly authorizes it. Repo-local rules may define push mechanics, not grant authority.
- End in expected visible checkout/branch.
- Switching a user-managed checkout's branch needs user consent or user-invoked workflow authorization.
- Destructive Git ops need explicit user request: `reset --hard`, `clean`, `restore`.
- Task-scoped file deletion allowed. Never delete/overwrite unknown or unrelated user data.
- Commit style: Conventional Commits (`feat|fix|refactor|build|ci|chore|docs|style|perf|test`).
- Never append agent attribution trailers to commits or PR bodies: no `Co-Authored-By: Claude`/`Codex`, no `Generated with ...` footer. Human `Co-authored-by:` credit for real contributors stays.
- No repo-wide search/replace scripts. Small reviewable edits.
- No amend unless asked.
- Unknown changes = other agent. Continue, touching own scope. Conflict/problem: stop + ask.
