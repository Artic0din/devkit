"""Run directly with Python to check the Codex post-tool output contract."""

import json
from pathlib import Path
import subprocess


def run_hook(stdout: str, stderr: str = "") -> str:
    payload = {"tool_response": {"stdout": stdout, "stderr": stderr}}
    result = subprocess.run(
        ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
        input=json.dumps(payload), text=True, capture_output=True, check=True,
        timeout=3,
    )
    assert result.stderr == "", result.stderr
    return result.stdout


if __name__ == "__main__":
    for response in ({}, {"stdout": ""}, {"stderr": ""}):
        result = subprocess.run(
            ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
            input=json.dumps({"tool_response": response}), text=True,
            capture_output=True, timeout=3,
        )
        assert result.returncode == 2 and result.stdout == "", result
    assert run_hook("ordinary output") == ""
    assert run_hook("eyJ" * 100000) == ""
    for prefix in ("sk-", "pk-"):
        token = prefix + "A" * 40
        output = run_hook(token)
        assert json.loads(output)["decision"] == "block"
        assert token not in output
    output = run_hook("x" * 1000000 + "ghp_" + "A" * 36)
    assert json.loads(output)["decision"] == "block"
    for channel in ("stdout", "stderr"):
        fake_token = "ghp_" + "A" * 36
        output = run_hook(**{channel: fake_token, **({"stdout": ""} if channel == "stderr" else {})})
        result = json.loads(output)
        assert result["decision"] == "block", result
        assert set(result) == {"decision", "reason"}, result
        assert fake_token not in output
        assert "[REDACTED_GH_TOKEN]" in result["reason"]
    assert "[REDACTED_HEX]" in json.loads(run_hook("a" * 40))["reason"]
    print("PASS: ordinary output, stdout/stderr redaction, Codex block contract")
