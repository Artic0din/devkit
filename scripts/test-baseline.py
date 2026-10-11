"""Execute the baseline workflow's actual shell step in consumer fixtures."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        workflow = (ROOT / ".github/workflows/baseline.yml").read_text()
        # This workflow has one shell step, at the end; fail if extraction becomes ambiguous.
        self.assertEqual(workflow.count("        run: |\n"), 1)
        self.script = textwrap.dedent(workflow.partition("        run: |\n")[2])

    def run_step(self, **values: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PATH"] = f'{Path(sys.executable).parent}{os.pathsep}{os.environ["PATH"]}'
        environment.update(values)
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c", self.script], cwd=self.root,
            env=environment, capture_output=True, text=True, timeout=15, check=False,
        )

    def test_rejects_empty_and_whitespace_lists(self) -> None:
        for value in ("", " , , \n", " \t"):
            with self.subTest(value=value):
                result = self.run_step(REQUIRED_FILES=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("required-files must include at least one path", result.stderr)
        (self.root / "README.md").write_text("fixture\n")
        result = self.run_step(REQUIRED_FILES="README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 1 required paths", result.stdout)

    def test_accepts_literal_paths_and_ignores_empty_entries(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs/with spaces.md").write_text("fixture\n")
        (self.root / "$(touch injected)").write_text("literal filename\n")
        (self.root / "linked").symlink_to("docs/with spaces.md")
        result = self.run_step(
            REQUIRED_FILES=" docs, docs/with spaces.md, , $(touch injected), linked, \n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 4 required paths", result.stdout)
        self.assertFalse((self.root / "injected").exists())

    def test_reports_all_missing_paths_and_rejects_dangling_links(self) -> None:
        (self.root / "README.md").write_text("fixture\n")
        (self.root / "dangling").symlink_to("absent-target")
        result = self.run_step(REQUIRED_FILES="README.md, missing, dangling")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Required paths do not exist", result.stderr)
        self.assertIn("missing", result.stderr)
        self.assertIn("dangling", result.stderr)

    def test_cannot_import_caller_modules(self) -> None:
        (self.root / "pathlib.py").write_text(
            "open('imported-caller-code', 'w').write('executed')\n"
            "class Path:\n"
            "    def __init__(self, path): pass\n"
            "    def exists(self): return True\n"
        )
        result = self.run_step(REQUIRED_FILES="missing", PYTHONPATH=str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "imported-caller-code").exists())
        self.assertIn("missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
