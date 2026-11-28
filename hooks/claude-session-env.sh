#!/bin/bash
# Claude Code SessionStart hook: put scripts/agent-bin first on PATH for the session's
# commands, so agent builds use its shims (see scripts/agent-bin/xcodebuild).
set -euo pipefail
[[ -n ${CLAUDE_ENV_FILE:-} ]] || exit 0
bin=$(cd "$(dirname "$0")/../scripts/agent-bin" && pwd -P)
printf 'case ":$PATH:" in *:%q:*) ;; *) export PATH=%q:"$PATH" ;; esac\n' "$bin" "$bin" >> "$CLAUDE_ENV_FILE"
