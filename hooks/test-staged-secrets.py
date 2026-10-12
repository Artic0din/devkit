import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main() -> None:
    assert shutil.which("gitleaks"), "Install gitleaks to run these checks"
    hooks = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="staged-secrets-") as temporary:
        root = Path(temporary)
        repository = root / "repository with spaces"
        repository.mkdir()
        nested = repository / "src"
        nested.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        document = repository / "notes with spaces.md"
        for host in ("claude", "codex"):
            command = [str(hooks / "check-staged-secrets.sh")]
            document.write_text("Document powerwall, teslemetry and API_KEY names.\n")
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            result = subprocess.run(command, cwd=repository, capture_output=True)
            assert result.returncode == 0, result.stderr
            assert result.stdout == result.stderr == b""
            secret = "ghp_" + hashlib.sha256(b"synthetic hook test credential").hexdigest()[:36]
            document.write_text(secret + "\n")
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            document.write_text("The working copy no longer contains the staged value.\n")
            result = subprocess.run(command, cwd=repository, capture_output=True)
            assert result.returncode == 2, result
            assert secret.encode() not in result.stdout + result.stderr
            assert b"Staged-secret check failed" in result.stderr
            linked_hooks = root / f"{host}-hooks"
            linked_hooks.symlink_to(hooks / host, target_is_directory=True)
            linked_command = ["/bin/bash", str(linked_hooks / "pre-commit-secrets.sh")]
            linked_result = subprocess.run(linked_command, cwd=repository, capture_output=True)
            assert linked_result.returncode == 0, linked_result
            assert "Staged-secret" in json.loads(linked_result.stdout)["systemMessage"]
            assert secret.encode() not in linked_result.stdout + linked_result.stderr
            if host == "claude":
                copilot = subprocess.run(linked_command + ["--copilot"], cwd=repository, capture_output=True)
                assert copilot.returncode == 0, copilot
                assert set(json.loads(copilot.stdout)) == {"additionalContext"}
                assert "Staged-secret" in json.loads(copilot.stdout)["additionalContext"]
                assert secret.encode() not in copilot.stdout + copilot.stderr
                configuration = json.loads((hooks.parent / "config/copilot.hooks.json").read_text())
                assert any(entry.get("bash", "").endswith("pre-commit-secrets.sh --copilot")
                           for entry in configuration["hooks"]["preToolUse"])
                scanner = next(entry for entry in configuration["hooks"]["preToolUse"]
                               if "pre-commit-secrets.sh" in entry.get("bash", ""))
                assert scanner.get("matcher") == "bash"
                cursor = subprocess.run(linked_command + ["--cursor"], cwd=repository, capture_output=True)
                assert cursor.returncode == 0, cursor
                assert set(json.loads(cursor.stdout)) == {"agent_message", "permission"}
                assert json.loads(cursor.stdout)["permission"] == "allow"
                assert "Staged-secret" in json.loads(cursor.stdout)["agent_message"]
                assert secret.encode() not in cursor.stdout + cursor.stderr
                configuration = json.loads((hooks.parent / "config/cursor.hooks.json").read_text())
                assert any(entry.get("command", "").endswith("pre-commit-secrets.sh --cursor")
                           for entry in configuration["hooks"]["beforeShellExecution"])
            assert subprocess.run(command, cwd=nested, capture_output=True).returncode == 2
            assert subprocess.run(command, cwd=root, capture_output=True).returncode == 0

            binaries = root / "bin"
            binaries.mkdir(exist_ok=True)
            for executable in ("git", "dirname"):
                target = binaries / executable
                if not target.exists():
                    target.symlink_to(shutil.which(executable))
            environment = {**os.environ, "PATH": str(binaries)}
            bash = binaries / "bash"
            if not bash.exists():
                bash.symlink_to("/bin/bash")
            result = subprocess.run(command, cwd=repository, env=environment, capture_output=True)
            assert result.returncode == 2, result
            assert b"install gitleaks" in result.stderr
            (binaries / "git").unlink()
            result = subprocess.run(command, cwd=repository, env=environment, capture_output=True)
            assert result.returncode == 2, result
            (binaries / "git").symlink_to(shutil.which("git"))
        damaged = root / "damaged"
        damaged.mkdir()
        (damaged / ".git").mkdir()
        assert subprocess.run(command, cwd=damaged, capture_output=True).returncode == 2
        (binaries / "git").unlink()
        (binaries / "git").write_text(
            '#!/bin/sh\necho "fatal: not a git repository (or any parent up to mount point /)" >&2\nexit 128\n'
        )
        (binaries / "git").chmod(0o755)
        assert subprocess.run(command, cwd=root, env=environment, capture_output=True).returncode == 0

        scripts = repository / "scripts"
        scripts.mkdir()
        validator = scripts / "validate-skills"
        validator.write_text("#!/bin/sh\nexit 0\n")
        validator.chmod(0o755)
        document.write_text("safe baseline\n")
        subprocess.run(["git", "add", "."], cwd=repository, check=True)
        commit = ["git", "-c", f"core.hooksPath={hooks}", "-c", "user.name=Hook Test",
                  "-c", "user.email=hook-test@example.invalid", "commit", "-qm", "test"]
        subprocess.run(commit, cwd=repository, capture_output=True, check=True)
        document.write_text(secret + "\n")
        result = subprocess.run(commit + ["-a"], cwd=repository, capture_output=True)
        assert result.returncode != 0, result
        assert b"Staged-secret check failed" in result.stderr
        assert secret.encode() not in result.stdout + result.stderr
    print("PASS: both hosts, staged versus working content, safe names, no disclosure, missing scanner")


if __name__ == "__main__":
    main()
