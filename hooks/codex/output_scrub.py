"""Return bounded, redacted feedback using the Codex PostToolUse contract."""

import json
import re
import sys


PREVIEW_CHARACTERS = 6000
PATTERNS = (
    # A token boundary prevents rescanning overlapping eyJ prefixes without dots.
    (r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", "JWT"),
    (r"(?:sk[-_]|pk[-_]|ptr_|psk_)[A-Za-z0-9_-]{20,}", "KEY"),
    (r"(?:gh[psour]_|github_pat_)[A-Za-z0-9_]{30,}", "GH_TOKEN"),
    (r"AKIA[0-9A-Z]{16}", "AWS_KEY"),
    (r"[a-fA-F0-9]{32,}", "HEX"),
)


def scrub(text: str) -> str:
    for pattern, label in PATTERNS:
        text = re.sub(pattern, f"[REDACTED_{label}]", text)
    return text


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        response = payload["tool_response"]
        stdout, stderr = response["stdout"], response["stderr"]
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            raise ValueError("Bash output fields must be strings")
        clean_stdout, clean_stderr = scrub(stdout), scrub(stderr)
        if (clean_stdout, clean_stderr) != (stdout, stderr):
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
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        print("Tool output withheld: output filter could not process the result.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
