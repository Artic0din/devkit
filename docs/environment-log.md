---
summary: 'Decision log and chat-only work for the environment rebuild, shown on the status page.'
read_when:
  - Making or recording a decision about how the development environment is set up.
  - Agreeing work in a chat that has no GitHub issue or pull request.
---

# Environment log

Decisions about how the development environment is set up, and work that exists only in chats.
`scripts/env-board.py` combines this file with live GitHub status into one page:

```bash
python3 scripts/env-board.py --open
```

Keep each row to one line, and keep `|` out of the cells.
Anything tracked as a GitHub issue or pull request belongs on GitHub, not here.
When a row below becomes an issue, delete the row so the item is not tracked twice.

## Decisions

One row per decision, newest first.
`Where` links the pull request or commit, or says `chat` when it was decided in conversation.

| Date | Decision | Why | Where |
|---|---|---|---|
| 2026-10-25 | Track decisions and chat-only work in this log, shown on one status page with live GitHub status | Decisions and to-dos from chats were scattered across conversations, pull requests and evidence folders, with no single view | chat |
| 2026-10-25 | Remove Basic Memory from the rules and skills | It was already uninstalled; the `ryan-knowledge` project and its folder no longer exist, so the rules pointed agents at nothing | [#61](https://github.com/Artic0din/devkit/pull/61) |
| 2026-10-13 | Remove the `/cos` Chief of Staff skill and its memory workflow | You chose the existing P3 Stack workflow instead | [#55](https://github.com/Artic0din/devkit/pull/55) |
| 2026-10-12 | Move the shared repository baseline check into DevKit | First step in consolidating shared workflows into DevKit, approved in #33 | [#50](https://github.com/Artic0din/devkit/pull/50) |
| 2026-10-10 | Point every repository and workflow reference at `Artic0din/devkit`, keeping installed folders and links where they are | GitHub does not redirect reusable workflow references after a repository rename | [#48](https://github.com/Artic0din/devkit/pull/48) |
| 2026-09-26 | Default every project to the smallest complete MVP, with YAGNI, KISS and DRY | The rules demanded speculative scale and discouraged deferring optional work | [#27](https://github.com/Artic0din/devkit/pull/27) |
| 2026-09-25 | Drop the dangerous-Git blocker hook from the default tool configs, keeping the secret checks | You asked for it; the pre-commit secret checks stay on | [#12](https://github.com/Artic0din/devkit/pull/12) |
| 2026-09-19 | Remove the active-repos table from `AGENTS.MD` | All eight paths had gone stale, and it needed editing every time a checkout moved | [#11](https://github.com/Artic0din/devkit/pull/11) |
| 2026-09-18 | Version the global rules as `AGENTS.MD` in this repository | The rules lived only on disk, outside any repository | [#7](https://github.com/Artic0din/devkit/pull/7) |
| 2026-09-18 | Keep rules, skills, agents, hooks and MCP config for every tool in one repository | One rebuilt layout for Claude Code, Codex, Cursor, GitHub Copilot and Antigravity | [#6](https://github.com/Artic0din/devkit/pull/6) |

## Work not on GitHub

Status is one of `waiting on you`, `in progress`, `blocked`, `pending` or `done`.
Mark finished rows `done` so they show under "What changed and why".

| Date | Item | Status | Why | Next step |
|---|---|---|---|---|
| 2026-10-17 | Bring the installed checkout at `~/Metisary/Enviroment/config` up to date with `main` | waiting on you | Agents load their rules and skills from it, and it is on an old branch with uncommitted local changes | Decide what to keep from its local changes, then switch it to `main` |
| 2026-10-25 | Delete the leftover `basic-memory` tool and `~/.basic-memory/` | waiting on you | Nothing uses them since Basic Memory was removed, but deleting them destroys `memory.db` | Say yes or no |
| 2026-10-17 | Stop Cursor finding the two gstack test-fixture skills under `skills/gstack/test/fixtures/context-bill/` | waiting on you | Cursor's skill discovery exposes them as skills, and editing the vendored gstack pack would be undone on its next update | Choose a discovery or link-layout fix |
