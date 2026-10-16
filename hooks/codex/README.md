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
Each scan starts from the original output.
When the raw scan redacts something and its result, with control sequences removed, differs from the normalized result, feedback omits that channel.
Values assigned to fields whose names contain words such as `secret`, `token` or `password` are redacted whatever their shape.
This applies to adjacent quoted and unquoted segments, and to any value except a complete call such as `token = getToken()`.
Empty quoted segments are included, and secret-named inline YAML fields with quoted or unquoted keys redact an unquoted value through the end of its line; a quoted value ends at its closing quote.
Standalone secret-named environment assignments also redact through the line ending, including values containing spaces.
A secret-named field with nothing after its separator redacts the first token on the next non-blank line, unless that line starts another field such as `user: bob` or `USER=bob`.
The separator itself may also sit on a later line, as in pretty-printed JSON.
Unquoted flow-style YAML values redact through the next comma or closing container, including when the value starts on a following line inside a flow map or list.
A value that is itself a list or map, such as `"api_keys": ["a", "b"]`, redacts through its matching closing bracket, ignoring brackets inside quotes and YAML comments; if that bracket or a quote inside it never closes, feedback omits the rest of that channel.
Feedback also omits the rest of the channel when other text follows that bracket on its line inside a YAML map or list, as in `{password: [a]b, user: bob}`, because the value boundary is uncertain.
For secret-named YAML block scalars or values starting with an anchor or tag, including inside flow maps, feedback omits the rest of that channel because the value boundary is uncertain.
Standalone secret-named keys with an unquoted plain YAML value use one continuation bound whether that value starts on the key line or after blank lines or `#` comments, including CRLF: more-indented folded lines are redacted with the value, and following sibling keys stay visible, including the next key of a `- ` list item.
A quoted value spans lines only when its closing quote is present.
Private-key PEM blocks are redacted wherever they appear.
Unlabelled hexadecimal values and UUIDs pass through, so ordinary commit IDs and request IDs stay visible.
Hexadecimal values assigned to secret-named fields still block.
This is pattern-based filtering, not a guarantee that arbitrary secrets are detected; lines such as `password: string;` or `max_tokens: 1000` also match.
Known gaps include eight-bit C1 control sequences, calls with one identifier argument such as `Summer(Rain)`, field names written with JSON `\u` escapes, and value tails after punctuation or shell `'\''` quoting.
Avoid emitting sensitive output in the first place.
The hook runs the first `bash` and `python3` found on `PATH`.
It does not defend against a hostile `PATH`, because anything placed there already runs with your privileges.

Register the script as a command handler under `PostToolUse` with matcher `^Bash$` in the host's hook settings.
Use an absolute script path and keep it synchronous.
Remove that handler to disable it.
This change publishes source only and does not modify installed host settings.

Run `python3 hooks/codex/test-output-scrub.py` from the repository root to validate the script's JSON and stdout/stderr filtering.
The test checks the emitted contract, not an authenticated model session.
