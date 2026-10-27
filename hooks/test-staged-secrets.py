import hashlib
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
    print("PASS: staged versus working content, safe names, no disclosure, missing scanner, Git hook")


if __name__ == "__main__":
    main()
