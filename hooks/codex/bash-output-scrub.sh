#!/usr/bin/env bash
set -eu
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Tool output withheld: Python 3 is required for output filtering.' >&2
  exit 2
fi
exec python3 -I "$(dirname -- "$0")/output_scrub.py"
