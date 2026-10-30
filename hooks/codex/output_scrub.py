from __future__ import annotations

import base64
import json
import re
import sys


PREVIEW_CHARACTERS = 6000
TERMINAL_CONTROL_PATTERN = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[\]PX^_][^\x07\x1b\n]*(?:\x07|\x1b\\)?|[ -/]*[0-~])|[\x00-\x08\x0b-\x1f\x7f]"
)
JWT_CANDIDATE_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])(?=(([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+))")
PATTERNS = (
    (r"(?<![A-Za-z0-9_-])(?:sk[-_]|pk[-_]|ptr_|psk_)[A-Za-z0-9_-]{20,}", "KEY"),
    (r"(?:gh[psour]_|github_pat_)[A-Za-z0-9_]{30,}", "GH_TOKEN"),
    (r"(?:AKIA|ASIA)[0-9A-Z]{16}", "AWS_KEY"),
)
SECRET_NAME_PATTERN = re.compile(r"secret|token|passw(?:or)?d|credential|api[_-]?key|private[_-]?key", re.IGNORECASE)
FIELD_PATTERN = re.compile(r"""(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+)["']?\s*([:=])(?!=)[ \t]*""")
STANDALONE_FIELD_PREFIX = re.compile(r"""[ \t]*(?:-[ \t]+)?["']?""")
INLINE_COLON_VALUE = re.compile(r"[^\n,}\]]+")
FLOW_VALUE_END = re.compile(r"[,}\]]")
QUOTED_VALUE_SEGMENT = r""""(?:[^"\\]|\\.)*"|"(?:[^"\\\n]|\\.)+|'(?:[^'\\]|\\.)*'|'(?:[^'\\\n]|\\.)+"""
BARE_VALUE_SEGMENT = r"""[^\s"']+"""
VALUE_PATTERN = re.compile(
    rf"""(?:{QUOTED_VALUE_SEGMENT}|{BARE_VALUE_SEGMENT})(?:(?<![,;:}}\]])(?:{QUOTED_VALUE_SEGMENT})|(?![,;:}}\]]){BARE_VALUE_SEGMENT})*""", re.DOTALL
)
FLOW_CLOSERS = {"[": "]", "{": "}"}
CLOSED_QUOTED_SCALAR = re.compile(r""""(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'""", re.DOTALL)
FLOW_COLLECTION_TAIL = re.compile(r"[ \t]*(?:[,}\]#\r\n]|\Z)")
SIBLING_FIELD = re.compile(r"""(?:-[ \t]+)?["']?[A-Za-z0-9_-]+["']?[ \t]*(?:=|:(?:[ \t\r\n]|\Z))""")
SEQUENCE_ITEM = re.compile(r"-(?=[ \t\r\n]|\Z)")
CALL_VALUE_EXEMPTION =re.compile(r"[A-Za-z_][\w.]*\((?:[A-Za-z_][\w.]*)?\)(?![^\s;,)\]}])")
PRIVATE_KEY_LABEL = r"[A-Z0-9 ]{0,40}PRIVATE KEY[A-Z ]{0,20}"
PRIVATE_KEY_PATTERN = re.compile(
    rf"-----BEGIN {PRIVATE_KEY_LABEL}-----.*?(?:-----END {PRIVATE_KEY_LABEL}-----|\Z)",
    re.DOTALL,
)


def _line_indent(text: str, line_start: int, limit: int) -> int:
    indent = 0
    while line_start + indent < limit and text[line_start + indent] in " \t":
        indent += 1
    return indent


def _advance_newline(text: str, pos: int) -> int:
    if pos < len(text) and text[pos] == "\r":
        pos += 1
    if pos < len(text) and text[pos] == "\n":
        pos += 1
    return pos


def _skip_yaml_ignorable_after_colon(text: str, pos: int) -> int:
    # YAML allows blank lines and comments between `key:` and a plain value start.
    n = len(text)
    while pos < n:
        if text[pos] in " \t":
            pos += 1
            continue
        if text[pos] == "#":
            while pos < n and text[pos] not in "\r\n":
                pos += 1
            continue
        if text[pos] in "\r\n":
            pos = _advance_newline(text, pos)
            while pos < n:
                line_start = pos
                indent = _line_indent(text, line_start, n)
                cursor = line_start + indent
                if cursor >= n:
                    return line_start
                if text[cursor] == "#":
                    pos = cursor
                    while pos < n and text[pos] not in "\r\n":
                        pos += 1
                    pos = _advance_newline(text, pos)
                    continue
                if text[cursor] in "\r\n":
                    pos = _advance_newline(text, cursor)
                    continue
                return line_start
            return pos
        return pos
    return pos


def _indented_yaml_continuation_end(text: str, value_line_start: int, line_indent: int, empty_key: bool) -> int | None:
    # Bare `key:` with a more-indented following line is a plain YAML value; lexical
    # VALUE_PATTERN cannot see past ignorable whitespace/comments, so bound by dedent.
    if value_line_start >= len(text):
        return None
    first_indent = _line_indent(text, value_line_start, len(text))
    content = value_line_start + first_indent
    if content >= len(text) or text[content] in "\r\n#":
        return None
    # YAML lets an empty key own a block sequence written at the key's own indentation.
    sequence = empty_key and first_indent == line_indent and SEQUENCE_ITEM.match(text, content)
    if first_indent <= line_indent and not sequence:
        return None
    scan = value_line_start
    while scan < len(text):
        line_end = text.find("\n", scan)
        if line_end == -1:
            segment_end = len(text)
        else:
            segment_end = line_end
            if segment_end > scan and text[segment_end - 1] == "\r":
                segment_end -= 1
        indent = _line_indent(text, scan, segment_end)
        # A YAML comment line never ends a block, whatever its indentation.
        if scan + indent < segment_end and indent <= line_indent and text[scan + indent] != "#":
            if not (sequence and indent == line_indent and SEQUENCE_ITEM.match(text, scan + indent)):
                return scan
        if line_end == -1:
            return len(text)
        scan = line_end + 1
    return len(text)


def _flow_yaml_continuation_end(text: str, value_line_start: int) -> int | None:
    # Flow entries may wrap after `key:`; bound a plain value at the next comma or closer.
    content = value_line_start + _line_indent(text, value_line_start, len(text))
    if content >= len(text) or text[content] in "\r\n#":
        return None
    if text[content] in "|>&!{[":
        return len(text)
    for index in range(content, len(text)):
        if text[index] in ",}]":
            return index
    return len(text)


def _plain_yaml_fold_end(text: str, value_line_start: int, key_indent: int, standalone: bool, empty_key: bool) -> int | None:
    if standalone:
        return _indented_yaml_continuation_end(text, value_line_start, key_indent, empty_key)
    return _flow_yaml_continuation_end(text, value_line_start)


def _flow_collection_end(text: str, start: int) -> int:
    # Quoted scalars and YAML comments may contain brackets; an unclosed quote or collection withholds the rest.
    expected: list[str] = []
    index = start
    while index < len(text):
        char = text[index]
        if char in "\"'":
            quoted = CLOSED_QUOTED_SCALAR.match(text, index)
            if not quoted:
                return len(text)
            index = quoted.end()
            continue
        if char == "#" and (text[index - 1].isspace() or text[index - 1] in ",[]{}"):
            line_end = text.find("\n", index)
            index = len(text) if line_end == -1 else line_end
            continue
        if char in FLOW_CLOSERS:
            expected.append(FLOW_CLOSERS[char])
        elif char == expected[-1]:
            expected.pop()
            if not expected:
                return index + 1
        index += 1
    return len(text)


def _next_line_value_end(text: str, start: int) -> int | None:
    # A field with nothing after its separator hides the next token, even on a later line, unless that token starts a sibling field.
    while start < len(text) and text[start].isspace():
        start += 1
    value = None if SIBLING_FIELD.match(text, start) else VALUE_PATTERN.match(text, start)
    if not value:
        return None
    if text[start] in FLOW_CLOSERS:
        return max(value.end(), _flow_collection_end(text, start))
    return value.end()


def redact_assignments(text: str) -> str:
    parts: list[str] = []
    end = 0
    # Fields arrive in text order, so line bounds and the last run of blank or comment
    # lines carry forward; rescanning them per field is quadratic on long output.
    line_start = 0
    scanned_to = 0
    line_end = text.find("\n")
    ignorable_run = (0, 0)
    prefix_checked_line = -1
    for field in FIELD_PATTERN.finditer(text):
        if field.start() < end or not SECRET_NAME_PATTERN.search(field.group(1)) or CALL_VALUE_EXEMPTION.match(text, field.end()):
            continue
        previous_newline = text.rfind("\n", scanned_to, field.start())
        if previous_newline != -1:
            line_start = previous_newline + 1
        scanned_to = field.start()
        if line_end != -1 and line_end < field.end():
            line_end = text.find("\n", field.end())
        # Only the first field on a line can stand alone; later ones have a field name before them.
        standalone = None
        if line_start != prefix_checked_line:
            prefix_checked_line = line_start
            standalone = STANDALONE_FIELD_PREFIX.fullmatch(text, line_start, field.start())
        sep = field.group(2)
        # A YAML `#` after `:` starts a comment, not a scalar value.
        value = VALUE_PATTERN.match(text, field.end())
        if value and sep == ":" and text[field.end()] == "#":
            value = None
        # Anchors, tags, and block scalars have uncertain bounds in flow and block form.
        if sep == ":" and field.end() < len(text) and text[field.end()] in "|>&!":
            parts.extend((text[end:field.end()], "[REDACTED_VALUE]"))
            end = len(text)
            continue
        redact_end: int | None = None
        fold_probe: int | None = None
        if value:
            redact_end = value.end()
            if standalone:
                redact_end = max(redact_end, len(text) if line_end == -1 else line_end)
            elif sep == ":" and text[field.end()] not in "\"'":
                inline_value = INLINE_COLON_VALUE.match(text, field.end())
                if inline_value:
                    redact_end = max(redact_end, inline_value.end())
            if text[field.end()] in FLOW_CLOSERS:
                collection_end = _flow_collection_end(text, field.end())
                redact_end = max(redact_end, collection_end)
                # Plain text glued to the closer leaves the flow value's bound uncertain.
                if sep == ":" and not standalone and not FLOW_COLLECTION_TAIL.match(text, collection_end):
                    redact_end = len(text)
            # Same-line unquoted values only fold onto following lines; never re-bound
            # same-line flow punctuation already handled by INLINE_COLON_VALUE.
            if sep == ":" and text[field.end()] not in "\"'":
                # A flow plain scalar ends at `,` `]` or `}`, and a collection at its closer; then it cannot fold.
                closed = not standalone and (text[field.end()] in FLOW_CLOSERS or FLOW_VALUE_END.search(text, field.end(), line_end))
                if line_end != -1 and not closed:
                    fold_probe = line_end
        elif sep == ":":
            fold_probe = field.end()
        value_line_start = None
        if fold_probe is not None:
            # A probe inside the remembered run lands at its end; that can only hide more.
            if not ignorable_run[0] <= fold_probe < ignorable_run[1]:
                ignorable_run = (fold_probe, _skip_yaml_ignorable_after_colon(text, fold_probe))
            value_line_start = ignorable_run[1]
        if not value:
            redact_end = _next_line_value_end(text, field.end() if value_line_start is None else value_line_start)
        if value_line_start is not None:
            # A key after `- ` is indented to the column after the dash; an opening quote is part of the key.
            key_indent = field.start() - line_start
            if key_indent and text[field.start() - 1] in "\"'":
                key_indent -= 1
            fold_end = _plain_yaml_fold_end(text, value_line_start, key_indent, bool(standalone), not value)
            if fold_end is not None:
                redact_end = fold_end if redact_end is None else max(redact_end, fold_end)
        if redact_end is None:
            continue
        # Keep a newline so following sibling keys stay on their own line in feedback.
        suffix = ""
        if (
            sep == ":"
            and redact_end < len(text)
            and text[redact_end] not in "\r\n"
            and "\n" in text[field.end() : redact_end]
        ):
            suffix = "\n"
        parts.extend((text[end:field.end()], "[REDACTED_VALUE]" + suffix))
        end = redact_end
    return "".join(parts) + text[end:]


def is_jwt_header(header: str) -> bool:
    # JSON whitespace changes the encoded prefix; recognize the decoded JOSE header.
    try:
        decoded = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(decoded, dict) and isinstance(decoded.get("alg"), str)


def scrub(text: str) -> str:
    text = redact_assignments(PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text))
    parts: list[str] = []
    end = 0
    for candidate in JWT_CANDIDATE_PATTERN.finditer(text):
        if candidate.start() >= end and is_jwt_header(candidate.group(2)):
            parts.extend((text[end:candidate.start()], "[REDACTED_JWT]"))
            end = candidate.start() + len(candidate.group(1))
    text = "".join(parts) + text[end:]
    for pattern, label in PATTERNS:
        text = re.sub(pattern, f"[REDACTED_{label}]", text)
    return text


def redact(text: str) -> tuple[str, bool]:
    # Colour codes can split a credential, and removing them can hide one the model still sees; scan both forms.
    raw_clean = scrub(text)
    displayed = TERMINAL_CONTROL_PATTERN.sub("", text)
    if displayed == text:
        return raw_clean, raw_clean != text
    clean = scrub(displayed)
    if raw_clean != text and TERMINAL_CONTROL_PATTERN.sub("", raw_clean) != clean:
        clean = "[REDACTED_OUTPUT]"
    return clean, raw_clean != text or clean != displayed


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        response = payload["tool_response"]
        # Newer Codex releases send Bash output as one combined string.
        stdout, stderr = (response, "") if isinstance(response, str) else (response["stdout"], response["stderr"])
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            raise ValueError("Bash output fields must be strings")
        (clean_stdout, stdout_changed), (clean_stderr, stderr_changed) = redact(stdout), redact(stderr)
        if stdout_changed or stderr_changed:
            reason = (
                "Original tool output withheld because it contains secret-shaped text. "
                "The command already ran; do not repeat it merely because its output was blocked. "
                f"Redacted stdout (first {PREVIEW_CHARACTERS} characters):\n"
                + clean_stdout[:PREVIEW_CHARACTERS]
                + f"\nRedacted stderr (first {PREVIEW_CHARACTERS} characters):\n"
                + clean_stderr[:PREVIEW_CHARACTERS]
            )
            print(json.dumps({"decision": "block", "reason": reason}))
        return 0
    except (AttributeError, KeyError, TypeError, ValueError, OSError, RecursionError):
        print("Tool output withheld: output filter could not process the result.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
