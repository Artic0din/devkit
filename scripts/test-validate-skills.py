"""Run scripts/validate-skills against synthetic skill folders."""

from pathlib import Path
import subprocess
import tempfile
import unittest


VALIDATOR = Path(__file__).resolve().parent / "validate-skills"


class ValidateSkillsTests(unittest.TestCase):
    def validate(self, body: str) -> subprocess.CompletedProcess[str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        skill = root / "skills" / "sample"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: sample\ndescription: Sample skill.\n---\n\n{body}\n")
        return subprocess.run([str(VALIDATOR)], cwd=root, capture_output=True, text=True, timeout=30, check=False)

    def test_rejects_attribution_instructions(self) -> None:
        for line in (
            "> 🤖 **<model> responding on behalf of <user>**",
            "End the description with `Created with <model> in <harness>.`",
            "Finish with 🤖 Generated with [Claude Code](https://claude.com/claude-code)",
        ):
            with self.subTest(line=line):
                result = self.validate(line)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("skills must not instruct agent attribution", result.stderr)

    def test_accepts_lines_that_ban_attribution(self) -> None:
        for line in (
            "Post comments without any agent, model or harness attribution.",
            "Never add `Created with <model>` lines or 'responding on behalf of' notes.",
            "Upstream asks for a responding on behalf of note; the vendored copy drops it.",
        ):
            with self.subTest(line=line):
                result = self.validate(line)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
