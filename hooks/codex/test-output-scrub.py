"""Run directly with Python to check the Codex post-tool output contract."""

import json
import base64
import os
from pathlib import Path
import subprocess
import tempfile


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
    assert run_hook("version abc.def.ghi") == ""
    assert run_hook("task-abcdefghijklmnopqrstuvwxyz") == ""
    assert run_hook("eyJ" * 100000) == ""
    header = base64.urlsafe_b64encode(b'{\n "alg":"HS256","typ":"JWT"}').decode().rstrip('=')
    token = header + '.e30.' + 'Z' * 43
    assert token not in run_hook(token)
    assert json.loads(run_hook(token))["decision"] == "block"
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "json.py").write_text("import sys\nprint(sys.stdin.read())\nraise SystemExit(0)\n")
        token = "sk-" + "Z" * 40
        result = subprocess.run(
            ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
            input=json.dumps({"tool_response": {"stdout": token, "stderr": ""}}),
            env={**os.environ, "PYTHONPATH": directory}, text=True,
            capture_output=True, check=True, timeout=3,
        )
        assert token not in result.stdout
        assert json.loads(result.stdout)["decision"] == "block"
    for prefix in ("sk-", "pk-"):
        token = prefix + "A" * 40
        output = run_hook(token)
        assert json.loads(output)["decision"] == "block"
        assert token not in output
    output = run_hook("x" * 1000000 + "ghp_" + "A" * 36)
    assert json.loads(output)["decision"] == "block"
    for channel in ("stdout", "stderr"):
        token = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=") + ".e30." + "Z" * 43
        output = run_hook(**{channel: "prefix." + token, **({"stdout": ""} if channel == "stderr" else {})})
        assert json.loads(output)["decision"] == "block"
        assert token not in output
        for credential in ("ASIA" + "Z" * 16, "eyJhbGciOiJIUzI1NiJ9.e30." + "Z" * 43):
            output = run_hook(**{channel: credential, **({"stdout": ""} if channel == "stderr" else {})})
            assert json.loads(output)["decision"] == "block"
            assert credential not in output
        for prefix in ("ghp_", "ghs_", "gho_", "ghu_", "ghr_", "github_pat_"):
            fake_token = prefix + "Z" * 36
            output = run_hook(**{channel: fake_token, **({"stdout": ""} if channel == "stderr" else {})})
            result = json.loads(output)
            assert result["decision"] == "block", result
            assert set(result) == {"decision", "reason"}, result
            assert fake_token not in output
            assert "[REDACTED_GH_TOKEN]" in result["reason"]
        for hexadecimal in ("a" * 40, "ABCDEF1234" * 4, "AbCdEf1234" * 4):
            output = run_hook(**{channel: hexadecimal, **({"stdout": ""} if channel == "stderr" else {})})
            assert hexadecimal not in output
            assert "[REDACTED_HEX]" in json.loads(output)["reason"]
    print("PASS: ordinary output, stdout/stderr redaction, Codex block contract")
