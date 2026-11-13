"""Check the browser profile's filesystem and child-process boundaries on macOS."""
from pathlib import Path
import subprocess
import tempfile
import unittest


PROFILE = Path(__file__).resolve().parents[1] / "config" / "obscura.sb"


@unittest.skipUnless(Path("/usr/bin/sandbox-exec").exists(), "macOS profile test")
class BrowserProfileTests(unittest.TestCase):
    def test_private_files_blocked_and_browser_files_readable(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as directory:
            root = Path(directory)
            allowed = root / "browser"
            allowed.mkdir()
            public = allowed / "fixture"
            private = root / "private"
            public.write_text("public fixture")
            private.write_text("private fixture")
            command = ["/usr/bin/sandbox-exec", "-D", f"OBSCURA_ROOT={allowed}",
                       "-D", "OBSCURA_EXEC=/bin/cat", "-f", str(PROFILE), "/bin/cat"]
            readable = subprocess.run(command + [str(public)], capture_output=True, text=True)
            self.assertEqual(readable.returncode, 0, readable.stderr)
            self.assertEqual(readable.stdout, "public fixture")
            refused = subprocess.run(command + [str(private)], capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertNotIn("private fixture", refused.stdout)
            with tempfile.TemporaryDirectory() as temporary:
                secret = Path(temporary) / "private"
                secret.write_text("temporary private fixture")
                refused = subprocess.run(command + [str(secret)], capture_output=True, text=True)
                self.assertNotEqual(refused.returncode, 0)
                self.assertNotIn("temporary private fixture", refused.stdout)
            shell = ["/usr/bin/sandbox-exec", "-D", f"OBSCURA_ROOT={allowed}",
                     "-D", "OBSCURA_EXEC=/bin/sh", "-f", str(PROFILE), "/bin/sh", "-c"]
            write = subprocess.run(shell + ['printf blocked > "$1"', "sh", str(allowed / "new")],
                                   capture_output=True, text=True)
            self.assertNotEqual(write.returncode, 0)
            self.assertFalse((allowed / "new").exists())
            with tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "new"
                write = subprocess.run(shell + ['printf blocked > "$1"', "sh", str(target)],
                                       capture_output=True, text=True)
                self.assertNotEqual(write.returncode, 0)
                self.assertFalse(target.exists())
            child = subprocess.run(shell + ["exec /usr/bin/true"], capture_output=True, text=True)
            self.assertNotEqual(child.returncode, 0)


if __name__ == "__main__":
    unittest.main()
