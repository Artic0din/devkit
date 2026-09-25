#!/usr/bin/env bash
set -euo pipefail

runtime="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/runtime" && pwd -P)"
cli="$runtime/node_modules/@playwright/cli/playwright-cli.js"
if [[ ! -f "$cli" ]]; then
  echo "Error: install the pinned CLI with: (cd '$runtime' && npm ci --ignore-scripts --no-audit --no-fund)" >&2
  exit 1
fi

has_session_flag="false"
for arg in "$@"; do
  case "$arg" in
    --session|--session=*)
      has_session_flag="true"
      break
      ;;
  esac
done

cmd=(node "$cli")
if [[ "${has_session_flag}" != "true" && -n "${PLAYWRIGHT_CLI_SESSION:-}" ]]; then
  cmd+=(--session "${PLAYWRIGHT_CLI_SESSION}")
fi
cmd+=("$@")

exec "${cmd[@]}"
