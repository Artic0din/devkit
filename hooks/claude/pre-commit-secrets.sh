#!/usr/bin/env bash
set -euo pipefail
message_field=systemMessage
permission_field=
if [[ "${1:-}" == --copilot ]]; then
  message_field=additionalContext
elif [[ "${1:-}" == --cursor ]]; then
  message_field=agent_message
  permission_field='"permission":"allow",'
fi
if ! bash "$(cd -P -- "$(dirname -- "$0")/.." && pwd -P)/check-staged-secrets.sh" >/dev/null 2>&1; then
  printf '{%s"%s":"Staged-secret check needs attention. Run gitleaks git --staged --redact and do not commit until it passes. This host check is advisory; Git-hook enforcement requires per-checkout installation."}\n' "$permission_field" "$message_field"
fi
