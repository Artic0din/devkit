#!/usr/bin/env python3
"""Offline tests for hooks/claude-worktree.py against throwaway Git repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("claude-worktree.py")


def sh(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


class ClaudeWorktreeHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "app"
        self.repo.mkdir()
        sh(self.repo, "git", "init", "-q", "-b", "main")
        (self.repo / "f").write_text("x")
        sh(self.repo, "git", "add", "f")
        sh(self.repo, "git", "commit", "-q", "-m", "init")
        self.root = self.tmp / "worktrees"

    def hook(self, verb: str, event: dict) -> subprocess.CompletedProcess:
        return subprocess.run(["python3", str(HOOK), verb], input=json.dumps(event), capture_output=True, text=True,
                              env={**os.environ, "AGENT_WORKTREES_ROOT": str(self.root)})

    def test_create_resume_remove(self) -> None:
        made = self.hook("create", {"name": "fix auth", "cwd": str(self.repo / ".")})
        self.assertEqual(made.returncode, 0, made.stderr)
        path = Path(made.stdout.strip().splitlines()[-1])
        self.assertEqual(path, self.root / "claude" / "app" / "fix-auth")
        self.assertEqual(sh(path, "git", "branch", "--show-current"), "worktree-fix-auth")
        again = self.hook("create", {"name": "fix auth", "cwd": str(self.repo)})
        self.assertEqual(again.stdout.strip(), str(path))
        gone = self.hook("remove", {"worktree_path": str(path)})
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertFalse(path.exists())
        self.assertIn("worktree-fix-auth", sh(self.repo, "git", "branch"))
        reused = self.hook("create", {"name": "fix auth", "cwd": str(self.repo)})
        self.assertEqual(reused.returncode, 0, reused.stderr)
        self.assertEqual(sh(path, "git", "branch", "--show-current"), "worktree-fix-auth")

    def test_same_named_repos_get_separate_paths(self) -> None:
        twin = self.tmp / "other" / "app"
        twin.mkdir(parents=True)
        sh(twin, "git", "init", "-q", "-b", "main")
        sh(twin, "git", "commit", "-q", "--allow-empty", "-m", "init")
        first = Path(self.hook("create", {"name": "x", "cwd": str(self.repo)}).stdout.strip())
        second = Path(self.hook("create", {"name": "x", "cwd": str(twin)}).stdout.strip())
        self.assertNotEqual(first, second)
        self.assertEqual(sh(second, "git", "rev-parse", "--path-format=absolute", "--git-common-dir"), str(twin / ".git"))

    def test_remove_refuses_outside_root(self) -> None:
        other = self.tmp / "other"
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "other", str(other))
        done = self.hook("remove", {"worktree_path": str(other)})
        self.assertNotEqual(done.returncode, 0)
        self.assertTrue(other.exists())

    def test_create_outside_git_fails(self) -> None:
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertNotEqual(self.hook("create", {"name": "x", "cwd": str(plain)}).returncode, 0)


if __name__ == "__main__":
    unittest.main()
