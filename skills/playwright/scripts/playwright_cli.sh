#!/usr/bin/env bash
# Modified by Artic0din/agent-scripts for a pinned runtime, trusted browser
# configuration, Node.js prerequisites, and separator-aware session handling.
set -euo pipefail

node -e 'if (Number(process.versions.node.split(".")[0]) < 20) { console.error("Playwright requires Node.js 20 or newer"); process.exit(1); }'

runtime="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/runtime" && pwd -P)"
cli="$runtime/node_modules/@playwright/cli/playwright-cli.js"
if [[ ! -f "$cli" ]]; then
  echo "Error: install the pinned CLI with: (cd '$runtime' && npm ci --ignore-scripts --no-audit --no-fund)" >&2
  exit 1
fi

has_session_flag="false"
for arg in "$@"; do
  case "$arg" in
    --) break ;;
    --config|--config=*)
      echo "Error: use the trusted runtime/config.json; project configuration overrides are disabled." >&2
      exit 1
      ;;
    --session|--session=*|-s|-s=*)
      has_session_flag="true"
      ;;
  esac
done

command_name="$(node - "$runtime" "$@" <<'NODE'
const root = process.argv[2] + '/node_modules/playwright-core/lib/tools/cli-client/';
const { minimist } = require(root + 'minimist.js');
const help = require(root + 'help.json');
const args = minimist(process.argv.slice(3), {
  boolean: [...help.booleanOptions, 'all', 'g', 'help', 'json', 'raw', 'version'],
  string: ['_'],
});
process.stdout.write(args._[0] || '');
NODE
)"
cmd=(node "$cli")
case "$command_name" in
  open|attach) cmd+=(--config "$runtime/config.json") ;;
esac
if [[ "${has_session_flag}" != "true" && -n "${PLAYWRIGHT_CLI_SESSION:-}" ]]; then
  cmd+=(--session "${PLAYWRIGHT_CLI_SESSION}")
fi
cmd+=("$@")

exec "${cmd[@]}"
