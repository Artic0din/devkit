"""Check recovery gates through their public entry point."""
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

CLI = str(Path(__file__).with_name("provider-cleanup-check"))


class Gates(unittest.TestCase):
    def call(self, *args: str) -> int:
        return subprocess.run([CLI, *args], capture_output=True).returncode

    def test_recovery_choice_and_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "backup.tar"
            for name in ["plugins.json", "skill.md"]:
                (root / name).write_text("synthetic " + name)
            (root / "plugins.json").chmod(0o644)
            (root / "skill.md").chmod(0o644)
            args = ["preflight", "--archive", str(archive), "--root", temp,
                    "--registration", "plugins.json", "--payload", "skill.md"]
            with tarfile.open(archive, "w") as tar:
                tar.add(root / "skill.md", arcname="skill.md")
            self.assertNotEqual(self.call(*args), 0)
            with tarfile.open(archive, "a") as tar:
                tar.add(root / "plugins.json", arcname="plugins.json")
            self.assertEqual(self.call(*args), 0)
            (root / "plugins.json").write_text("changed")
            self.assertNotEqual(self.call(*args), 0)
            (root / "plugins.json").write_text("synthetic plugins.json")
            original = (root / "plugins.json").stat().st_mode
            (root / "plugins.json").chmod(0o600)
            self.assertNotEqual(self.call(*args), 0, "private registration permissions must survive restore")
            (root / "plugins.json").chmod(original)
            (root / "skill.md").chmod(0o755)
            self.assertNotEqual(self.call(*args), 0, "executable bits must survive restore")
            self.assertNotEqual(self.call("preflight"), 0)
            archive.unlink()
            self.assertEqual(self.call("preflight", "--no-backup"), 0)
            self.assertFalse(archive.exists())

    def test_equivalent_paths_and_nested_payload_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "snapshot.tar"
            (root / "registration").write_text("synthetic")
            payload = root / "skills"
            nested = payload / "nested"
            nested.mkdir(parents=True)
            (nested / "instructions").write_text("synthetic skill")
            args = ["preflight", "--archive", str(archive), "--root", temp,
                    "--registration", "registration", "--payload"]
            with tarfile.open(archive, "w") as tar:
                tar.add(root / "registration", arcname="registration")
                tar.add(payload, arcname="skills")
            self.assertEqual(self.call(*args, "skills"), 0)
            self.assertNotEqual(self.call(*args, "./registration"), 0)
            original_mode = nested.stat().st_mode
            nested.chmod(0o700 if nested.stat().st_mode & 0o077 else 0o755)
            self.assertNotEqual(self.call(*args, "skills"), 0)
            nested.chmod(original_mode)
            (nested / "extra").write_text("missing from backup")
            self.assertNotEqual(self.call(*args, "skills"), 0)

    def test_leaf_requires_restorable_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = root / "config"
            parent.mkdir()
            (parent / "registration").write_text("synthetic")
            (root / "skill").write_text("skill")
            archive = root / "backup.tar"
            with tarfile.open(archive, "w") as tar:
                tar.add(parent / "registration", arcname="config/registration")
                tar.add(root / "skill", arcname="skill")
            args = ["preflight", "--root", temp, "--archive", str(archive),
                    "--registration", "config/registration", "--payload", "skill"]
            self.assertNotEqual(self.call(*args), 0)
            with tarfile.open(archive, "a") as tar:
                tar.add(parent, arcname="config", recursive=False)
            self.assertEqual(self.call(*args), 0)
            self.assertNotEqual(self.call(*args[:-1], "config"), 0,
                                "a directory holding only the registration is not a payload")

    def test_pilot_gates_the_next_host(self) -> None:
        for exit_code, rows, expected in [(1, ["sample"], False), (0, [], False),
                                          (0, [{"name": "sample", "enabled": False}], False),
                                          (0, [{"name": "sample", "errors": ["load error"]}], False),
                                          (0, [{"name": "sample"}], True)]:
            with self.subTest(exit_code=exit_code, rows=rows):
                start = json.dumps([sys.executable, "-c", f"raise SystemExit({exit_code})"])
                catalog = json.dumps([sys.executable, "-c", f"print({json.dumps(rows)!r})"])
                self.assertEqual(self.call("pilot", "--startup", start, "--catalog", catalog,
                                           "--expect", "sample") == 0, expected)


if __name__ == "__main__":
    unittest.main()
