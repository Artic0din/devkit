# Create a note

Create note lets a user save a titled note from the browser or CLI, cancel an unfinished draft, and confirm the saved note from a second user-facing view.

## Sub-features

- `create-open` opens a blank editor from each browser entry point.
- `create-save` persists a title and body.
- `create-cancel` discards an unfinished browser draft.
- `create-cli` creates the same note shape from the terminal.

## How to get to it (user POV)

- Choose the `New note` button in the browser toolbar.
- Press `n` in the browser while focus is outside an editable field.
- Run `notes create --title <title> --body <body>` in a terminal.

## Driving it with control-notes

Preconditions:

- Notes is healthy at `http://127.0.0.1:4173`.
- No note is titled `Release checklist`.
- `control-notes doctor` reports the expected URL and disposable data directory.

- **Open editor (`create-open/toolbar`).** Choose `New note`.
  Run `control-notes browser click --role button --name "New note"`.
  A form named `Note editor` appears with focus in the `Title` textbox.
- **Enter content (`create-save/toolbar`).** Type the title and body.
  Run `control-notes browser fill --role textbox --name "Title" --value "Release checklist"` and `control-notes browser fill --role textbox --name "Body" --value "Tag and publish"`.
  The `Save note` button becomes enabled.
- **Save note (`create-save/toolbar`).** Choose `Save note`.
  Run `control-notes browser click --role button --name "Save note"`.
  A status named `Note saved` appears and the heading reads `Release checklist`.
- **Confirm persistence (`create-save/toolbar`).** Return to the note list and reopen the note.
  Run `control-notes browser click --role link --name "All notes"` and `control-notes browser click --role link --name "Release checklist"`.
  The editor shows both saved values.
- **Cancel draft (`create-cancel/toolbar`).** Open a new note, enter `Discard me`, and choose `Cancel`.
  Run `control-notes browser click --role button --name "New note"`, `control-notes browser fill --role textbox --name "Title" --value "Discard me"`, `control-notes browser click --role button --name "Cancel"`, and `control-notes browser reload`.
  After the reload, the note list has no `Discard me` link, so the draft was not stored.
- **Keyboard entry (`create-open/keyboard`).** From the note list, focus the non-editable `All notes` heading, then press `n`.
  Run `control-notes browser focus --role heading --name "All notes"` and `control-notes browser press --key n`.
  The blank `Note editor` form appears with focus in `Title`; run `control-notes browser click --role button --name "Cancel"` to return to the list without saving.
- **CLI entry (`create-cli/cli`).** Create a second note.
  Run `control-notes cli -- notes create --title "CLI note" --body "Created from terminal" --format json`.
  Exit code `0` and stdout contain the new note ID and title.
- **Confirm CLI persistence (`create-cli/cli`).** Refresh the browser list and open the CLI-created note.
  Run `control-notes browser reload` and `control-notes browser click --role link --name "CLI note"`.
  The editor shows title `CLI note` and body `Created from terminal`; assert both stored values.
- **Proof (`proof`).** Return to the note list with `control-notes browser click --role link --name "All notes"`.
  Run `control-notes browser snapshot --aria --path "$NOTES_EVIDENCE_DIR/create-note/list.aria.txt"` and `control-notes browser screenshot --path "$NOTES_EVIDENCE_DIR/create-note/list.png"`.
  The artifacts show `Release checklist` and `CLI note`, and no `Discard me`.

## Gotchas

- Pressing `n` while a textbox has focus types the character instead of opening a new editor.
- Titles are trimmed on save.
  Assert the rendered title, not the draft input value.
- A save status alone is insufficient proof.
  Reopen the note from the list.
- Remove `Release checklist` and `CLI note` during fixture cleanup, but retain their proof artifacts.
