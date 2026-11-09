#!/usr/bin/env python3
"""Offline tests for scripts/agent-sweep against real throwaway Git repositories."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

LOADER = importlib.machinery.SourceFileLoader("agent_sweep", str(Path(__file__).with_name("agent-sweep")))
SPEC = importlib.util.spec_from_loader("agent_sweep", LOADER)
assert SPEC
sweep_mod = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(sweep_mod)


def sh(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


class AgentSweepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        os.environ["AGENT_SWEEP_SKIP_SIMULATORS"] = "1"
        self.remote = self.tmp / "remote.git"
        sh(self.tmp, "git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        self.repo = self.tmp / "projects" / "app"
        self.repo.mkdir(parents=True)
        sh(self.repo, "git", "init", "-q", "-b", "main")
        sh(self.repo, "git", "remote", "add", "origin", str(self.remote))
        (self.repo / ".gitignore").write_text("node_modules/\n")
        self.commit("init")
        sh(self.repo, "git", "push", "-q", "-u", "origin", "main")
        sh(self.repo, "git", "remote", "set-head", "origin", "main")
        self.wts = self.tmp / "worktrees"
        self.wts.mkdir()
        self.squashed = ""
        fake = self.tmp / "fake-gh"
        fake.write_text('#!/bin/sh\nprintf \'[{"headRefOid":"%s"}]\' "$(cat "$0.sha" 2>/dev/null)"\n')
        fake.chmod(0o755)
        os.environ["AGENT_SWEEP_GH"] = str(fake)
        # GitHub-looking fetch URL so the PR lookup runs; pushes still go to the local bare repo.
        sh(self.repo, "git", "remote", "set-url", "origin", "https://github.com/o/app.git")
        sh(self.repo, "git", "remote", "set-url", "--push", "origin", str(self.remote))

    def commit(self, msg: str, where: Path | None = None) -> str:
        where = where or self.repo
        (where / f"{msg}.txt").write_text(msg)
        sh(where, "git", "add", "-A")
        sh(where, "git", "commit", "-q", "-m", msg)
        return sh(where, "git", "rev-parse", "HEAD")

    def worktree(self, name: str) -> Path:
        wt = self.wts / name
        sh(self.repo, "git", "worktree", "add", "-q", "-b", name, str(wt), "main")
        return wt

    def run_sweep(self, apply: bool = False, days: int = 0) -> tuple[str, dict]:
        buf = io.StringIO()
        totals = sweep_mod.sweep([self.tmp / "projects", self.wts], apply, days, False, out=buf)
        return buf.getvalue(), totals

    def line(self, report: str, needle: str) -> str:
        hits = [l for l in report.splitlines() if needle in l]
        self.assertEqual(len(hits), 1, f"{needle!r} in:\n{report}")
        return hits[0]

    def test_verdicts_and_apply(self) -> None:
        merged = self.worktree("merged")
        self.commit("merged-work", merged)
        sh(self.repo, "git", "merge", "-q", "--ff-only", "merged")
        sh(self.repo, "git", "push", "-q", "origin", "main")

        dirty = self.worktree("dirty")
        (dirty / "scratch.txt").write_text("keep me")

        unpushed = self.worktree("unpushed")
        self.commit("local-only", unpushed)

        squash = self.worktree("squash")
        tip = self.commit("squash-work", squash)
        sh(squash, "git", "push", "-q", "origin", "squash")
        Path(os.environ["AGENT_SWEEP_GH"] + ".sha").write_text(tip)

        stale = self.worktree("stale")
        self.commit("stale-work", stale)
        sh(stale, "git", "push", "-q", "origin", "stale")
        (stale / "node_modules" / "pkg").mkdir(parents=True)
        old = time.time() - 30 * 86400
        gitdir = Path(sh(stale, "git", "rev-parse", "--path-format=absolute", "--git-dir"))
        os.environ["GIT_COMMITTER_DATE"] = "@%d" % old
        try:
            sh(stale, "git", "commit", "-q", "--amend", "--no-edit", "--date", "@%d" % old)
        finally:
            del os.environ["GIT_COMMITTER_DATE"]
        sh(stale, "git", "push", "-q", "-f", "origin", "stale")
        for p in (gitdir / "HEAD", gitdir / "logs" / "HEAD"):
            os.utime(p, (old, old))

        sh(self.repo, "git", "branch", "old-merged", "main")
        sh(self.repo, "git", "branch", "unmerged", "unpushed")

        report, totals = self.run_sweep()
        self.assertIn("\tremove\t", self.line(report, str(merged)))
        self.assertIn("uncommitted changes", self.line(report, str(dirty)))
        self.assertIn("1 unpushed commit(s)", self.line(report, str(unpushed)))
        self.assertIn("clean and merged (squash)", self.line(report, str(squash)))
        self.assertIn("not merged yet", self.line(report, f"{stale}\t"))
        self.assertIn("reinstallable", self.line(report, str(stale / "node_modules")))
        self.assertIn("app:old-merged", report)
        self.assertNotIn("app:unmerged", report)
        self.assertTrue(merged.exists(), "report mode must not delete")
        self.assertEqual(totals["worktrees"], 2)

        self.run_sweep(apply=True)
        self.assertFalse(merged.exists())
        self.assertFalse(squash.exists())
        self.assertTrue((dirty / "scratch.txt").exists())
        self.assertTrue(unpushed.exists())
        self.assertTrue(stale.exists())
        self.assertFalse((stale / "node_modules").exists())
        branches = sh(self.repo, "git", "branch", "--format=%(refname:short)").split()
        for gone in ("merged", "squash", "old-merged"):
            self.assertNotIn(gone, branches)
        for kept in ("main", "dirty", "unpushed", "unmerged", "stale"):
            self.assertIn(kept, branches)

    def test_review_guards(self) -> None:
        fresh = self.worktree("fresh")
        secret = self.worktree("secret")
        (secret / ".gitignore").write_text("*.env\n")
        sh(secret, "git", "add", ".gitignore")
        sh(secret, "git", "commit", "-q", "-m", "ignore env")
        sh(self.repo, "git", "merge", "-q", "--ff-only", "secret")
        sh(self.repo, "git", "push", "-q", "origin", "main")
        (secret / "local.env").write_text("TOKEN=x")
        outside = self.tmp / "elsewhere" / "wt"
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "outside", str(outside), "main")
        sh(self.repo, "git", "checkout", "-q", "-b", "feature")
        on_main = self.wts / "on-main"
        sh(self.repo, "git", "worktree", "add", "-q", str(on_main), "main")

        report, _ = self.run_sweep(apply=True, days=14)
        self.assertIn("active in the last 14 days", self.line(report, str(fresh)))
        report, _ = self.run_sweep(apply=True)
        self.assertIn("ignored file local.env", self.line(report, str(secret)))
        self.assertIn("outside the scanned folders", self.line(report, str(outside)))
        self.assertIn("default branch", self.line(report, str(on_main)))
        for wt in (secret, outside, on_main):
            self.assertTrue(wt.exists(), wt)
        self.assertTrue((secret / "local.env").exists())
        self.assertIn("main", sh(self.repo, "git", "branch", "--format=%(refname:short)").split())

    def test_gh_failure_keeps_unproven_squash(self) -> None:
        wt = self.worktree("maybe")
        self.commit("maybe-work", wt)
        sh(wt, "git", "push", "-q", "origin", "maybe")
        os.environ["AGENT_SWEEP_GH"] = "/nonexistent/gh"
        report, _ = self.run_sweep(apply=True)
        self.assertIn("not merged yet", self.line(report, str(wt)))
        self.assertTrue(wt.exists())


if __name__ == "__main__":
    unittest.main()
