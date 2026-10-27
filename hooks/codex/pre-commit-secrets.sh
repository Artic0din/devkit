#!/usr/bin/env bash
set -euo pipefail
if ! bash "$(cd -P -- "$(dirname -- "$0")/.." && pwd -P)/check-staged-secrets.sh" >/dev/null 2>&1; then
  printf '%s\n' '{"systemMessage":"Staged-secret check needs attention. Run gitleaks git --staged --redact and do not commit until it passes. This host check is advisory; Git-hook enforcement requires per-checkout installation."}'
fi
