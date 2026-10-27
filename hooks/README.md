# Staged-secret checks

`hooks/check-staged-secrets.sh` runs one Gitleaks scan of the caller's Git index.
It requires Bash, Git and Gitleaks, writes no files and makes no network requests.

Run it from the repository being checked.
Outside a repository it does nothing; missing Git, unreadable metadata and damaged `.git` directories block the check.
It returns exit code 2 with a generic message on a finding, scanner error or missing Gitleaks, and 0 with no output on a clean scan.
It does not print staged lines, even when a secret is detected.

The repository's `hooks/pre-commit` runs the scanner after Git has staged all commit content, including `git commit -a`, before its existing skill validation.
This enforcement covers `git commit` in opted-in checkouts, not every command that can create commits.
In particular, cherry-pick does not invoke `pre-commit`, and merge can use `pre-merge-commit` instead.
Opt in as documented in the main README with `git config core.hooksPath hooks`.
The Git hook fails closed if scanning is unavailable.
It never replaces the mandatory explicit staged scan before commits and exact outgoing-commit-range scan before pushes.
Git's explicit hook bypasses remain possible; this is not a server-side enforcement boundary.

Run `python3 hooks/test-staged-secrets.py` to exercise the scanner and the Git hook against isolated Git repositories and the installed Gitleaks executable.
