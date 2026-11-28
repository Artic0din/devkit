#!/usr/bin/env python3
"""Offline tests for scripts/agent-sweep against real throwaway Git repositories."""

from __future__ import annotations

import fcntl
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import shutil
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
        self.addCleanup(shutil.rmtree, self.tmp, True)
        os.environ["AGENT_SWEEP_SKIP_SIMULATORS"] = "1"
        os.environ["AGENT_SWEEP_T3_DB"] = str(self.tmp / "statev2.sqlite")
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
        # Answers only a merged-PR query, so a sweep asking for other states would see nothing.
        fake.write_text('#!/bin/sh\ncase "$*" in *"--state merged"*) printf \'[{"headRefOid":"%s","headRefName":"%s","headRepository":{"name":"app"},"headRepositoryOwner":{"login":"o"}}]\' "$(cat "$0.sha" 2>/dev/null)" "$(cat "$0.name" 2>/dev/null)";; *) echo "[]";; esac\n')
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

    def age(self, wt: Path, days: int = 30) -> None:
        """Backdate a worktree's last commit and HEAD files so it looks idle."""
        old = time.time() - days * 86400
        os.environ["GIT_COMMITTER_DATE"] = "@%d" % old
        try:
            sh(wt, "git", "commit", "-q", "--amend", "--no-edit", "--date", "@%d" % old)
        finally:
            del os.environ["GIT_COMMITTER_DATE"]
        gitdir = Path(sh(wt, "git", "rev-parse", "--path-format=absolute", "--git-dir"))
        for f in (gitdir / "HEAD", gitdir / "logs" / "HEAD"):
            os.utime(f, (old, old))

    def test_verdicts_and_apply(self) -> None:
        merged = self.worktree("merged")
        self.commit("merged-work", merged)
        sh(self.repo, "git", "merge", "-q", "--ff-only", "merged")
        sh(self.repo, "git", "push", "-q", "origin", "main")

        dirty = self.worktree("dirty")
        (dirty / "scratch.txt").write_text("abandoned")

        unpushed = self.worktree("unpushed")
        self.commit("local-only", unpushed)

        squash = self.worktree("squash")
        tip = self.commit("squash-work", squash)
        sh(squash, "git", "push", "-q", "origin", "squash")
        Path(os.environ["AGENT_SWEEP_GH"] + ".sha").write_text(tip)
        Path(os.environ["AGENT_SWEEP_GH"] + ".name").write_text("squash")

        junk = self.worktree("junk")
        (junk / ".gitignore").write_text(".DS_Store\nnode_modules/\n.pytest_cache/\n*.xcodeproj/\n*.gen.ts\n.coverage\n")
        sh(junk, "git", "add", ".gitignore")
        sh(junk, "git", "commit", "-q", "-m", "ignore junk")
        (junk / ".DS_Store").write_text("x")
        for f in ("pkg/node_modules/dep/index.js", "pkg/.DS_Store", ".pytest_cache/v/cache",
                  "App.xcodeproj/project.pbxproj", "src/routeTree.gen.ts", ".coverage"):
            (junk / f).parent.mkdir(parents=True, exist_ok=True)
            (junk / f).write_text("x")

        sh(self.repo, "git", "branch", "old-merged", "main")
        sh(self.repo, "git", "branch", "unmerged", "unpushed")

        report, totals = self.run_sweep()
        self.assertIn("idle 0+ days (merged; merged)", self.line(report, str(merged)))
        self.assertIn("discards uncommitted changes", self.line(report, str(dirty)))
        self.assertIn("discards 1 unpushed commit(s)", self.line(report, str(unpushed)))
        self.assertIn("(squash; merged)", self.line(report, str(squash)))
        self.assertIn("\tremove\t", self.line(report, str(junk)))
        self.assertIn("app:old-merged", report)
        self.assertIn("not proven merged", self.line(report, "app:unmerged"))
        for still in (merged, dirty, squash, junk):
            self.assertTrue(still.exists(), f"report mode deleted {still}")
        self.assertEqual(totals["worktrees"], 5)

        self.run_sweep(apply=True)
        for gone in (merged, dirty, unpushed, squash, junk):
            self.assertFalse(gone.exists(), gone)
        branches = sh(self.repo, "git", "branch", "--format=%(refname:short)").split()
        for gone in ("merged", "dirty", "unpushed", "squash", "junk", "old-merged"):
            self.assertNotIn(gone, branches)
        for kept in ("main", "unmerged"):
            self.assertIn(kept, branches)

    def test_kept_idle_worktree_loses_node_modules(self) -> None:
        wt = self.worktree("has-secret")
        (wt / ".gitignore").write_text("*.env\nnode_modules/\n")
        sh(wt, "git", "add", ".gitignore")
        sh(wt, "git", "commit", "-q", "-m", "ignore env")
        self.age(wt)
        (wt / "local.env").write_text("TOKEN=x")
        (wt / "node_modules" / "pkg").mkdir(parents=True)
        report, _ = self.run_sweep(apply=True, days=14)
        self.assertIn("ignored file local.env", self.line(report, f"{wt}\t"))
        self.assertIn("reinstallable", self.line(report, str(wt / "node_modules")))
        self.assertTrue((wt / "local.env").exists())
        self.assertFalse((wt / "node_modules").exists())

    def test_review_guards(self) -> None:
        fresh = self.worktree("fresh")
        secret = self.worktree("secret")
        (secret / ".gitignore").write_text("*.env\nbuild\n")
        sh(secret, "git", "add", ".gitignore")
        sh(secret, "git", "commit", "-q", "-m", "ignore env")
        sh(self.repo, "git", "merge", "-q", "--ff-only", "secret")
        sh(self.repo, "git", "push", "-q", "origin", "main")
        (secret / "local.env").write_text("TOKEN=x")
        plain = self.worktree("plain-file")
        (plain / "build").write_text("not a folder")
        outside = self.tmp / "elsewhere" / "wt"
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "outside", str(outside), "main")
        sh(self.repo, "git", "checkout", "-q", "-b", "feature")
        on_main = self.wts / "on-main"
        sh(self.repo, "git", "worktree", "add", "-q", str(on_main), "main")

        report, _ = self.run_sweep(apply=True, days=14)
        self.assertIn("active in the last 14 days", self.line(report, str(fresh)))  # a fresh worktree is not finished
        report, _ = self.run_sweep(apply=True)
        self.assertIn("ignored file local.env", self.line(report, str(secret)))
        self.assertIn("ignored file build", self.line(report, str(plain)))
        self.assertIn("outside the scanned folders", self.line(report, str(outside)))
        self.assertIn("default branch", self.line(report, str(on_main)))
        for wt in (secret, outside, on_main):
            self.assertTrue(wt.exists(), wt)
        self.assertTrue((secret / "local.env").exists())
        self.assertIn("main", sh(self.repo, "git", "branch", "--format=%(refname:short)").split())

    def test_nested_repo_and_submodule_are_kept(self) -> None:
        nested = self.worktree("nested")
        inner = nested / "vendor" / "inner"
        inner.mkdir(parents=True)
        sh(inner, "git", "init", "-q")
        (inner / ".gitignore").write_text("*.env\n")
        (inner / "s.env").write_text("TOKEN=x")
        subs = self.worktree("subs")
        (subs / ".gitmodules").write_text("")
        report, _ = self.run_sweep(apply=True)
        self.assertIn("nested repository vendor/inner", self.line(report, str(nested)))
        self.assertIn("has submodules", self.line(report, str(subs)))
        self.assertTrue((inner / "s.env").exists())
        self.assertTrue(subs.exists())

    def test_missing_outside_worktree_is_not_pruned(self) -> None:
        outside = self.tmp / "elsewhere" / "gone"
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "gone", str(outside), "main")
        shutil.rmtree(outside)
        report, _ = self.run_sweep(apply=True)
        self.assertIn("outside the scanned folders", self.line(report, str(outside)))
        self.assertIn(str(outside), sh(self.repo, "git", "worktree", "list"))

    def test_scratch_idle_entries_removed(self) -> None:
        import sqlite3
        from datetime import datetime, timezone

        scratch = self.tmp / "scratch"
        old = time.time() - 30 * 86400
        stale, fresh, snoozed_scratch, reg_proj, nested = (
            scratch / "t3" / "stale-job",
            scratch / "t3" / "fresh-job",
            scratch / "t3" / "snoozed-no-project",
            scratch / "t3" / "registered-proj ",
            scratch / "claude" / "claude-501" / "proj",
        )
        for f in (
            stale / "out.png",
            fresh / "out.png",
            snoozed_scratch / "notes.md",
            reg_proj / "unsaved.txt",
            nested / "old-session" / "x",
            nested / "new-session" / "y",
        ):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x")
        for p in (
            stale / "out.png",
            stale,
            snoozed_scratch / "notes.md",
            snoozed_scratch,
            reg_proj / "unsaved.txt",
            reg_proj,
            nested / "old-session" / "x",
            nested / "old-session",
        ):
            os.utime(p, (old, old))
        future_iso = datetime.fromtimestamp(time.time() + 5 * 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        stale_iso = datetime.fromtimestamp(old, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        alt_case = scratch / "T3" / "SNOOZED-NO-PROJECT"
        db_wt_path = str(alt_case) if alt_case.exists() and os.path.samestat(alt_case.stat(), snoozed_scratch.stat()) else str(snoozed_scratch)
        outside_target = self.tmp / "outside-scratch-target"
        outside_target.mkdir(parents=True)
        alias_root = self.tmp / "t3-scratch-alias"
        alias_root.symlink_to(scratch / "t3")
        alias_box = scratch / "t3" / "aliased-box"
        alias_box.mkdir(parents=True)
        mid_hop = scratch / "t3" / "mid-hop-link"
        mid_hop.symlink_to(outside_target)
        (alias_box / "link").symlink_to(mid_hop)
        os.utime(alias_box, (old, old))
        try:
            os.utime(mid_hop, (old, old), follow_symlinks=False)
            os.utime(alias_box / "link", (old, old), follow_symlinks=False)
        except (NotImplementedError, OSError):
            pass
        con = sqlite3.connect(os.environ["AGENT_SWEEP_T3_DB"])
        con.execute("CREATE TABLE orchestration_v2_projection_threads (updated_at TEXT NOT NULL, deleted_at TEXT, payload_json TEXT NOT NULL)")
        con.execute("CREATE TABLE projection_projects (project_id TEXT, workspace_root TEXT, deleted_at TEXT)")
        con.execute("INSERT INTO projection_projects VALUES ('p-scratch', ?, NULL)", (str(scratch),))
        con.execute("INSERT INTO projection_projects VALUES ('p-reg', ?, NULL)", (str(reg_proj),))
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (stale_iso, json.dumps({"worktreePath": db_wt_path, "updatedAt": stale_iso, "snoozedUntil": future_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (recent_iso := datetime.fromtimestamp(time.time() - 3600, tz=timezone.utc).isoformat().replace("+00:00", "Z"), json.dumps({"worktreePath": str(alias_root / "aliased-box" / "link"), "updatedAt": recent_iso})),
        )
        con.commit()
        con.close()
        buf = io.StringIO()
        sweep_mod.sweep([self.wts], False, 14, False, out=buf, scratch=scratch)
        self.assertIn("\tremove\t", self.line(buf.getvalue(), str(stale)))
        self.assertIn("\tremove\t", self.line(buf.getvalue(), str(nested / "old-session")))
        self.assertNotIn(str(snoozed_scratch), buf.getvalue())
        self.assertNotIn(str(reg_proj), buf.getvalue())
        self.assertNotIn(str(alias_box), buf.getvalue())
        self.assertNotIn(str(mid_hop), buf.getvalue())
        self.assertTrue(stale.exists(), "report mode deleted scratch")
        sweep_mod.sweep([self.wts], True, 14, False, out=io.StringIO(), scratch=scratch)
        self.assertFalse(stale.exists())
        self.assertFalse((nested / "old-session").exists())
        for kept in (fresh, snoozed_scratch, snoozed_scratch / "notes.md", reg_proj, reg_proj / "unsaved.txt", alias_box, alias_box / "link", mid_hop, nested / "new-session"):
            self.assertTrue(kept.exists(), kept)

    def test_jobs_follow_their_lock_not_their_age(self) -> None:
        scratch = self.tmp / "scratch"
        jobs = scratch / "agent-job"
        old = time.time() - 30 * 86400

        def job(name: str) -> Path:
            d = jobs / name
            (d / "tmp").mkdir(parents=True)
            (d / "tmp" / "out").write_text("x")
            (d / "job.lock").write_text("")
            (d / "job.json").write_text(json.dumps({"id": name, "colima_profile": None}))
            return d
        dead_fresh, dead_old, running = job("dead-fresh"), job("dead-old"), job("running")
        for d in (dead_old, running):
            for f in (d / "tmp" / "out", d / "tmp", d / "job.json", d / "job.lock", d):
                os.utime(f, (old, old))
        held = os.open(running / "job.lock", os.O_RDWR)
        self.addCleanup(os.close, held)
        fcntl.flock(held, fcntl.LOCK_EX)  # what a live agent-job runner holds
        derived = scratch / "xcode" / "App-12345678" / "DerivedData" / "Build"
        derived.mkdir(parents=True)
        for f in (derived, derived.parent, derived.parent.parent):
            os.utime(f, (old, old))
        buf = io.StringIO()
        totals = sweep_mod.sweep([self.wts], False, 14, False, out=buf, scratch=scratch)
        self.assertEqual(totals["jobs"], 2)
        self.assertIn("job is running", self.line(buf.getvalue(), str(running)))
        self.assertTrue(dead_old.exists(), "report mode removed a job")
        sweep_mod.sweep([self.wts], True, 14, False, out=io.StringIO(), scratch=scratch)
        self.assertFalse(dead_fresh.exists())
        self.assertFalse(dead_old.exists())
        self.assertTrue((running / "tmp" / "out").exists(), "idle running job was removed")
        self.assertFalse((scratch / "xcode" / "App-12345678").exists(), "idle DerivedData scratch kept")

    def test_worktree_reached_through_link_counts_as_inside(self) -> None:
        # What agent-locations does: the app made a worktree in its own folder, which was then
        # moved into the shared root and replaced by a link, so git still records the old path.
        app_dir = self.tmp / "app-folder"
        linked = app_dir / "via-link"
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "via-link", str(linked), "main")
        shutil.move(str(linked), str(self.wts / "via-link"))
        app_dir.rmdir()
        app_dir.symlink_to(self.wts)
        report, _ = self.run_sweep(apply=True)
        self.assertIn("\tremove\t", self.line(report, str(linked)))
        self.assertFalse((self.wts / "via-link").exists())
    def test_removes_worktrees_when_main_checkout_is_outside_roots(self) -> None:
        # Only the worktree folder is scanned, so the sweep finds the repository through one of
        # its linked worktrees; removal must still run from the main checkout.
        first, second = self.worktree("first"), self.worktree("second")
        real = sweep_mod.find_repos
        sweep_mod.find_repos = lambda roots: [first]  # the scan reached the repo through "first"
        self.addCleanup(setattr, sweep_mod, "find_repos", real)
        buf = io.StringIO()
        sweep_mod.sweep([self.wts], True, 0, False, out=buf)
        self.assertNotIn("\terror\t", buf.getvalue())
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())

    def test_merged_worktree_removed_even_when_fresh(self) -> None:
        done = self.worktree("done-today")  # squash-merged PR from this branch
        tip = self.commit("finished", done)
        Path(os.environ["AGENT_SWEEP_GH"] + ".sha").write_text(tip)
        Path(os.environ["AGENT_SWEEP_GH"] + ".name").write_text("done-today")
        stacked = self.wts / "stacked"  # new branch on that merged tip, nothing committed
        sh(self.repo, "git", "worktree", "add", "-q", "-b", "stacked", str(stacked), tip)
        gone = self.worktree("branch-deleted")  # merged, then its own remote branch was deleted
        self.commit("landed", gone)
        # Push by remote name: before Git 2.56, a push to a URL never creates origin/<branch>.
        sh(gone, "git", "push", "-q", "-u", "origin", "branch-deleted")
        sh(self.repo, "git", "merge", "-q", "--ff-only", "branch-deleted")
        inherited = self.wts / "inherited"  # tracks another branch that is gone
        sh(self.repo, "git", "worktree", "add", "-q", "--track", "-b", "inherited", str(inherited), "origin/branch-deleted")
        dirty = self.worktree("finished-but-editing")
        self.commit("pr-work", dirty)
        sh(dirty, "git", "push", "-q", str(self.remote), "finished-but-editing:finished-but-editing")
        sh(self.repo, "git", "fetch", "-q", str(self.remote), "+refs/heads/*:refs/remotes/origin/*")
        sh(dirty, "git", "branch", "-q", "--set-upstream-to=origin/finished-but-editing")
        sh(self.repo, "git", "merge", "-q", "--ff-only", "finished-but-editing")
        sh(self.repo, "git", "push", "-q", "origin", "main", ":branch-deleted", ":finished-but-editing")
        sh(self.repo, "git", "fetch", "-q", "--prune", str(self.remote), "+refs/heads/*:refs/remotes/origin/*")
        (dirty / "notes.txt").write_text("wip")
        fresh = self.worktree("just-started")  # tip still on main, but no work has landed
        fresh_gone = self.worktree("pushed-then-deleted")  # own upstream gone, but no commits of its own
        sh(fresh_gone, "git", "push", "-q", "-u", "origin", "pushed-then-deleted")
        sh(self.repo, "git", "push", "-q", "origin", ":pushed-then-deleted")
        sh(self.repo, "git", "fetch", "-q", "--prune", str(self.remote), "+refs/heads/*:refs/remotes/origin/*")
        report, _ = self.run_sweep(apply=True, days=5)
        self.assertIn("merged (done-today; merged)", self.line(report, str(done)))
        self.assertIn("merged (branch-deleted; merged)", self.line(report, str(gone)))
        for kept in (fresh, fresh_gone, dirty, stacked, inherited):
            self.assertIn("active in the last 5 days", self.line(report, f"{kept}\t"))
            self.assertTrue(kept.exists(), kept)
        self.assertFalse(done.exists())
        self.assertFalse(gone.exists())

    def test_failed_fetch_keeps_merged_branch(self) -> None:
        sh(self.repo, "git", "branch", "also-merged", "main")
        sh(self.repo, "git", "remote", "set-url", "origin", str(self.tmp / "missing.git"))
        buf = io.StringIO()
        sweep_mod.sweep([self.wts, self.tmp / "projects"], True, 0, True, out=buf)
        self.assertIn("not proven merged", self.line(buf.getvalue(), "app:also-merged"))
        self.assertIn("also-merged", sh(self.repo, "git", "branch", "--format=%(refname:short)").split())

    def test_gh_failure_keeps_unproven_squash_branch(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "maybe")
        tip = self.commit("maybe-work")
        sh(self.repo, "git", "push", "-q", "origin", "maybe")
        sh(self.repo, "git", "checkout", "-q", "main")
        Path(os.environ["AGENT_SWEEP_GH"] + ".sha").write_text(tip)
        os.environ["AGENT_SWEEP_GH"] = "/nonexistent/gh"
        report, _ = self.run_sweep(apply=True)
        self.assertIn("merged-PR lookup failed", self.line(report, "github\twarning"))
        self.assertIn("not proven merged", self.line(report, "app:maybe"))
        self.assertIn("maybe", sh(self.repo, "git", "branch", "--format=%(refname:short)").split())

    def test_default_idle_days_preserves_snoozed_t3_worktrees_under_ten_days(self) -> None:
        import json, sqlite3
        from datetime import datetime, timezone

        self.assertEqual(sweep_mod.DEFAULT_IDLE_DAYS, 10)
        snoozed = self.worktree("snoozed-six-days")
        self.commit("wip-snoozed", snoozed)
        self.age(snoozed, days=6)

        t3_active = self.worktree("git-old-t3-recent")
        self.commit("wip-t3-active", t3_active)
        self.age(t3_active, days=15)  # Git commits are >10 days old, but T3 thread updated 2 days ago.

        woke_unread = self.worktree("snooze-woke-marked-unread")
        self.commit("wip-woke-unread", woke_unread)
        (woke_unread / "uncommitted.txt").write_text("keep")
        self.age(woke_unread, days=15)

        link_host = self.worktree("symlink-carrier")
        self.commit("wip-carrier", link_host)
        (link_host / "jump").symlink_to(t3_active)
        sh(link_host, "git", "add", "jump")
        self.commit("track-jump", link_host)
        self.age(link_host, days=15)

        def land_and_delete_remote_branch(wt: Path, branch: str) -> None:
            sh(wt, "git", "push", "-q", str(self.remote), f"{branch}:{branch}")
            sh(self.repo, "git", "fetch", "-q", str(self.remote), "+refs/heads/*:refs/remotes/origin/*")
            sh(wt, "git", "branch", "-q", f"--set-upstream-to=origin/{branch}")
            sh(self.repo, "git", "merge", "-q", "--ff-only", branch)
            sh(self.repo, "git", "push", "-q", str(self.remote), "main", f":{branch}")
            sh(self.repo, "git", "fetch", "-q", "--prune", str(self.remote), "+refs/heads/*:refs/remotes/origin/*")

        tf_primary = self.worktree("tf-primary")
        self.commit("wip-tf-primary", tf_primary)
        self.age(tf_primary, days=15)
        tf_companion = self.worktree("tf-companion")
        self.commit("wip-tf-companion", tf_companion)
        self.age(tf_companion, days=15)
        land_and_delete_remote_branch(tf_companion, "tf-companion")

        merged_carrier = self.worktree("merged-symlink-carrier")
        (merged_carrier / "to-active").symlink_to(t3_active)
        sh(merged_carrier, "git", "add", "to-active")
        self.commit("merged-carrier-link", merged_carrier)
        self.age(merged_carrier, days=15)
        land_and_delete_remote_branch(merged_carrier, "merged-symlink-carrier")

        merged_snoozed = self.worktree("merged-but-snoozed")
        self.commit("merged-snoozed-work", merged_snoozed)
        land_and_delete_remote_branch(merged_snoozed, "merged-but-snoozed")

        merged_running = self.worktree("merged-with-running-run")
        self.commit("merged-running-work", merged_running)
        land_and_delete_remote_branch(merged_running, "merged-with-running-run")

        sub_child = self.worktree("subagent-isolated-child")
        self.commit("subagent-child-work", sub_child)
        self.age(sub_child, days=15)
        (sub_child / "child-wip.txt").write_text("pending-delivery")

        sub_from_main = self.worktree("subagent-from-main-parent")
        self.commit("subagent-main-parent-work", sub_from_main)
        self.age(sub_from_main, days=20)
        (sub_from_main / "main-child-wip.txt").write_text("active-main-parent")

        merged_plain = self.worktree("merged-plain-settled")
        self.commit("merged-plain-work", merged_plain)
        land_and_delete_remote_branch(merged_plain, "merged-plain-settled")

        expired = self.worktree("expired-eleven-days")
        self.commit("wip-expired", expired)
        self.age(expired, days=11)

        recent_iso = datetime.fromtimestamp(time.time() - 2 * 86400, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        woke_iso = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        stale_iso = datetime.fromtimestamp(time.time() - 12 * 86400, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        tomorrow_iso = datetime.fromtimestamp(time.time() + 86400, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        con = sqlite3.connect(os.environ["AGENT_SWEEP_T3_DB"])
        con.execute("CREATE TABLE orchestration_v2_projection_threads (thread_id TEXT, updated_at TEXT NOT NULL, deleted_at TEXT, payload_json TEXT NOT NULL)")
        con.execute("CREATE TABLE orchestration_v2_projection_runs (run_id TEXT, thread_id TEXT, status TEXT, requested_at TEXT, completed_at TEXT, payload_json TEXT)")
        con.execute("CREATE TABLE orchestration_v2_projection_subagents (subagent_id TEXT, thread_id TEXT, child_thread_id TEXT, status TEXT, completion_delivery_state TEXT, started_at TEXT, completed_at TEXT, updated_at TEXT, payload_json TEXT)")
        con.execute("CREATE TABLE task_folders (root TEXT, real_root TEXT, project_id TEXT, project_root TEXT, anchor TEXT, project_path TEXT, project_is_worktree INTEGER, repositories_json TEXT, created_at TEXT)")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-link', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "t-link", "worktreePath": str(link_host / "jump"), "updatedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-carrier', ?, NULL, ?)",
            (stale_iso, json.dumps({"id": "t-carrier", "worktreePath": str(merged_carrier / "to-active"), "updatedAt": stale_iso, "snoozedUntil": tomorrow_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-msnooze', ?, NULL, ?)",
            (stale_iso, json.dumps({"id": "t-msnooze", "worktreePath": str(merged_snoozed), "updatedAt": stale_iso, "snoozedUntil": tomorrow_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-mrun', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "t-mrun", "worktreePath": str(merged_running), "updatedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_runs VALUES ('run-live', 't-mrun', 'running', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "run-live", "threadId": "t-mrun", "status": "running", "requestedAt": recent_iso, "startedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-subchild', ?, NULL, ?)",
            (stale_iso, json.dumps({"id": "t-subchild", "worktreePath": str(sub_child), "updatedAt": stale_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_subagents VALUES ('sa-1', 't-mrun', 't-subchild', 'completed', 'pending', ?, ?, ?, ?)",
            (stale_iso, stale_iso, stale_iso, json.dumps({"id": "sa-1", "threadId": "t-mrun", "childThreadId": "t-subchild", "status": "completed"})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-mainparent', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "t-mainparent", "worktreePath": None, "updatedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-submain', ?, NULL, ?)",
            (
                stale_iso,
                json.dumps(
                    {
                        "id": "t-submain",
                        "worktreePath": str(sub_from_main),
                        "updatedAt": stale_iso,
                        "lineage": {"parentThreadId": "t-mainparent", "relationshipToParent": "subagent", "rootThreadId": "t-mainparent"},
                    }
                ),
            ),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_subagents VALUES ('sa-2', 't-mainparent', 't-submain', 'completed', 'delivered', ?, ?, ?, ?)",
            (stale_iso, stale_iso, stale_iso, json.dumps({"id": "sa-2", "threadId": "t-mainparent", "childThreadId": "t-submain", "status": "completed"})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-mplain', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "t-mplain", "worktreePath": str(merged_plain), "updatedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_runs VALUES ('run-done', 't-mplain', 'completed', ?, ?, ?)",
            (recent_iso, recent_iso, json.dumps({"id": "run-done", "threadId": "t-mplain", "status": "completed", "requestedAt": recent_iso, "completedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-tf', ?, NULL, ?)",
            (recent_iso, json.dumps({"id": "t-tf", "worktreePath": str(tf_primary), "updatedAt": recent_iso})),
        )
        con.execute(
            "INSERT INTO task_folders VALUES (?, ?, 'p1', ?, ?, ?, 1, ?, ?)",
            (
                str(self.wts / "tf-root"),
                str((self.wts / "tf-root").resolve()),
                str(self.repo),
                str(self.tmp),
                str(tf_primary),
                json.dumps([{"repositoryPath": str(self.repo), "worktreePath": str(tf_companion), "name": "companion"}]),
                stale_iso,
            ),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-woke', ?, NULL, ?)",
            (stale_iso, json.dumps({"id": "t-woke", "worktreePath": str(woke_unread), "updatedAt": stale_iso, "snoozedUntil": None, "lastSnoozeWakeAt": woke_iso})),
        )
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES ('t-exp', ?, NULL, ?)",
            (stale_iso, json.dumps({"id": "t-exp", "worktreePath": str(expired), "updatedAt": stale_iso})),
        )
        con.commit()
        con.close()

        rc = sweep_mod.main(["--apply", "--no-fetch", str(self.tmp / "projects"), str(self.wts)])
        self.assertEqual(rc, 0)
        self.assertTrue(snoozed.exists(), "6-day Git-idle worktree should survive default 10-day retention")
        self.assertTrue(t3_active.exists(), "15-day Git-old worktree with 2-day-old T3 thread activity should survive")
        self.assertTrue(link_host.exists(), "worktree containing a symlink traversed by an active T3 worktreePath should survive")
        self.assertTrue(merged_carrier.exists(), "clean merged worktree containing a symlink traversed by a snoozed T3 thread should survive")
        self.assertTrue(merged_snoozed.exists(), "clean merged worktree snoozed until tomorrow should survive")
        self.assertTrue(merged_running.exists(), "clean merged worktree with a running row in orchestration_v2_projection_runs should survive")
        self.assertTrue(sub_child.exists(), "isolated subagent child checkout with pending completion delivery should survive")
        self.assertTrue((sub_child / "child-wip.txt").exists(), "uncommitted file in isolated subagent child checkout should survive")
        self.assertTrue(sub_from_main.exists(), "isolated subagent child checkout of an active main-checkout parent (worktreePath=None) should survive")
        self.assertTrue((sub_from_main / "main-child-wip.txt").exists(), "uncommitted file in child of active main-checkout parent should survive")
        self.assertTrue(tf_companion.exists(), "merged companion checkout in task_folders of an active primary checkout should survive")
        self.assertTrue(woke_unread.exists(), "worktree whose snooze woke 1 day ago (lastSnoozeWakeAt) should survive")
        self.assertFalse(merged_plain.exists(), "clean merged worktree with only completed runs should still be removed")
        self.assertFalse(expired.exists(), "11-day idle worktree with stale T3 thread should be removed")

    def test_unreadable_t3_db_fails_closed_and_keeps_unmerged_worktree(self) -> None:
        import sqlite3
        risky = self.worktree("snoozed-with-corrupt-db")
        self.commit("unpushed-commit", risky)
        self.age(risky, days=15)
        (risky / "dirty.txt").write_text("unsaved")
        (risky / "node_modules" / "pkg").mkdir(parents=True)
        db = Path(os.environ["AGENT_SWEEP_T3_DB"])

        # 1. Corrupt SQLite header
        db.write_bytes(b"corrupt sqlite header")
        report, _ = self.run_sweep(apply=True, days=10)
        self.assertIn("T3 thread activity could not be checked", self.line(report, "t3\twarning"))
        self.assertIn("T3 thread activity could not be checked", self.line(report, f"{risky}\t"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "node_modules").exists())

        # 2. Valid SQLite table missing payload_json column (schema drift)
        db.unlink()
        con = sqlite3.connect(str(db))
        con.execute("CREATE TABLE orchestration_v2_projection_threads (thread_id TEXT PRIMARY KEY, updated_at TEXT NOT NULL)")
        con.commit()
        con.close()
        report, _ = self.run_sweep(apply=True, days=10)
        self.assertIn("T3 thread activity could not be checked", self.line(report, "t3\twarning"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "dirty.txt").exists())
        self.assertTrue((risky / "node_modules").exists())

        # 3. Stale valid updated_at combined with unparseable snoozedUntil must still fail closed
        import json
        db.unlink()
        con = sqlite3.connect(str(db))
        con.execute("CREATE TABLE orchestration_v2_projection_threads (updated_at TEXT NOT NULL, deleted_at TEXT, payload_json TEXT NOT NULL)")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            ("2026-01-01T00:00:00Z", json.dumps({"worktreePath": str(risky), "updatedAt": "2026-01-01T00:00:00Z", "snoozedUntil": "not-an-iso-date"})),
        )
        con.commit()
        con.close()
        report, _ = self.run_sweep(apply=True, days=10)
        self.assertIn("T3 thread activity could not be checked", self.line(report, "t3\twarning"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "dirty.txt").exists())
        self.assertTrue((risky / "node_modules").exists())

        # 4. Special URI characters (?, #, %20) in DB path open the exact file rather than truncating at '?'
        from datetime import datetime, timezone
        special_db = self.tmp / "state?v2#special%20.sqlite"
        recent_iso = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        con = sqlite3.connect(str(special_db))
        con.execute("CREATE TABLE orchestration_v2_projection_threads (updated_at TEXT NOT NULL, deleted_at TEXT, payload_json TEXT NOT NULL)")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (recent_iso, json.dumps({"worktreePath": str(risky), "updatedAt": recent_iso})),
        )
        con.commit()
        con.close()
        os.environ["AGENT_SWEEP_T3_DB"] = str(special_db)
        report, _ = self.run_sweep(apply=True, days=10)
        self.assertIn("active in the last 10 days", self.line(report, f"{risky}\t"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "node_modules").exists())

        # 5. Mid-sweep T3 wakeup during disk measurement (size_kb) keeps disposable worktrees and node_modules
        stale_iso = datetime.fromtimestamp(time.time() - 15 * 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        con = sqlite3.connect(str(special_db))
        con.execute("DELETE FROM orchestration_v2_projection_threads")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (stale_iso, json.dumps({"worktreePath": str(risky), "updatedAt": stale_iso})),
        )
        con.commit()
        con.close()
        orig_size_kb = sweep_mod.size_kb

        def wakeup_during_wt_size(p: Path) -> int:
            res = orig_size_kb(p)
            if p == risky:
                c2 = sqlite3.connect(str(special_db))
                c2.execute(
                    "UPDATE orchestration_v2_projection_threads SET updated_at = ?, payload_json = ?",
                    (recent_iso, json.dumps({"worktreePath": str(risky), "updatedAt": recent_iso})),
                )
                c2.commit()
                c2.close()
            return res

        sweep_mod.size_kb = wakeup_during_wt_size
        try:
            report, _ = self.run_sweep(apply=True, days=10)
        finally:
            sweep_mod.size_kb = orig_size_kb
        self.assertIn("active in the last 10 days", self.line(report, f"{risky}\t"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "dirty.txt").exists())
        self.assertTrue((risky / "node_modules").exists())

        # 5b. T3 wakeup during node_modules size_kb on an otherwise kept idle worktree preserves node_modules
        (risky / ".env").write_text("SECRET=1\n")
        (self.repo / ".gitignore").write_text(".env\nnode_modules/\n")
        sh(self.repo, "git", "add", ".gitignore")
        self.commit("ignore-env")
        sh(risky, "git", "merge", "-q", "main")
        self.age(risky, days=15)
        con = sqlite3.connect(str(special_db))
        con.execute("DELETE FROM orchestration_v2_projection_threads")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (stale_iso, json.dumps({"worktreePath": str(risky), "updatedAt": stale_iso})),
        )
        con.commit()
        con.close()

        def wakeup_during_nm_size(p: Path) -> int:
            res = orig_size_kb(p)
            if p == risky / "node_modules":
                c2 = sqlite3.connect(str(special_db))
                c2.execute(
                    "UPDATE orchestration_v2_projection_threads SET updated_at = ?, payload_json = ?",
                    (recent_iso, json.dumps({"worktreePath": str(risky), "updatedAt": recent_iso})),
                )
                c2.commit()
                c2.close()
            return res

        sweep_mod.size_kb = wakeup_during_nm_size
        try:
            report, _ = self.run_sweep(apply=True, days=10)
        finally:
            sweep_mod.size_kb = orig_size_kb
        self.assertTrue((risky / "node_modules").exists())
        self.assertNotIn("node_modules\tremove", report)

        # 5c. Future snooze committed during final last_activity check still preserves worktree and node_modules
        future_snooze = datetime.fromtimestamp(time.time() + 3 * 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        (risky / ".env").unlink()
        self.age(risky, days=15)
        con = sqlite3.connect(str(special_db))
        con.execute("DELETE FROM orchestration_v2_projection_threads")
        con.execute(
            "INSERT INTO orchestration_v2_projection_threads VALUES (?, NULL, ?)",
            (stale_iso, json.dumps({"worktreePath": str(risky), "updatedAt": stale_iso})),
        )
        con.commit()
        con.close()
        orig_last_activity = sweep_mod.last_activity
        calls = 0

        def snooze_during_recheck_git(p: Path) -> float:
            nonlocal calls
            res = orig_last_activity(p)
            if p == risky:
                calls += 1
                if calls >= 2:
                    c2 = sqlite3.connect(str(special_db))
                    c2.execute(
                        "UPDATE orchestration_v2_projection_threads SET payload_json = ?",
                        (json.dumps({"worktreePath": str(risky), "updatedAt": stale_iso, "snoozedUntil": future_snooze}),),
                    )
                    c2.commit()
                    c2.close()
            return res

        sweep_mod.last_activity = snooze_during_recheck_git
        try:
            report, _ = self.run_sweep(apply=True, days=10)
        finally:
            sweep_mod.last_activity = orig_last_activity
        self.assertIn("active in the last 10 days", self.line(report, f"{risky}\t"))
        self.assertTrue(risky.exists())
        self.assertTrue((risky / "node_modules").exists())

        # 6. Inaccessible DB parent directory fails closed instead of raising PermissionError or returning {}
        if os.geteuid() != 0:
            locked_dir = self.tmp / "locked-t3-dir"
            locked_dir.mkdir()
            (locked_dir / "statev2.sqlite").write_bytes(special_db.read_bytes())
            locked_dir.chmod(0)
            self.addCleanup(locked_dir.chmod, 0o700)
            os.environ["AGENT_SWEEP_T3_DB"] = str(locked_dir / "statev2.sqlite")
            report, _ = self.run_sweep(apply=True, days=10)
            self.assertIn("T3 thread activity could not be checked", self.line(report, "t3\twarning"))
            self.assertTrue(risky.exists())
            self.assertTrue((risky / "node_modules").exists())


if __name__ == "__main__":
    unittest.main()
