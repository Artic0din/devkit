# Staged-secret checks

The Claude and Codex `pre-commit-secrets.sh` entrypoints provide advisory feedback from one Gitleaks scan of the caller's Git index.
They require Bash, Git and Gitleaks, write no files and make no network requests.
Keep the entire `hooks` directory together; the host entrypoints require the shared script in their parent directory.

Run them from the repository being checked, or use `hooks/check-staged-secrets.sh` directly.
Outside a repository they do nothing; missing Git, unreadable metadata and damaged `.git` directories block the check.
The shared scanner returns exit code 2 with a generic message on a finding, scanner error or missing Gitleaks.
Host entrypoints turn that result into a nonblocking system message, so diagnostics and unstaging remain possible.
The Copilot registration uses the Claude entrypoint's `--copilot` mode to emit its supported `additionalContext` field.
Its `bash` matcher avoids scanning on unrelated reads and edits.
Cursor selects `--cursor` to emit `agent_message` with advisory `permission: "allow"`.
Successful scans return 0 with no output.
They do not print staged lines, even when a secret is detected.

The existing host settings invoke the secret check for each Bash call.
This remains a check of the hook process's current repository, not a shell parser: commands that change directory or use `git -C` need an explicit scan of their target repository.
The repository's `hooks/pre-commit` runs the scanner after Git has staged all commit content, including `git commit -a`, before its existing skill validation.
This enforcement covers `git commit` in opted-in checkouts, not every command that can create commits.
In particular, cherry-pick does not invoke `pre-commit`, and merge can use `pre-merge-commit` instead.
Opt in as documented in the main README with `git config core.hooksPath hooks`.
Publishing these source files does not change host settings or opt a checkout into Git hooks.
The host warning is advisory in all checkouts, including those without this Git hook installed.
It never authorizes committing a finding: the mandatory explicit staged scan before commits and exact outgoing-commit-range scan before pushes still apply.
Git's explicit hook bypasses remain possible; this is not a server-side enforcement boundary.

The old local keyword checks treated ordinary product names as credentials and printed matching lines.
These entrypoints replace that behavior with the existing required scanner; the Git hook fails closed if scanning is unavailable.
Remove the corresponding host hook registration to disable the check.

Run `python3 hooks/test-staged-secrets.py` to exercise both entrypoints against isolated Git repositories and the installed Gitleaks executable.
