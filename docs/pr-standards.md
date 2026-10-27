# PR Standards — Full Playbook

Canonical PR/commit/review practice for all coding agents (Claude Code, Codex, Antigravity).
Distilled from Kubernetes contributor guides (pull-requests, release-notes) and Home Assistant core agent skills (raise-pull-request, ha-review, bump-dependency), adapted to Ryan's solo + upstream-contribution workflow.
AGENTS.md carries the short rules; this doc is the detail behind them.

## PR scope and size

- One logical change per PR. Two independent concerns = two PRs.
- Prefactoring is its own PR (or at minimum its own commit): if a feature needs restructuring first, land the restructure separately, then the feature. Reviewers must never untangle "moved code" from "changed code" in one diff.
- Drive-by fixes found while implementing (bad names, dead code, unrelated bugs) go to a separate PR or a GitHub issue — never into the feature diff.
- Many small PRs beat one monolith. A PR too big to review in ~30 minutes should be split.
- Never open repo-spanning mechanical PRs (mass lint fixes, global rename, search/replace) without prior agreement from the repo owner/maintainer. If agreed, state in the PR body exactly how the edit was generated so reviewers can reproduce it.

## Commits

- Subject: conventional commits `{type}({scope}): {description}`. Types: feat, fix, test, refactor, perf, docs, style, chore, ci, build, revert. No others. Imperative mood, ≤72 chars, no trailing period. Test: "If applied, this commit will `<subject>`".
- Body: wrap at 72 chars. Explain WHAT changed and WHY — the commit message is the permanent record; PR comments are not. One-liner commits acceptable only when the why is self-evident.
- Never use GitHub closing keywords (`fixes #N`, `closes #N`, `resolves #N`) or @mentions inside commit messages — keywords misfire on cherry-picks and forks, mentions spam on every rebase. Put `Fixes #N` in the PR body instead.
- Commit sequencing: group logically distinct ideas into separate commits (prefactor / feature / tests can be separate). Avoid both extremes — one giant commit and 25 fragment commits.

## Review-fixup protocol

- While a PR is under review, push fixes as NEW commits — never force-push a rewrite mid-review. The reviewer diffs only the new commit instead of re-reading everything.
- Squash before merge, not before: "sausage" commits (fixups, review responses, `fix test`, `address comments`) get squashed once the PR is approved. "Layers" (independent changes building to one goal) stay separate.
- Squashing auto-fix/formatter commits before the FIRST push is fine and expected (pre-push hygiene). The no-rewrite rule starts when review starts.

## PR body

- Use the repository's PR template; without one, use the global default for the change type ([github-intake.md](github-intake.md)).
- Plain English: what was broken, what this fixes, test plan. Reference the linked issue (`Fixes #N` here, not in commits).
- Release note line: any user-visible change (CLI/API/UI/config/behaviour/perf/deprecation/security fix) gets a one-sentence user-facing summary in the body, past tense, written for users not developers ("Fixed X not updating when Y" — not "refactored coordinator"). Tests/build/unreleased-bug fixes need no release-note line — but CHANGELOG.md `[Unreleased]` is still updated in every PR (docs-check enforces it); use a `Changed`/`Internal` entry for non-user-facing work.
- Breaking change or deprecation: dedicated section stating (1) what breaks, (2) how users fix/migrate, (3) why it was necessary. Include "action required" phrasing when the user must do something.
- Mechanical/AI-bulk edits: state how the change was generated.
- Never create draft PRs.

## Verification before PR (pipeline order)

Run in order; STOP and report on any failure — never create the PR on a red step:

1. Establish merge-base against the target branch; diff from merge-base, not HEAD~n.
2. Run the repo's lint/format hooks scoped to changed files. Commit any formatter-generated changes as their own commit.
3. Run tests for the touched scope. Failing tests = stop.
4. Diff hygiene: confirm the final diff touches ONLY intended files (especially after codegen/regeneration steps).
5. Grep for each new symbol added (additive-diff verify) and for the OLD value of anything updated (count/version/date) across the whole scope.
6. Secrets scan over everything the PR ships, not just what is currently staged: `git diff <merge-base>..HEAD | grep -iE 'key|secret|token|password'` — any match, stop. (The staged-only variant misses secrets already committed on the branch.)

## Checklist honesty

- When a PR template has checkboxes, tick ONLY items actually verified in this session. Items requiring human judgment ("I understand the code", "manually tested on hardware", "generated code carefully reviewed") stay unchecked, flagged in the handoff for Ryan.
- Report after PR creation: PR URL, what passed/failed, which boxes were left unchecked and why, what Ryan must do.

## Contributing to upstream/external repos

- Read the upstream's PULL_REQUEST_TEMPLATE.md and CONTRIBUTING doc from the repo at PR time — never hardcode or reconstruct a template from memory; they change.
- Preserve template structure exactly: all type-of-change options stay listed, exactly one gets `[x]`. Remove sections only when the template says to.
- PR title doubles as the release-notes entry on many upstreams (HA does this): write it as a complete, specific sentence fragment — "Fix Hikvision NVR binary sensors not being detected", not "fix sensors".
- AI policy compliance: check whether the upstream requires AI-assistance disclosure (k8s does — one sentence in the PR body) or bans AI co-author trailers (k8s bans them). Where banned, strip `Co-Authored-By: Claude` and similar trailers before pushing. You must be able to explain every line; if you can't explain it, don't submit it.
- Respond to upstream review comments substantively and specifically; never paste generated boilerplate replies.
- Small focused PRs, no repo-wide formatting, no fork-only CI in upstream PRs (existing PowerSync rule — applies to all upstreams).

## Reviewing PRs (agent as reviewer)

- Review dimensions: correctness/bugs, style consistency with surrounding code, performance, security, test coverage, docs updated.
- Verify findings before reporting: for each candidate finding, re-check it against the actual code (spawn parallel verification subagents when available). Report only findings that survive. Plausible-but-wrong findings are worse than silence.
- Don't praise what's fine; report only what needs attention.
- Output format: one line per finding — `[CRITICAL|PROBLEM|SUGGESTION] file:line — issue`. End with a verdict: approve / request changes / comment.
- Check whether prior review comments were actually addressed before adding new ones.
- Review-only means review-only: never push changes while acting as reviewer.

## Dependency-bump PRs

- One package (or one tightly-coupled set) per PR. Title: `chore(deps): bump <package> to <version>` (own repos) or the upstream's convention.
- Resolve the real release tag programmatically — GitHub tag formats are inconsistent (`v1.2.3` / `1.2.3` / `release-1.2.3`); never guess compare URLs.
- PR body links the changelog or compare view between old and new versions.
- After regenerating lockfiles/requirements, verify the diff contains only the intended manifest + generated files.
- Run tests for everything that consumes the bumped package, not just the build.

## Merging

- Native GitHub squash merge is the normal merge path after required CI passes and every review thread is resolved.
- Agents never invoke a direct merge or bypass protection.
  An explicit user request may authorize a specific manual merge.
- When a current pull request conflicts with its base, the scoped repair automation merges the base into the existing branch without rebasing or force-pushing.
  The detector revalidates the exact head and base revisions, posts the `cursor-merge-conflict-repair` marker comment, and Cursor acts only on that marker in the configured repositories.
  Close the pull request only when it is superseded, unsafe to repair mechanically, or explicitly abandoned.
