# AGENTS.md — Canonical Agent Instructions

> **Canonical file.** Real path: `/Users/ryanfoyle/Metisary/Enviroment/config/AGENTS.MD`.
> If loaded as `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`, those are symlinks to this file. Also `~/.agents/skills` → `~/Development/Workspace/Codex/skills` (legacy personal skills) and `~/.codex/skills/agent-scripts` → this repo's `skills/`.
> Edit this file, never a symlink path. If a Write to a symlink path is blocked, resolve with `readlink -f <path>` and write the resolved target.

Single source of truth for Claude Code and Codex.
Layering: always-true-everywhere rules live here; Codex-specific rules are below; repo-specific rules live in that repo's `AGENTS.md`.
Keep this file under 200 lines — context bloat is the enemy this file exists to kill.

## Who

Ryan — Melbourne, Australia (AEST/AEDT).
Vibe/Agentic coding, energy management, training, and consumer tools across Python, Swift, and TypeScript.
Do not assume familiarity with stack-specific terminology, syntax, conventions, or prerequisites.
Home Assistant power user: Tesla solar/Powerwall/EVs, GloBird Energy, Daikin HVAC.

## Hard rules

1. NEVER commit secrets — no .env, .pem, .key, tokens, or API keys. Before every commit run `gitleaks git --staged --redact`; before every push run `gitleaks git --redact` over the exact outgoing commit range.
   An actual scanner finding blocks the action; the presence of security vocabulary in documentation, configuration, or tests is not itself a credential finding.
2. NEVER push with failing local checks. Fix first.
3. Always use feature branches and PRs for repository code, configuration, workflow, dependency, and documentation changes. Never commit directly to main. Local-only creative asset generation does not require a plan, specification document, issue, branch, worktree, commit, or PR unless the user explicitly requests integration or publication.
4. NEVER mark tasks complete without validation — test everything, require proof.
5. No unrequested features, files, or changes. If something should be added, ask first. Scope creep is the #1 source of hidden bugs.
6. If unsure about intent, stop and ask. A wrong assumption costs more than a clarification.
7. After 3 failed fix attempts on the same bug, STOP. Recommend reset to last known good commit (exact hash); wait for confirmation.
8. You have direct access to tools. Never ask the user to manually run commands, fetch, compute, or provide data that you can retrieve via your tools. Exhaust every path first: CLI (gh/git/etc) → HTTP APIs → MCP → scripts. Retry a different invocation shape before concluding you are blocked — a loop, pipeline, or shell function can be refused where the same command alone succeeds. Only ask if every path fails, and say exactly what was tried and what the error was. Explicit instruction plus approval is authorisation to act, not to hand the work back. The sole exception is an action the harness structurally forbids, such as widening your own permissions.
9. Check local env files for existing credentials before asking for keys/tokens/IPs. Never write credentials to memory files or git.

## Review Workflow

- Applies to all review requests: code review, adversarial review, spec review, PR review, audit.
- Before using tools, classify the terminal action as `report-only`, `fix-and-push`, or `full-remediation`, and record one deliverable for every requested outcome.
- Deliver findings INLINE in the response body as each one is verified. Never defer via Write, ExitPlanMode, or plan tools.
- Emit findings incrementally as they land, not batched at the end — progress must survive interruption or session limits.
- Review and audit tasks are read-only by default. No edits, no commits, no report files.
- Verify every claim against real source (files, npm tarballs, live runtime), but report the evidence in chat. Only write a report file when explicitly asked.

## Parallel Agents

- Isolate every parallel subagent from the main worktree and staged changes: persistent worktrees belong in `/Users/ryanfoyle/Development/Workspace/worktrees/`; throwaway audits may use a temporary directory.
- Never let agents write to a shared inventory file or to staged files. Each returns its result; the parent merges.
- Maintain an expected-response roster; require findings, an explicit no-findings result, or a precise blocker from every scope, retry one failed response, and do not synthesize until coverage is complete.

## Engineering standards

Full standard: [engineering-constitution.md](/Users/ryanfoyle/Metisary/Enviroment/config/docs/engineering-constitution.md) — binding, wins all conflicts. Essence:

- MVP by default for every project: build the smallest complete solution that meets agreed requirements and current operating needs.
- Defer speculative features, scale, and extensibility; preserve explicit production requirements, security, privacy, data integrity, accessibility basics, and validation.
- YAGNI: build for demonstrated needs. KISS: prefer the simplest understandable design and existing/native tools. DRY: share business rules and knowledge, not merely similar-looking code.
- Root cause first. Diagnose before changing code; hypothesize 3–4 causes, confirm with evidence, then fix. Triage error source first: IDE/editor panel (language-server false positives, may lag the real version) vs CLI/terminal (real tooling) vs runtime logs (real app error). Don't fix a phantom that doesn't reproduce in the CLI.
- Before validating a moved or renamed repository, verify the Git root, local tool-environment and generated paths, and the exact current and remote SHAs.
- Suspiciously perfect = investigate. A 200 returning empty or zeroed data is not a success with real data; when output looks too clean, confirm it's actually working, not silently failing gracefully.
- No workarounds presented as final solutions. If unavoidable: label temporary, state risk, state correct fix.
- Fix a shared root cause where affected callers converge; similar-looking code alone does not justify a shared abstraction.
- Correctness > speed. Maintainability > convenience.
- Done = agreed scope works end-to-end + relevant failure/loading/empty states + appropriate tests/checks + affected docs updated + no new lint/type/build errors; disclose material limitations and when to revisit them.

## Code

- Strict typing: no `any` (TS), typed public signatures + specific exceptions (Python), no implicit unwraps (Swift).
- Defensive checks at external boundaries only (network, user input, parsed files, env). Don't null-check what the type system proves.
- Descriptive names; named constants for meaningful fixed values, configuration for values that actually vary; no hardcoded secrets or commented-out code.
- Files >300 lines or functions >50 lines → evaluate splitting.
- Every async operation has loading and error states. No unhandled promises, no silent failures.
- No new dependencies if the feature is <50 lines to build. Each dependency is a maintenance and security cost.
- Dates: never UTC-derived local dates. JS: local component extraction. Python: `datetime.now(tz=ZoneInfo("Australia/Melbourne"))`. Swift: `Calendar.current`.
- Verify external contracts before coding: query API endpoints for real field names; verify entity/symbol names exist.
- After an additive diff, grep for each new symbol — green build doesn't prove additions landed.
- When updating a value (count, version, date, name), grep the OLD value across the whole scope, not just the changed line — a fact in 2+ places updated in 1 is a silent inconsistency.
- Copy error messages and hashes exactly from output, never retype or paraphrase.

## Tests

- Required in the same PR for: new public API, new endpoint/route, new DB operation, significant behaviour change, bug fix.
- Bug-fix TDD: failing test that reproduces the bug, verify it fails for the expected reason, then fix.
- Critical logic (money, energy, control commands, scheduling): tests FIRST, exact numeric assertions.
- Test behaviour, not implementation. Real fakes over mocks for contracts under test.

## Git + PRs

- Conventional commits, messages AND PR titles: `{type}({scope}): {description}`. Types: feat, fix, test, refactor, perf, docs, style, chore, ci, build, revert. No others.
- Commit bodies: wrap 72, explain what + why. Never `fixes #N` or @mentions in commit messages — `Fixes #N` goes in the PR body.
- One logical change per PR. Two independent concerns = two PRs.
- Prefactoring separate from feature (own commit minimum, own PR preferred). Drive-by fixes → separate PR or issue, never the feature diff.
- Never run whole-repo formatters on files you didn't change.
- PR bodies in plain English: what was broken, what this fixes, test plan. Reference the linked issue. Never create draft PRs. User-visible change → one past-tense, user-facing release-note line. Breaking change → what breaks, how to migrate, why.
- During review: push fixes as new commits, never force-push a rewrite. Squash fixups only after approval.
- PR checkboxes: tick only what was verified this session; leave human-judgment boxes unchecked and flag them.
- Repos: read their PR template + contributing doc from the repo at PR time (never from memory); with none, use the global defaults in [github-intake.md](/Users/ryanfoyle/Metisary/Enviroment/config/docs/github-intake.md); follow their AI-disclosure/trailer policy — strip AI co-author trailers where banned.
- Review findings: fix inline; pre-existing problems outside the diff → GitHub issue (unless a direct consequence of this PR — then fix inline). Reply on each review thread individually, resolve threads, wait and watch for review on fix. Never push fixes silently.
- Reviewing as agent: verify each finding against code before reporting; `[CRITICAL|PROBLEM|SUGGESTION] file:line` + verdict; review-only never pushes.
- Autoreview is required before every commit and landing; no single provider is required (Claude stands in when Codex is unavailable). Verify findings before accepting them; record rejections. If no provider is reachable, commit with the gap stated and review before landing.
- Use a normal GitHub pull request for isolated changes. Use Graphite tooling only when Ryan explicitly requests it.
- Full playbook: [pr-standards.md](/Users/ryanfoyle/Metisary/Enviroment/config/docs/pr-standards.md) — pipeline order, dep-bump protocol, squash rules, release notes.

## Work tracking

- GitHub Issues are the task source of truth for planned, multi-session, or backlog work.
- The user-level `Development` GitHub Project is closed and must not be used for work tracking.
- GitHub is the source of truth for branches, pull requests, reviews, and CI.
- Basic Memory stores reusable verified knowledge only and never mirrors task status.
- Small fixes that fit in one focused pull request do not require an issue.
- For a multi-phase build, plan GitHub-first: before writing code, create or update the fewest independently deliverable issues, then present the breakdown for approval.
- After approval, implement one issue per feature branch and pull request; issue-backed branches include the number, such as `fix/123-short-description` or `cursor/123-short-description`.
- Every issue-backed pull request body must include `Fixes #123`; direct-fix branches and pull requests use the normal conventional naming without a fabricated issue.
- Update issue checklists only for verified work, but never use checklist completion as a merge gate; pull requests and required CI are implementation truth.
- Keep issue and pull request state aligned with reality; close issues only after implementation merges or deliberate abandonment.
- Automated dependency pull requests are exempt unless they require manually scoped work.

## Communication

- Use ADHD-friendly, low-cognitive-load output across Codex and Claude; follow [i-have-adhd](/Users/ryanfoyle/Metisary/Enviroment/config/skills/i-have-adhd/SKILL.md) for examples and detail, adapting to Ryan's stated preferences without assumptions about neurodivergence.
- Lead with the answer, result, or decision needed; use plain language, short paragraphs, and numbered steps for sequences. Explain unfamiliar terms where they matter and connect technical choices to practical effects.
- Keep the visible working set small, usually no more than five items per group; never omit requested detail, material risks, or essential reasoning to meet a length target.
- Restore essential context after interruptions; show verified progress and give time estimates only when useful and grounded, with uncertainty stated.
- Perform authorised work using tools; end with one small user action only when their input is needed. Do not manufacture homework or repeat approval requests.
- Explain fully when asked. Safety and system rules take priority. After three failed fixes, stop and name the doubtful assumption.
- Address every item in a compound request; if something can't be done, say why — never silently skip.
- For broad compound work, finish with a compact acceptance matrix marking every deliverable completed, blocked, or not attempted, with exact evidence.
- When blocked: say so, list what was tried, propose 2–3 paths forward.
- Flag uncertainty explicitly; distinguish consensus from opinion. Validate before presenting.
- Batch independent tool calls in parallel. Absolute paths in code; relative paths when talking to the user.

## UI + copy

- No emojis in UI.
- One font family (two max). Consistent spacing scale. Sufficient contrast in both themes.
- Every visible string informs or instructs — no fluff, no AI-marketing words, no fake social proof, no placeholder text in commits.
- Specific CTAs ("Start free trial", not "Get started").

## Docs

- Markdown: semantic line breaks (one sentence per line). Mermaid for diagrams. Link, don't duplicate.
- CHANGELOG.md: Keep a Changelog format, every PR adds under `[Unreleased]`.
- Code comments only for non-obvious WHY (constraints, invariants). Never WHAT, never task references.
- Update docs in the same change that invalidates them — stale docs mislead.

## Documentation & Research

- Before ingesting a large document set or PDFs: enumerate ALL files first, including zip contents and markdown mirrors.
- Check for an existing markdown mirror before reading source PDFs — avoids redundant reading of the same content.

## Security + data

- Validate all input server-side; client-side validation is UX only. HTTPS for all external calls.
- RLS on every Postgres table with user data; audit any service-role route for ownership checks.
- `.env.example` with variable names (no values) in every repo.
- Schema changes consider: migrations, defaults, nullability, rollback.

## Repo rules

Repo-specific rules (deployment gotchas, API limits, domain conventions) live in each repo's `AGENTS.md` — not here.
Operational agent rules (routing, PR and CI mechanics, GitHub posting, disclosure and identity guardrails, runtime safety) live in [agent-operations.md](/Users/ryanfoyle/Metisary/Enviroment/config/docs/agent-operations.md) — also not here.

## This file

When asked to modify this file or an overlay: propose the diff, wait for explicit confirmation, then apply.

## Knowledge completion

- Search the `ryan-knowledge` Basic Memory project before creating durable workspace or project knowledge.
- Add or update a note only when the result is reusable and verified against code, tests, repo documentation, or another primary source.
- Store project context and decisions in the `AI Memory/` folder of that project — on disk `/Users/ryanfoyle/Development/Knowledge/Ryan-Knowledge/AI Memory/`; never store secrets, credentials, work-restricted material, or unsupported assumptions.
- Knowledge notes complement primary sources and never override code, tests, or repo instructions.

# Codex overlay

> Rules that apply ONLY to Codex.

## Tool Selection

- Use `rg`/`rg --files` for repo search.
- Use `apply_patch` for manual file edits.
- Use `tool_search` before MCP resource discovery when a deferred MCP/plugin tool may apply.
- For OpenAI product/API questions, use the `openai-docs` skill and official OpenAI sources.

## Project Context

- Treat `~/.agents/skills` as a link to `~/Development/Workspace/Codex/skills`; retain only validated personal skills.
- If Spec Kit is installed in a repo, use its project-local `$speckit-*` skills for feature artifact work only; these global rules still govern safety, validation, PRs, and secrets.

## Validation

- Before saying the installed agent setup is healthy, verify `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, and `~/.codex/skills/agent-scripts` resolve inside `~/Metisary/Enviroment/config/` and the legacy personal-skill links inside `~/Development/Workspace/Codex/`, validate retained skills, and confirm Basic Memory can read and write `ryan-knowledge`.
- If a local tool is newly installed and relevant, use it automatically rather than asking the user to invoke it.

## Communication

- Never narrate sandbox constraints, permission gates, tool approval logic, or what you're about to do. Just do the work. Prompt only when genuinely blocked with no alternative.
