#!/usr/bin/env python3
"""Exercise the documented activation with disposable source and target paths."""

from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


root = Path(__file__).resolve().parent.parent
documentation = (root / "docs/curated-pstack.md").read_text()
command = re.search(r"```sh\n(.*?)\n```", documentation, re.S).group(1)
names = ("unslop", "create-verification-skill", "maintain-verification-skill")

with TemporaryDirectory() as temporary:
    fixture = Path(temporary).resolve()
    for name in names:
        source = fixture / "skills" / name
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("synthetic skill")
    # Substitute only the destination prefix; never modify the real home directory.
    command = command.replace("$HOME/.cursor/skills", str(fixture / "targets"))

    def run():
        return subprocess.run(["sh", "-c", command], cwd=fixture, capture_output=True, text=True)

    assert run().returncode == 0
    assert run().returncode == 0
    assert all((fixture / "targets" / name).resolve() == fixture / "skills" / name for name in names)
    assert all(list((fixture / "skills" / name).iterdir()) == [fixture / "skills" / name / "SKILL.md"] for name in names)
    target = fixture / "targets" / names[0]
    target.unlink()
    target.mkdir()
    assert run().returncode != 0 and not list(target.iterdir())
    target.rmdir()
    target.symlink_to(fixture / "missing", target_is_directory=True)
    assert run().returncode != 0 and target.is_symlink()

print("Cursor activation fresh, repeated, conflicting-directory, and dangling-link checks passed.")
