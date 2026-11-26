"""Exercise the actual CLI against fixed read-only gh responses."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class HeadCheck(unittest.TestCase):
    def test_remote_outcomes(self) -> None:
        head = "a" * 40
        with tempfile.TemporaryDirectory() as temp:
            gh = Path(temp) / "gh"
            gh.write_text('#!/bin/sh\n[ "$#" = 7 ] && [ "$*" = "pr view 1 --repo example/repo --json state,headRefOid" ] || exit 91\nprintf "%s" "$RESPONSE"\nexit "$RESULT"\n')
            gh.chmod(0o755)
            for state, sha, gh_exit, expected in [
                ("OPEN", head, 0, 0), ("OPEN", "b" * 40, 0, 1),
                ("MERGED", head, 0, 1), ("CLOSED", head, 0, 1),
                ("OPEN", head, 1, 2), ("OPEN", "", 0, 2),
            ]:
                with self.subTest(state=state, head=sha, gh_exit=gh_exit):
                    env = dict(os.environ, PATH=temp + os.pathsep + os.environ["PATH"],
                               RESPONSE=f'{{"state":"{state}","headRefOid":"{sha}"}}', RESULT=str(gh_exit))
                    result = subprocess.run([str(Path(__file__).with_name("pr-head-check")),
                                             "example/repo", "1", head], env=env, capture_output=True)
                    self.assertEqual(result.returncode, expected, result)


if __name__ == "__main__":
    unittest.main()
