# Codex output feedback hook

`bash-output-scrub.sh` is a synchronous `PostToolUse` hook for Bash results with string `stdout` and `stderr` fields.
It needs Bash and Python 3, writes no files, and makes no network requests.
Ordinary results produce no hook output.
When its patterns match, the hook returns `decision: "block"` with redacted feedback.
Feedback includes at most 6,000 characters from each redacted channel, so large results never become command-line arguments.
Malformed results, missing Python and any other filter failure return blocking exit code 2 with a generic message.

[The Codex hook contract](https://learn.chatgpt.com/docs/hooks#posttooluse) specifies that a blocking post-tool hook replaces the model-visible result with feedback.
For nested code-mode calls, it rejects the tool promise with that feedback.
The command has already run, so this does not undo its effects or erase logs from other systems.
Output is scanned both as received and with terminal control sequences removed, so colour codes cannot split a credential; feedback shows plain text.
Values assigned to fields whose names contain words such as `secret`, `token` or `password` are redacted whatever their shape.
This applies to adjacent quoted and unquoted segments, and to any value except a complete call such as `token = getToken()`.
A quoted value spans lines only when its closing quote is present.
Private-key PEM blocks are redacted wherever they appear.
This is pattern-based filtering, not a guarantee that arbitrary secrets are detected; long hexadecimal commit IDs and lines such as `password: string;` or `max_tokens: 1000` also match.
Known gaps include YAML block scalars such as `password: |`, eight-bit C1 control sequences, calls with one identifier argument such as `Summer(Rain)`, and value tails after punctuation or shell `'\''` quoting.
Avoid emitting sensitive output in the first place.
The hook runs the first `bash` and `python3` found on `PATH`.
It does not defend against a hostile `PATH`, because anything placed there already runs with your privileges.

Register the script as a command handler under `PostToolUse` with matcher `^Bash$` in the host's hook settings.
Use an absolute script path and keep it synchronous.
Remove that handler to disable it.
This change publishes source only and does not modify installed host settings.

Run `python3 hooks/codex/test-output-scrub.py` from the repository root to validate the script's JSON and stdout/stderr filtering.
The test checks the emitted contract, not an authenticated model session.
