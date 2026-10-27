# Notes verification map

This directory is the maintained source for verifying the user-facing behavior of Notes.
Read the index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions

- Create the disposable data directory with `NOTES_DATA_DIR="$(mktemp -d /tmp/notes-verify.XXXXXX)" || exit 1`, then `export NOTES_DATA_DIR`.
- Create a separate evidence directory with `NOTES_EVIDENCE_DIR="$(mktemp -d /tmp/notes-proof.XXXXXX)" || exit 1`, then `export NOTES_EVIDENCE_DIR`.
- Run `mkdir -p "$NOTES_EVIDENCE_DIR/create-note" "$NOTES_EVIDENCE_DIR/search"` before capture; retain this directory through data cleanup and keep it out of commits.
- Launch Notes at `http://127.0.0.1:4173` with that disposable data directory; a second run needs its own port and matching harness configuration as well as its own directories.
- Seed notes titled `Quarterly plan` and `Grocery list`.
- Put `control-notes` and the `notes` CLI on `PATH`.
- Run `control-notes doctor` and require the expected URL, data directory, and build revision.
- Never drive an instance that was not started by this verification run.

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Prefer ARIA roles and accessible names over CSS selectors or DOM position.
- Treat every command as literal.
  Keep quoted names and flags unchanged.
- Run browser actions through `control-notes browser`.
- Run terminal actions through `control-notes cli -- <command>`.
- Every driving bullet carries a `<sub-feature ID>/<entry point>` tag in its label; `Proof` uses the tag `proof`.
  Before running the bullet, run `control-notes step "<tag>"` with that tag; the harness keeps it as the current step until the next `step` call.
- `control-notes` appends every command it runs to `$NOTES_EVIDENCE_DIR/actions.log` with the current step, arguments, stdout, stderr, and exit code.
- Right after each browser bullet's observable result, and before any later command in that bullet changes it, run `control-notes browser snapshot --aria` so the log records the resulting state for that step.
- Restore seeded data after a mutation.
  Do not remove proof artifacts during cleanup.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- Per-step UI proof is the logged ARIA snapshot; the `Proof` bullet adds a screenshot with the app identity visible.
- CLI proof includes the command, stdout, stderr, and exit code.
- Mutation proof includes a read-only second view of the stored value.
- `actions.log` ties every action and its result to a sub-feature ID and entry point; each feature's `Proof` bullet adds the combined final state.
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.
- Inspect and redact evidence before authorized sharing, including visual inspection of screenshots.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior.
It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with <harness>` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result; every bullet tags its label with `<sub-feature ID>/<entry point>`, and `Proof` uses `proof`.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map.
Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [Create a note](./create-note.md) covers browser and CLI creation, cancellation, persistence, and cleanup.
- [Search notes](./search.md) covers toolbar, keyboard, and CLI search with matching, empty, and clear states.
