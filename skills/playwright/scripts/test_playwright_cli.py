"""Check the wrapper ignores project-local CLI packages; run after runtime setup."""

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


wrapper = Path(__file__).with_name("playwright_cli.sh").resolve()
with TemporaryDirectory() as directory:
    project = Path(directory)
    package = project / "node_modules" / "@playwright" / "cli"
    package.mkdir(parents=True)
    marker = project / "selected-project-package"
    (package / "package.json").write_text(
        '{"name":"@playwright/cli","version":"0.1.21",'
        '"bin":{"playwright-cli":"playwright-cli.js"}}', encoding="utf-8",
    )
    executable = package / "playwright-cli.js"
    executable.write_text(
        '#!/usr/bin/env node\nrequire("fs").writeFileSync('
        'process.env.PROJECT_PACKAGE_MARKER, "selected");\n', encoding="utf-8",
    )
    executable.chmod(0o755)
    binaries = project / "node_modules" / ".bin"
    binaries.mkdir()
    (binaries / "playwright-cli").symlink_to(executable)
    environment = {**os.environ, "PROJECT_PACKAGE_MARKER": str(marker)}
    for arguments in (["--version"], ["--session", "synthetic", "--version"]):
        result = subprocess.run(
            [str(wrapper), *arguments], cwd=project, env=environment,
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "0.1.21", result.stdout
        assert not marker.exists(), "Project-local CLI was executed"
    environment["PLAYWRIGHT_CLI_SESSION"] = "synthetic-default"
    result = subprocess.run(
        [str(wrapper), "--version"], cwd=project, env=environment,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists(), "Project-local CLI was executed"
print("PASS: project-local CLI excluded; explicit and default session arguments work")
