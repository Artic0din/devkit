---
summary: Vendored tstack PR-workflow skills, their dependencies, and how they interact with local rules.
read_when:
  - Updating the vendored tstack skills or changing PR workflow rules.
---

# Vendored tstack skills

Source: [Theo Browne's tstack](https://github.com/t3dotgg/tstack/tree/11e37a74d0a6868c121cd0910ab2b3bd9873b92a).
Revision: `11e37a74d0a6868c121cd0910ab2b3bd9873b92a`.
License: [MIT, Copyright 2026 Theo Browne](licenses/tstack-MIT.txt).

The skills are vendored with local attribution and review-completion changes described below.
When updating, review the upstream diff from the pinned revision and preserve those changes.

| Skill | Invocation | Uses |
| --- | --- | --- |
| `full-send` | "full send" | `sol-loop`, `file-pr`, `babysit-pr` |
| `full-stop` | "full stop", including a closing "Full stop." | `full-send` |
| `council` | "council" | Three models from different providers |
| `sol-loop` | "sol loop" | A GPT Sol reviewer |
| `file-pr` | Filing, opening, or creating a PR | `leaving-pr-comments` |
| `takeover` | Taking over a PR, branch, or agent thread | `modernize`, `file-pr`, `babysit-pr`, `leaving-pr-comments` |
| `babysit-pr` | Watching or babysitting a PR | `leaving-pr-comments`, `scripts/pr-wait` (needs `python3`) |
| `modernize` | Rebasing or modernizing an old PR | `leaving-pr-comments` |
| `leaving-pr-comments` | Automatic for any GitHub comment | None |

All skills need an authenticated `gh`.
`council` and `sol-loop` need subagents on other providers' models; T3 Code provides them through `delegate_task`.

## Interaction with local rules

`AGENTS.MD` still governs where it is stricter.
Known overlaps:

- `full-send`, `full-stop`, and `modernize` allow `--force-with-lease` on the task's own branch after a rebase.
  `AGENTS.MD` forbids force-pushing a rewrite during review; outside those explicit requests, push fixes as new commits.
- `full-send` grants merge permission only when the user says "full send".
- `full-stop` also triggers on a closing "Full stop.", which can be ordinary emphasis.
  If the message is not plainly asking for PR delivery, `AGENTS.MD` says to stop and ask first.
- `council` fixes known issues and outstanding PR comments before an audit.
  `AGENTS.MD` keeps reviews and audits read-only by default, so make those edits only when the request also asks for fixes or delivery.
  Problems outside the diff still go to an issue.
- `council` counts only required delegates toward round completion and final sign-off.
  Delegates explicitly marked non-blocking by the user remain optional feedback.
- Upstream `leaving-pr-comments` and `file-pr` ask for model attribution on comments and PR bodies.
  The vendored copies drop it, because `AGENTS.MD` bans agent attribution unless a repository's template requires AI disclosure, and `scripts/validate-skills` fails if it returns.
