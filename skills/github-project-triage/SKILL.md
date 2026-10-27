---
name: "github-project-triage"
description: "GitHub issue/PR triage: queues, project board, CI, blockers, risk, proof, next actions."
---

# GitHub Project Triage

Always use this skill when the user types `triage`, unless the request explicitly targets a
non-GitHub domain. From inside a repo, triage that repo by default.

Triage means maintainer-facing item cards: URL, what each issue/PR is about, why it matters, fit,
risk, proof/test state, blockers, and next action. Never return only queue numbers or opaque refs.

Output is URL-first: every surfaced issue, PR, or repo item includes its GitHub URL in the first line
or first sentence for that item. For a shortlist, print one URL per item.

Triage of a single newly opened issue (classify, duplicates, missing information, one outcome label) follows the
repository's `.github/triage/PLAYBOOK.md`, or the global `templates/github/triage/PLAYBOOK.md`; see
`docs/github-intake.md`. Adopting repositories run it automatically on every new issue.

## Owners and scope

Ryan's work spans two owners:

- `Artic0din` — personal repositories, and the user-level project boards.
- `Plaintext-Lab` — the org holding most active products.

Several repositories were transferred to the org, so an `Artic0din/<name>` reference may redirect.
`gh` follows the redirect, but report the canonical name it returns rather than the one you typed.

```bash
gh repo view <owner>/<name> --json nameWithOwner -q .nameWithOwner
```

Do not broaden beyond the current repo unless the user says `broad`, `all`, `everything`, or names
owners. For broad triage, scan both owners above.

## Project board

Issues are the task source of truth, and the user-level `Development` board (project `2`) tracks them
across both owners. Read it before ranking a queue, because board status is Ryan's own judgement and
outranks anything inferred from labels.

```bash
gh project list --owner Artic0din
gh project view 2 --owner Artic0din --format json
gh project item-list 2 --owner Artic0din --format json --limit 400
```

`Status` is a single-select with: `On Hold`, `Researching`, `Todo`, `In Progress`, `Reviews`,
`Complete`, `Out of Scope`. Items also carry `Repository`, `Labels`, `Milestone`, `Linked pull
requests`, `Parent issue`, and `Sub-issues progress`.

Treat `On Hold` and `Out of Scope` as explicit decisions: do not resurface them as candidates.
`In Progress` and `Reviews` usually mean someone is already on it, so check before starting.

```bash
gh project item-list 2 --owner Artic0din --format json --limit 400 |
  jq -r '.items[] | select(.status=="Todo") | [.repository, .title] | @tsv'
```

Some items carry no status at all. A `select(.status==...)` filter drops them silently, so check for
them explicitly rather than assuming the board is fully classified:

```bash
gh project item-list 2 --owner Artic0din --format json --limit 400 |
  jq -r '.items[] | select(has("status") | not) | [.repository, .title] | @tsv'
```

Per-repo boards also exist. Use them when the task names one, and the `Development` board otherwise.

## Local repo gate

Before starting work inside a local checkout, verify it is ready:

```bash
git status --short --branch
git branch --show-current
git pull --ff-only
git status --short --branch
```

Proceed only when the branch is the default branch, the pull succeeds, and the worktree is clean. If
the branch differs, the pull fails, or `git status --short` shows changes, stop and ask. Do not
switch branches, stash, commit, reset, restore, or clean without explicit direction.

## Current-repo triage

Resolve the repository:

```bash
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)
if [ -z "$repo" ]; then
  url=$(git remote get-url origin 2>/dev/null || true)
  repo=$(printf '%s\n' "$url" | sed -E 's#^git@github.com:##; s#^https://github.com/##; s#\.git$##')
fi
printf '%s\n' "$repo"
```

If the repo has a `VISION.md`, read it before judging what can be handled autonomously; it is the
product-fit source of truth. Otherwise use the autonomous-fit rules below.

```bash
gh issue list --repo "$repo" --state open --limit 50 \
  --json number,title,author,labels,createdAt,updatedAt,url
gh pr list --repo "$repo" --state open --limit 50 \
  --json number,title,author,isDraft,reviewDecision,mergeStateStatus,createdAt,updatedAt,url
```

Read all comments before acting. Ryan's own comments are authoritative routing instructions: if he
says it looks good, needs changes, is superseded, is approved, or is not wanted, that overrides bot
labels and ordinary triage judgement. Where he has not commented, use your own judgement and say the
call is yours.

Then inspect enough detail to explain every surfaced item. For roughly ten open items or fewer,
inspect all of them; for larger queues, inspect the top slice and say what was not expanded.

```bash
gh issue view <n> --repo "$repo" \
  --json number,title,author,body,comments,labels,createdAt,updatedAt,url
gh pr view <n> --repo "$repo" \
  --json number,title,author,body,comments,files,commits,isDraft,reviewDecision,mergeStateStatus,statusCheckRollup,createdAt,updatedAt,url
gh pr diff <n> --repo "$repo" --patch
```

Only comment, close, merge, rerun, or patch with strong evidence, and only when asked.

## Triage output

Scan open issues and open PRs, then return:

- `Autonomous candidates`: items that look fixable or landable without more product input, with URL,
  why they qualify, required verification, and confidence. This is a selection for review, not
  permission to start work unless the user also asks for autonomous execution.
- `Needs Ryan`: items blocked on his decision, product direction, missing credentials or access, live
  proof that cannot be obtained, security or privacy judgement, or a board status he already set.
- `Defer/close/supersede`: stale, duplicate, or overlapping items where the likely action is not new
  code.

For every plausible autonomous candidate, use a subagent or independent review to sanity-check
feasibility before presenting it. Give it only task-local evidence and ask whether the item can be
completed autonomously, what verification is required, and what could make it unsafe. Without that
tooling, do the same depth yourself and say so.

## Autonomous work mode

When the user says `do work autonomously`, `keep going`, or similar, treat it as permission to
process the eligible queue sequentially until no safe item remains, each is landed, closed or
deferred with proof, or a blocker needs Ryan.

Never work multiple tickets at once. For each item:

1. Read the issue or PR, related code, docs, CI, and `VISION.md` if present. Check current docs when
   facts may be stale.
2. Decide if it is autonomous:
   - Go: bugfixes with a repro and root cause; performance work that does not balloon complexity;
     small UI tweaks; docs fixes; narrow test or internal fixes; low-risk dependency and CI cleanup
     with green proof.
   - Ask first: new features, product or vision choices, broad behaviour changes, risky dependencies,
     security-sensitive changes without strong proof, provider work without usable credentials, and
     anything that cannot be tested end to end.
   - Prefer a clean bounded refactor when it is the better fix. Do not default to a small patch that
     leaves worse design.
3. Implement it the best maintainable way, on a feature branch, never on the default branch.
4. Verify locally and end to end where possible. For UI behaviour use the repo's own expected proof
   path, such as its test suite or screenshots. For API or provider behaviour, use a real usable key
   or account through the expected secret workflow. If the needed access is missing, stop and say so
   rather than reporting the item done.
5. Run `$autoreview` before landing unless the change is trivial or docs-only, and address its
   accepted findings.
6. Ensure CI is green and the PR body and changelog are right. Land, close, or comment with evidence,
   then return to the default branch, pull `--ff-only`, and verify a clean worktree before the next
   item.
7. After landing, comment with exactly how it was tested: local commands, live proof, CI state,
   landed commit, and caveats. Include the screenshot path when an image matters and no uploader is
   available, rather than silently omitting it.
8. Update the board item's status to match reality.

Do not end autonomous mode with dirty files or an unpushed local fix unless blocked. If blocked,
state the exact blocker, current branch and status, proof already gathered, and the next decision
needed.

## Trust signals

Include author trust for any non-Ryan, non-bot item you recommend acting on. For Dependabot and
Copilot items, a terse bot line is enough.

```bash
skills/github-project-triage/scripts/github-activity.sh --repo <owner/repo> --global <login>
```

Use `$github-author-context` when a PR needs deeper judgement: security-sensitive changes, broad
diffs, new accounts, or unusual author behaviour.

Keep trust output factual:

```text
Trust: @login; acct 2021-04-03; repo 2 PRs/1 issue/0 commits in 12mo; GitHub 9 PRs/3 issues/12 reviews; signal: known contributor / new drive-by / bot / unknown.
```

Trust is not proof. It changes review depth, not correctness.

## Item evaluation

Classify each item:

- `bug`: require a repro, log, failing test, or current-default-branch proof where feasible; identify
  root cause before recommending a fix or merge.
- `feature`: require an end-to-end test plan. Name exactly what credential, account, device, or
  service access is missing before the work can be called complete.
- `dependency`: explain the package group, major or minor risk, failing checks, runtime changes, and
  whether to split.
- `security`: raise priority, require code-path proof and tests, and do not merge on rationale alone.
- `docs/internal`: lower risk, but still explain user-visible relevance and stale-churn risk.

Judge each on `Fit` (good/mixed/poor), `Risk` (low/medium/high, with blast radius), `Proof` (CI,
local repro, failing test, end-to-end, or missing), `Blocker`, and `Next` action.

## Broad queue map

Only when the scope is broad. RepoBar is the first pass: it is faster than hand-rolled `gh` loops and
already understands repo activity, issue and PR counts, local checkouts, auth, and filters.

`repobar` is on `PATH` via `/opt/homebrew/bin/repobar`, a symlink into the installed app bundle.

```bash
repobar_cmd() {
  if command -v repobar >/dev/null 2>&1; then
    repobar "$@"
  else
    /Applications/RepoBar.app/Contents/MacOS/repobarcli "$@"
  fi
}

repobar_cmd status --json
```

PR queue, the primary triage order:

```bash
repobar_cmd repos --scope all --only-with work \
  --owner Artic0din --owner Plaintext-Lab --sort prs --json
```

Issue pressure, as a second pass:

```bash
repobar_cmd repos --scope all --only-with work \
  --owner Artic0din --owner Plaintext-Lab --sort issues --json
```

Use `--plain` for a compact terminal view, and `--forks` or `--archived` only when the user asks for
everything or wants archaeology. A repo with zero issues but open PRs is still triage-relevant.

```bash
repobar_cmd repos --scope all --only-with work --owner Plaintext-Lab --sort prs --json |
  jq -r '.[] | [.fullName, .openIssues, .openPulls, .activityTitle, .activityActor] | @tsv'
```

Preserve RepoBar's count order when summarising: do not surface a lower-PR repo while omitting a
higher-PR one from the same owner scope.

`gh repo list` is the fallback if RepoBar is unavailable. Its `issues` and `pullRequests` totals are
open items only:

```bash
gh repo list <owner> --limit 100 --no-archived --json name,issues,pullRequests,updatedAt
```

## Detail pass

After the queue map, inspect only the top repos unless the user wants exhaustive detail.

```bash
repobar_cmd issues <owner/name> --limit 50 --json
repobar_cmd pulls <owner/name> --limit 50 --json
repobar_cmd ci <owner/name> --limit 20 --json
repobar_cmd activity <owner/name> --limit 20 --json
```

For PRs that look mergeable or suspicious, switch to `gh` for maintainer-grade state:

```bash
gh pr view <n> --repo <owner/name> --json number,title,state,author,isDraft,mergeStateStatus,reviewDecision,statusCheckRollup,updatedAt,url
gh pr diff <n> --repo <owner/name> --patch
gh run list --repo <owner/name> --branch <branch> --limit 10
```

For issues that may already be fixed, use `gh issue view`, then read current source before commenting
or closing.

## Local cross-check

Use this when the task mentions local project state, dirty repos, or "what do I own here". Ryan's
checkouts are under `~/Developer` and `~/Development/projects`; `~/Metisary/Projects` is the migration
target. Scan the roots that hold repos.

```bash
repobar_cmd local --root "$HOME/Developer" --depth 2 --limit 200 --plain
repobar_cmd local --root "$HOME/Developer" --depth 2 --sync --limit 200 --json
```

Do not run destructive local actions (`local reset`, branch deletes, checkout moves) unless the user
explicitly asks.

## Triage heuristics

Prioritise:

- PRs with green or nearly-green CI, and low-risk dependency, docs, or test changes.
- Board items in `Todo` that already carry a clear repro or owner path.
- Security, release, auth, install, CI, and data-loss reports before cosmetic items.
- Issues that are reproducible, recently reported, or block a release.

Deprioritise:

- Board items marked `On Hold` or `Out of Scope`; those are decisions, not backlog.
- Archived and fork queues unless asked.
- Old broad feature requests with no repro or owner signal.
- Feature work needing unavailable keys or accounts for end-to-end proof.
- Broad generated changes without a clear user problem or test plan.

## Output shape

For current-repo triage:

```text
Repo: owner/name
Board: Development #2 — <n> items for this repo (<status breakdown>)
Source: gh list/view/diff/checks, local source/tests where inspected

Immediate:
- #123 PR: title — <url>
  What: one-line summary in plain words.
  Type/Fit/Risk: bug|feature|dependency; good|mixed|poor; low|medium|high because ...
  Board: Todo | In Progress | not on board
  Trust: @login; acct date; repo/global activity; known/unknown/bot.
  Proof: CI/repro/test/e2e state.
  Blocker: none / missing key / failing lint / unclear direction.
  Next: exact action.

Needs Ryan:
- #124 issue: ...

Defer/close:
- #125 issue: ...

Skipped:
- <why>
```

For a broad scan:

```text
Owners scanned: Artic0din, Plaintext-Lab
Source: RepoBar <command summary>, plus gh for selected PRs/issues

Top queues:
- owner/repo: X issues, Y PRs; why it matters; next action

Immediate actions:
- <small obvious merge/fix/comment/rerun, with item summary>

Needs Ryan:
- <larger or ambiguous queues, with item summary>

Skipped:
- archived/forks/missing access/etc.
```

When asked to act, keep going: inspect the selected items with `gh`, fix CI, comment, close or merge
only with evidence, and report the exact commands and proof.
