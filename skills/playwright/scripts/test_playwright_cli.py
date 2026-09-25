"""Check the wrapper ignores project-local CLI packages; run after runtime setup."""

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4


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
    session = "isolation-" + uuid4().hex
    environment.update(PLAYWRIGHT_CLI_SESSION=session, NO_UPDATE_NOTIFIER="1")
    configuration = project / ".playwright" / "cli.config.json"
    configuration.parent.mkdir()
    configuration.write_text(
        '{"browser":{"launchOptions":{"executablePath":'
        + json.dumps(str(executable)) + '}}}', encoding="utf-8",
    )

    def run(*arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(wrapper), *arguments], cwd=project, env=environment,
            capture_output=True, text=True, check=False, timeout=45,
        )

    override = run("--config", str(configuration), "--version")
    assert override.returncode == 1 and "overrides are disabled" in override.stderr, override
    try:
        opened = run("open", "about:blank")
        assert opened.returncode == 0, (opened.stdout, opened.stderr)
        assert not marker.exists(), "Project launch executable was selected"
        prepared = run("eval", "() => { document.body.innerHTML = '<textarea></textarea>'; document.querySelector('textarea').focus(); }")
        assert prepared.returncode == 0, (prepared.stdout, prepared.stderr)
        for value in ("--session", "--session=literal"):
            typed = run("type", "--", value)
            assert typed.returncode == 0, (typed.stdout, typed.stderr)
        actual = run("eval", "document.querySelector('textarea').value")
        assert actual.returncode == 0 and "--session--session=literal" in actual.stdout, actual
    finally:
        closed = run("close")
        assert closed.returncode == 0, (closed.stdout, closed.stderr)
print("PASS: project-local CLI/config excluded; explicit, default, and positional session arguments work")
