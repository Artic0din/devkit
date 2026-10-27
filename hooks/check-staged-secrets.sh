#!/usr/bin/env bash
set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo 'Staged-secret check unavailable: Git is required.' >&2
  exit 2
fi
if ! repository_root=$(LC_ALL=C git rev-parse --show-toplevel 2>&1); then
  if [[ "$repository_root" == 'fatal: not a git repository ('* ]]; then
    directory=$PWD
    while [[ ! -e "$directory/.git" && ! -L "$directory/.git" ]]; do
      [[ "$directory" == / ]] && exit 0
      directory=$(dirname -- "$directory")
    done
  fi
  echo 'Staged-secret check unavailable: Git could not read repository metadata.' >&2
  exit 2
fi
cd "$repository_root"
if ! command -v gitleaks >/dev/null 2>&1; then
  echo 'Staged-secret check unavailable: install gitleaks before continuing.' >&2
  exit 2
fi
if ! gitleaks git --staged --redact --no-banner >/dev/null 2>&1; then
  echo 'Staged-secret check failed. Run gitleaks git --staged --redact to inspect the redacted findings or scanner error.' >&2
  exit 2
fi
