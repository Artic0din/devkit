# Hooks

`hooks/pre-commit` runs `scripts/validate-skills` before each commit.
Opt in once per checkout with `git config core.hooksPath hooks`.

`hooks/claude-worktree.py` and `hooks/codex/` hold the Claude Code and Codex hook scripts; their tests sit beside them.
