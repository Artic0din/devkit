---
summary: Vendored tstack PR-workflow skills, their dependencies, and how they interact with local rules.
read_when:
  - Updating the vendored tstack skills or changing PR workflow rules.
---

# Vendored tstack skills

Source: [Theo Browne's tstack](https://github.com/t3dotgg/tstack/tree/7de017b3fc9d50c03cf3ecb98fb71e0ca65a78bd).
Revision: `7de017b3fc9d50c03cf3ecb98fb71e0ca65a78bd`.
License: [MIT, Copyright 2026 Theo Browne](licenses/tstack-MIT.txt).

The skills are copied unmodified.
When updating, review the upstream diff from the pinned revision and copy the changed folders.

| Skill | Invocation | Uses |
| --- | --- | --- |
| `full-send` | "full send" | `sol-loop`, `file-pr`, `babysit-pr` |
| `full-stop` | "full stop" | `full-send` |
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
- `leaving-pr-comments` prefixes every agent-authored GitHub comment with a model attribution note.
- `file-pr` ends PR bodies with a model and harness line; repositories that ban AI attribution take precedence.
