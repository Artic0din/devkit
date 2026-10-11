---
summary: 'Repository baseline workflow contract, provenance, adoption, and rollback.'
read_when:
  - Adopting or maintaining DevKit reusable workflows.
---
# Reusable workflows

The [repository baseline](../.github/workflows/baseline.yml) is the first workflow consolidated under [#33](https://github.com/Artic0din/devkit/issues/33).
It was originally copied unchanged from [reusable-workflows at `0f54a568155a3eea0f56e8f669a712dacfd91e4e`](https://github.com/Artic0din/reusable-workflows/blob/0f54a568155a3eea0f56e8f669a712dacfd91e4e/.github/workflows/baseline.yml); DevKit now rejects paths outside the caller checkout.
Its behavioral fixtures are adapted from that revision's `tests/test_workflows.py`; the original MIT notices are retained in [LICENSE](../LICENSE).
DevKit maintains this copy and runs its own [caller](../.github/workflows/checks.yml) against the same commit.
Other workflows and existing external callers remain in the old repository until each migration is verified; do not archive it yet.

## Baseline contract

| Interface | Behavior |
| --- | --- |
| `required-files` | Optional string of comma-separated repository-relative paths; default: `README.md, LICENSE, .gitignore, AGENTS.md` |
| Validation | Trim whitespace and ignore empty entries; reject an empty list or report all invalid, missing, and unresolvable paths together |
| Paths | Relative paths must resolve within the checkout; reject absolute paths, traversal escapes, and outside symlink targets; internal directories and symlinks count as present; dangling symlinks fail; names containing commas cannot be represented |
| Permissions and secrets | `contents: read`; no secrets; caller checkout credentials are not persisted |
| Execution | Ubuntu 24.04, five-minute timeout; isolated Python prevents imports from caller files or `PYTHONPATH` |
| Check identity | Job `baseline`, named `Repository baseline`; keep the caller job ID to preserve the existing composed check name |

This checks path presence, not file contents, agent behavior, builds, or platform-specific requirements.
DevKit overrides the list with `README.md, .gitignore, AGENTS.MD` to preserve its existing contract.
Caller-specific tests and macOS jobs remain local.

## Adoption and rollback

Action required when adopting or updating: replace absolute paths with repository-relative paths and keep required artifacts and symlink targets inside the checkout.
This deliberately tightens the original presence-only validation; external paths could previously make a missing repository artifact appear valid.
Paths remain case-sensitive on Linux.

1. Wait for the DevKit path-confinement fix to merge and record its reviewed full commit SHA.
   Replace only the existing baseline job's `uses` value with `Artic0din/devkit/.github/workflows/baseline.yml@` followed by that SHA.
   Keep caller triggers, job ID, permissions, and `required-files` unchanged.
2. Confirm the caller can access DevKit through its GitHub Actions policy, including private-repository callers.
   No token or inherited secrets are needed for this public workflow; allow the workflow and its checkout action if policies restrict allowed actions.
3. Run the caller's real pull-request checks and compare its required-check names before merging the caller update.
   Record the prior repository/ref alongside the new SHA in the caller PR; review subsequent workflow updates before changing its pin.
4. Roll back by restoring that caller's exact previous `uses` reference and rerunning its checks.
   Revert DevKit's local caller to its previous reference if the DevKit migration itself must be rolled back.

`python3 scripts/test-baseline.py` executes the workflow's actual shell step in temporary caller fixtures.
It covers empty lists, literal and normalized relative paths, missing paths, internal and dangling links, absolute paths, traversal and symlink escapes, sibling-directory prefixes, and caller-module isolation without new dependencies.
