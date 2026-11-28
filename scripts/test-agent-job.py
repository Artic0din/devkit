#!/usr/bin/env python3
"""Offline tests for scripts/agent-job, the agent xcodebuild shim and the Claude session hook,
using a fake colima that creates and deletes real profile folders in a throwaway COLIMA_HOME."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
JOB = HERE / "agent-job"
SHIM = HERE / "agent-bin" / "xcodebuild"
SESSION_HOOK = HERE.parent / "hooks" / "claude-session-env.sh"
LOADER = importlib.machinery.SourceFileLoader("agent_job", str(JOB))
SPEC = importlib.util.spec_from_loader("agent_job", LOADER)
assert SPEC
job_mod = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(job_mod)

# Mimics colima 0.10: start makes the profile, VM and disk folders plus a _store state file;
# delete --data removes the folders but leaves the state file.
FAKE_COLIMA = r"""#!/bin/sh
echo "$*" >> "$COLIMA_HOME/calls.log"
verb=$1 p=$2
case $verb in
  start)
    mkdir -p "$COLIMA_HOME/$p" "$COLIMA_HOME/_lima/colima-$p" "$COLIMA_HOME/_lima/_disks/colima-$p" "$COLIMA_HOME/_store"
    echo '{}' > "$COLIMA_HOME/_store/colima-$p.json"
    if [ -n "$FAKE_COLIMA_DAEMON" ]; then
      sleep 60 </dev/null >/dev/null 2>&1 &
      echo $! > "$COLIMA_HOME/daemon-pid"
    fi
    [ -n "$FAKE_COLIMA_START_SLEEP" ] && touch "$COLIMA_HOME/starting" && sleep "$FAKE_COLIMA_START_SLEEP"
    exit "${FAKE_COLIMA_START_EXIT:-0}" ;;
  delete)
    [ -n "$FAKE_COLIMA_DELETE_FAILS" ] && exit 1
    rm -rf "$COLIMA_HOME/$p" "$COLIMA_HOME/_lima/colima-$p"
    [ "$3" = "--data" ] && rm -rf "$COLIMA_HOME/_lima/_disks/colima-$p"
    exit 0 ;;
esac
exit 2
"""


def sh(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


def wait_for(path: Path, timeout: float = 10) -> None:
    end = time.time() + timeout
    while not path.exists():
        if time.time() > end:
            raise AssertionError(f"{path} never appeared")
        time.sleep(0.05)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class AgentJobTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.colima = self.tmp / "colima-home"
        self.scratch = self.tmp / "scratch"
        fake = self.tmp / "colima"
        fake.write_text(FAKE_COLIMA)
        fake.chmod(0o755)
        self.env = {**os.environ, "COLIMA_HOME": str(self.colima), "AGENT_SCRATCH_ROOT": str(self.scratch),
                    "AGENT_JOB_COLIMA": str(fake)}
        for k in ("FAKE_COLIMA_START_EXIT", "FAKE_COLIMA_START_SLEEP", "FAKE_COLIMA_DELETE_FAILS", "AGENT_JOB_DIR"):
            self.env.pop(k, None)
        # The user's own resources: the default profile and a profile no job recorded.
        self.foreign = [self.colima / "default", self.colima / "_lima" / "colima", self.colima / "_lima" / "_disks" / "colima",
                        self.colima / "agent-job-other", self.colima / "_lima" / "colima-agent-job-other"]
        for d in self.foreign:
            d.mkdir(parents=True)
            (d / "keep").write_text("x")
        self.patch_env()

    def patch_env(self) -> None:
        saved = {k: os.environ.get(k) for k in ("COLIMA_HOME", "AGENT_SCRATCH_ROOT", "AGENT_JOB_COLIMA")}
        os.environ.update({k: self.env[k] for k in saved})

        def restore() -> None:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(restore)

    def job(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(JOB), "run", *args], capture_output=True, text=True,
                              env=env or self.env, timeout=60)

    def spawn(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, "-I", str(JOB), "run", *args], env=self.env, stderr=subprocess.DEVNULL)

    def calls(self) -> List[str]:
        log = self.colima / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def assert_clean(self) -> None:
        jobs = self.scratch / "agent-job"
        self.assertEqual(list(jobs.iterdir()) if jobs.exists() else [], [], "job folder left behind")
        left = [p for p in self.colima.rglob("*agent-job-*") if "agent-job-other" not in str(p)]
        self.assertEqual(left, [], "job profile, disk or state file left behind")
        for d in self.foreign:
            self.assertTrue((d / "keep").exists(), f"{d} was touched")

    def sweep(self, apply: bool) -> str:
        buf = io.StringIO()

        def emit(kind: str, verdict: str, path: str, why: str, kb: int = 0) -> None:
            print(f"{kind}\t{verdict}\t{path}\t{why}", file=buf)
        job_mod.sweep_jobs(self.scratch / "agent-job", apply, emit)
        return buf.getvalue()

    def test_success_records_routes_and_removes_everything(self) -> None:
        out = self.tmp / "seen.json"
        script = ('import json, os, shutil, sys; json.dump({k: os.environ.get(k) for k in '
                  '("AGENT_JOB_ID", "AGENT_JOB_DIR", "TMPDIR", "DOCKER_HOST", "DOCKER_CONTEXT")} | '
                  '{"xcodebuild": shutil.which("xcodebuild"), "record": json.load(open(os.environ["AGENT_JOB_DIR"] + "/job.json"))}, '
                  'open(sys.argv[1], "w")); open(os.environ["TMPDIR"] + "/x", "w").write("x")')
        env = {**self.env, "DOCKER_CONTEXT": "desktop-linux"}
        done = self.job("--label", "My CI Run!", "--colima", "--colima-arg=--cpu=2", "--", sys.executable, "-c",
                        script, str(out), env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        seen = json.loads(out.read_text())
        job_id = seen["AGENT_JOB_ID"]
        self.assertRegex(job_id, r"^my-ci-run-[0-9a-f]{8}$")
        profile = f"agent-job-{job_id}"
        self.assertEqual(seen["record"]["colima_profile"], profile)
        self.assertEqual(seen["AGENT_JOB_DIR"], str(self.scratch / "agent-job" / job_id))
        self.assertEqual(seen["TMPDIR"], seen["AGENT_JOB_DIR"] + "/tmp")
        self.assertEqual(seen["DOCKER_HOST"], f"unix://{self.colima / profile / 'docker.sock'}")
        self.assertIsNone(seen["DOCKER_CONTEXT"])
        self.assertEqual(seen["xcodebuild"], str(SHIM))
        self.assertEqual(self.calls(), [f"start {profile} --activate=false --cpu=2", f"delete {profile} --data --force"])
        self.assert_clean()

    def test_failing_command_keeps_its_exit_code_and_cleans_up(self) -> None:
        done = self.job("--colima", "--", "sh", "-c", "exit 7")
        self.assertEqual(done.returncode, 7)
        self.assert_clean()

    def test_job_without_colima_never_calls_colima(self) -> None:
        done = self.job("--", "sh", "-c", 'test -d "$AGENT_JOB_DIR"')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.calls(), [])
        self.assert_clean()

    def test_failed_colima_start_removes_the_partial_profile(self) -> None:
        marker = self.tmp / "ran"
        done = self.job("--colima", "--", "touch", str(marker), env={**self.env, "FAKE_COLIMA_START_EXIT": "1"})
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("colima start", done.stderr)
        self.assertFalse(marker.exists(), "command ran without its profile")
        self.assert_clean()

    def test_signals_stop_the_command_and_clean_up(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(sig=sig):
                pid_file = self.tmp / f"pid-{sig}"
                runner = self.spawn("--colima", "--", "sh", "-c", f'echo $$ > "{pid_file}"; exec sleep 60')
                wait_for(pid_file)
                command_pid = int(pid_file.read_text())
                runner.send_signal(sig)
                self.assertEqual(runner.wait(timeout=30), 128 + sig)
                self.assertFalse(alive(command_pid), "command outlived the job")
                self.assert_clean()

    def test_command_ignoring_sigterm_is_killed_after_the_grace_period(self) -> None:
        pid_file = self.tmp / "pid"
        self.env["AGENT_JOB_STOP_GRACE_S"] = "1"
        runner = self.spawn("--", "sh", "-c", f'trap "" TERM; echo $$ > "{pid_file}"; while :; do sleep 0.1; done')
        wait_for(pid_file)
        runner.send_signal(signal.SIGTERM)
        self.assertEqual(runner.wait(timeout=20), 143)
        self.assertFalse(alive(int(pid_file.read_text())))
        self.assert_clean()

    def test_sweep_waits_for_orphaned_colima_start(self) -> None:
        self.env["FAKE_COLIMA_START_SLEEP"] = "1"
        self.env["FAKE_COLIMA_DAEMON"] = "1"
        runner = self.spawn("--colima", "--", "true")
        wait_for(self.colima / "starting")
        daemon = int((self.colima / "daemon-pid").read_text())
        self.addCleanup(os.kill, daemon, signal.SIGTERM)
        runner.kill()
        runner.wait(timeout=10)
        self.assertIn("job is running", self.sweep(apply=True))
        deadline = time.monotonic() + 10
        while "job is running" in self.sweep(apply=False):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        self.sweep(apply=True)
        self.assert_clean()

    def test_stalled_git_check_preserves_package_checkout(self) -> None:
        repo = self.tmp / "SourcePackages/checkouts/Lib"
        repo.mkdir(parents=True)
        sh(repo, "git", "init", "-q")
        def stall(*args, timeout, **kwargs):
            self.assertGreater(timeout, 0)
            raise subprocess.TimeoutExpired(args, timeout)
        with patch.object(subprocess, "run", side_effect=stall):
            self.assertEqual(job_mod.checkout_inside(self.tmp), "SourcePackages/checkouts/Lib")

    def test_interrupted_record_update_preserves_previous_record(self) -> None:
        path, fd, record = job_mod.new_job("record", True)
        try:
            with patch.object(os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    job_mod.teardown(path, record)
            self.assertEqual(job_mod.read_record(path), record)
            self.assertTrue(job_mod.teardown(path, record)[0])
        finally:
            os.close(fd)

    def test_job_is_private_with_a_permissive_umask(self) -> None:
        done = self.job("--", sys.executable, "-c",
                        'import os;print(oct(os.stat(os.environ["AGENT_JOB_DIR"]).st_mode & 0o777))')
        self.assertEqual(done.stdout.strip(), "0o700")

    def test_indeterminate_session_scan_preserves_job(self) -> None:
        (self.tmp / "command.sid").write_text("42")
        with patch.object(os, "getsid", side_effect=ProcessLookupError):
            self.assertTrue(job_mod.command_session_active(self.tmp))

    def test_worker_without_lock_keeps_job_active(self) -> None:
        worker_file = self.tmp / "worker"
        script = ("import os,subprocess,sys,time; "
                  "p=subprocess.Popen(['sleep','30'],close_fds=True,preexec_fn=os.setpgrp); "
                  "open(sys.argv[1],'w').write(str(p.pid)+' '+str(os.getpid())); time.sleep(30)")
        runner = self.spawn("--", sys.executable, "-c", script, str(worker_file))
        wait_for(worker_file)
        worker, leader = map(int, worker_file.read_text().split())
        try:
            runner.kill()
            runner.wait(timeout=10)
            os.kill(leader, signal.SIGKILL)
            deadline = time.monotonic() + 5
            while alive(leader) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertIn("job is running", self.sweep(apply=True))
        finally:
            os.kill(worker, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while "job is running" in self.sweep(apply=False):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        self.sweep(apply=True)
        self.assert_clean()

    def test_package_edits_and_local_commits_survive_sweep(self) -> None:
        source = self.tmp / "remote"
        source.mkdir()
        sh(source, "git", "init", "-q")
        (source / "code").write_text("upstream")
        sh(source, "git", "add", "code")
        sh(source, "git", "commit", "-qm", "upstream")
        for commit in (False, True):
            with self.subTest(commit=commit):
                script = ('repo="$AGENT_JOB_DIR/SourcePackages/checkouts/Lib"; git clone -q "$1" "$repo"; '
                          'echo local > "$repo/code"')
                if commit:
                    script += '; git -C "$repo" -c user.name=t -c user.email=t@t commit -qam local'
                done = self.job("--", "sh", "-ec", script, "sh", str(source))
                self.assertNotEqual(done.returncode, 0)
                self.sweep(apply=True)
                files = list((self.scratch / "agent-job").glob("*/SourcePackages/checkouts/Lib/code"))
                self.assertEqual(len(files), 1 + int(commit))
                self.assertTrue(all(file.read_text() == "local\n" for file in files))

    def test_ignored_package_file_survives_cleanup(self) -> None:
        script = ('repo="$AGENT_JOB_DIR/SourcePackages/checkouts/Lib"; git init -q "$repo"; '
                  'echo .env >> "$repo/.git/info/exclude"; touch "$repo/.env"')
        done = self.job("--", "sh", "-ec", script)
        self.assertNotEqual(done.returncode, 0)
        [job_dir] = (self.scratch / "agent-job").iterdir()
        self.sweep(apply=True)
        self.assertTrue((job_dir / "SourcePackages/checkouts/Lib/.env").is_file())

    def test_cancel_at_successful_startup_handoff_skips_command(self) -> None:
        marker = self.tmp / "spawned"
        driver = """
import os, runpy, signal, subprocess, sys
module = runpy.run_path(sys.argv[1])
class StartupExit(int):
    def __ne__(self, other):
        os.kill(os.getpid(), signal.SIGTERM)
        return super().__ne__(other)
class ObservedProcess(subprocess.Popen):
    def __init__(self, args, **kwargs):
        if args[-1:] == ["true"]:
            open(sys.argv[2], "w").close()
        super().__init__(args, **kwargs)
    def wait(self, *args, **kwargs):
        result = super().wait(*args, **kwargs)
        if self.args[:1] == ["/bin/bash"]:
            if sys.argv[3] == "pending":
                os.kill(os.getpid(), signal.SIGTERM)
                return result
            return StartupExit(result)
        return result
subprocess.Popen = ObservedProcess
sys.exit(module["run"]("handoff", True, [], ["true"]))
"""
        for timing in ("pending", "handoff"):
            with self.subTest(timing=timing):
                runner = subprocess.run([sys.executable, "-c", driver, str(JOB), str(marker), timing], env=self.env)
                self.assertEqual(runner.returncode, 143)
                self.assertFalse(marker.exists(), "command spawned after cancellation")
                self.assert_clean()

    def test_cancel_during_colima_start_cleans_up(self) -> None:
        marker = self.tmp / "ran"
        self.env["FAKE_COLIMA_START_SLEEP"] = "30"
        runner = self.spawn("--colima", "--", "touch", str(marker))
        wait_for(self.colima / "starting")
        runner.send_signal(signal.SIGTERM)
        self.assertEqual(runner.wait(timeout=30), 143)
        self.assertFalse(marker.exists())
        self.assert_clean()

    def test_killed_job_is_recovered_by_the_sweep_only_once_inactive(self) -> None:
        pid_file = self.tmp / "pid"
        runner = self.spawn("--colima", "--", "sh", "-c", f'echo $$ > "{pid_file}"; exec sleep 60')
        wait_for(pid_file)
        command_pid = int(pid_file.read_text())
        runner.kill()  # SIGKILL: no cleanup runs
        runner.wait(timeout=10)
        [job_dir] = list((self.scratch / "agent-job").iterdir())
        profile = f"agent-job-{job_dir.name}"
        self.assertTrue((self.colima / profile).exists())
        # The orphaned command still holds the job's lock, so the job counts as running.
        self.assertIn("keep\t" + str(job_dir) + "\tjob is running", self.sweep(apply=True))
        self.assertTrue(job_dir.exists())
        os.kill(command_pid, signal.SIGKILL)
        end = time.time() + 10
        while alive(command_pid) and time.time() < end:
            time.sleep(0.05)
        report = self.sweep(apply=False)
        self.assertIn(f"remove\t{job_dir}\tjob ended without cleanup (colima {profile})", report)
        self.assertTrue(job_dir.exists(), "report mode removed the job")
        self.assertTrue((self.colima / profile).exists(), "report mode removed the profile")
        self.sweep(apply=True)
        self.assertIn(f"delete {profile} --data --force", self.calls())
        self.assert_clean()

    def test_concurrent_jobs_get_their_own_resources(self) -> None:
        runners, pids = [], []
        for i in range(3):
            pid_file = self.tmp / f"pid{i}"
            pids.append(pid_file)
            runners.append(self.spawn("--colima", "--", "sh", "-c",
                                      f'echo "$AGENT_JOB_ID $DOCKER_HOST" > "{pid_file}.env"; echo $$ > "{pid_file}"; exec sleep 60'))
        for pid_file in pids:
            wait_for(pid_file)
            wait_for(Path(f"{pid_file}.env"))
        ids = {Path(f"{p}.env").read_text().split()[0] for p in pids}
        hosts = {Path(f"{p}.env").read_text().split()[1] for p in pids}
        self.assertEqual((len(ids), len(hosts)), (3, 3))
        report = self.sweep(apply=True)
        self.assertEqual(report.count("job is running"), 3, report)
        os.kill(int(pids[0].read_text()), signal.SIGTERM)  # one job ends; the others keep running
        self.assertEqual(runners[0].wait(timeout=30), 143)
        self.assertEqual(len(list((self.scratch / "agent-job").iterdir())), 2)
        for r in runners[1:]:
            r.terminate()
            r.wait(timeout=30)
        self.assert_clean()

    def test_sweep_preserves_unknown_foreign_and_default_records(self) -> None:
        jobs = self.scratch / "agent-job"
        no_record = jobs / "half-made"
        no_record.mkdir(parents=True)
        (no_record / "job.lock").write_text("")
        default = jobs / "points-at-default"
        default.mkdir()
        (default / "job.lock").write_text("")
        (default / "job.json").write_text(json.dumps({"id": default.name, "colima_profile": "default"}))
        other = jobs / "points-at-other"
        other.mkdir()
        (other / "job.lock").write_text("")
        (other / "job.json").write_text(json.dumps({"id": other.name, "colima_profile": "agent-job-other"}))
        renamed = jobs / "renamed"
        renamed.mkdir()
        (renamed / "job.lock").write_text("")
        (renamed / "job.json").write_text(json.dumps({"id": "something-else", "colima_profile": None}))
        (jobs / "link").symlink_to(self.tmp)
        report = self.sweep(apply=True)
        for d in (no_record, default, other, renamed):
            self.assertIn(f"keep\t{d}\tno valid job record", report)
            self.assertTrue(d.exists())
        self.assertIn(f"keep\t{jobs / 'link'}\tnot a job folder", report)
        self.assertEqual(self.calls(), [])
        for d in self.foreign:
            self.assertTrue((d / "keep").exists())

    def test_failed_colima_delete_keeps_the_record_for_a_retry(self) -> None:
        done = self.job("--colima", "--", "true", env={**self.env, "FAKE_COLIMA_DELETE_FAILS": "1"})
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("cleanup incomplete", done.stderr)
        [job_dir] = list((self.scratch / "agent-job").iterdir())
        self.assertIsNotNone(job_mod.read_record(job_dir))
        self.sweep(apply=True)  # the fake colima deletes normally now
        self.assert_clean()

    def test_git_checkout_with_uncommitted_files_in_job_scratch_is_kept(self) -> None:
        script = 'git init -q "$AGENT_JOB_DIR/repo" && echo work > "$AGENT_JOB_DIR/repo/wip.txt"'
        done = self.job("--colima", "--", "sh", "-c", script)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Git checkout at repo", done.stderr)
        [job_dir] = list((self.scratch / "agent-job").iterdir())
        self.assertEqual((job_dir / "repo" / "wip.txt").read_text(), "work\n")
        self.assertEqual(list(self.colima.glob(f"agent-job-{job_dir.name}")), [], "profile should still be removed")

    def test_owned_package_checkouts_clean_up_while_other_checkouts_are_kept(self) -> None:
        script = 'git init -q "$AGENT_JOB_DIR/DerivedData/SourcePackages/checkouts/Lib"'
        done = self.job("--", "sh", "-ec", script)
        self.assertEqual(done.returncode, 0, done.stderr)
        done = self.job("--", "sh", "-ec", script + '; git init -q "$AGENT_JOB_DIR/mine"')
        self.assertIn("Git checkout at mine", done.stderr)

    def test_linked_package_worktree_survives(self) -> None:
        source = self.tmp / "source"
        source.mkdir()
        sh(source, "git", "init", "-q")
        sh(source, "git", "commit", "--allow-empty", "-qm", "initial")
        script = 'git -C "$1" worktree add -q --detach "$AGENT_JOB_DIR/SourcePackages/checkouts/Lib"'
        done = self.job("--", "sh", "-ec", script, "sh", str(source))
        self.assertNotEqual(done.returncode, 0)
        [job_dir] = (self.scratch / "agent-job").iterdir()
        self.assertTrue((job_dir / "SourcePackages/checkouts/Lib/.git").is_file())

    def test_retained_job_is_never_counted_as_removed(self) -> None:
        self.job("--", "sh", "-ec", 'git init -q "$AGENT_JOB_DIR/mine"')
        for apply in (False, True):
            events = []
            count = job_mod.sweep_jobs(self.scratch / "agent-job", apply, lambda *row: events.append(row))
            self.assertEqual(count, 0)
            self.assertNotIn("remove", [row[1] for row in events])

    def test_recovery_uses_the_original_colima_home(self) -> None:
        self.job("--colima", "--", "true", env={**self.env, "FAKE_COLIMA_DELETE_FAILS": "1"})
        [job_dir] = (self.scratch / "agent-job").iterdir()
        profile = "agent-job-" + job_dir.name
        other = self.tmp / "other"
        (other / profile).mkdir(parents=True)
        os.environ["COLIMA_HOME"] = str(other)
        self.sweep(apply=True)
        self.assertTrue((other / profile).is_dir())
        self.assert_clean()

    def test_symlinked_jobs_root_is_preserved(self) -> None:
        root = self.scratch / "agent-job"
        target = self.tmp / "outside"
        self.scratch.mkdir()
        target.mkdir()
        root.symlink_to(target)
        orphan = target / "job-12345678"
        orphan.mkdir()
        (orphan / "job.lock").touch()
        (orphan / "job.json").write_text(json.dumps({"id": orphan.name, "colima_profile": None}))
        self.sweep(apply=True)
        self.assertTrue(orphan.exists())
        self.assertNotEqual(self.job("--", "true").returncode, 0)

    def test_signal_during_command_registration_stops_child(self) -> None:
        driver = """
import os, runpy, signal, subprocess, sys
module = runpy.run_path(sys.argv[1])
original = subprocess.Popen
def interrupt(*args, **kwargs):
    proc = original(*args, **kwargs)
    if kwargs.get("start_new_session"):
        open(sys.argv[2], "w").write(str(proc.pid))
        os.kill(os.getpid(), signal.SIGTERM)
    return proc
subprocess.Popen = interrupt
sys.exit(module["run"]("signal", False, [], ["sleep", "5"]))
"""
        pidfile = self.tmp / "child-pid"
        runner = subprocess.run([sys.executable, "-c", driver, str(JOB), str(pidfile)], env=self.env)
        self.assertEqual(runner.returncode, 143)
        self.assertFalse(alive(int(pidfile.read_text())))

    def test_colima_args_cannot_pick_another_profile(self) -> None:
        for bad in ("-p", "--profile=default", "--activate"):
            done = self.job("--colima", f"--colima-arg={bad}", "--", "true")
            self.assertEqual(done.returncode, 2, bad)
        self.assertEqual(self.calls(), [])


class XcodebuildShimTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        real = self.tmp / "real-xcodebuild"
        real.write_text('#!/bin/sh\nfor a in "$@"; do echo "$a"; done\n')
        real.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if k != "AGENT_JOB_DIR"}
        self.env.update(AGENT_XCODEBUILD_REAL=str(real), AGENT_SCRATCH_ROOT=str(self.tmp / "scratch"))
        self.repo = self.tmp / "App"
        self.repo.mkdir()
        sh(self.repo, "git", "init", "-q")

    def shim(self, *args: str, cwd: Path | None = None, **env: str) -> List[str]:
        done = subprocess.run([str(SHIM), *args], cwd=cwd or self.repo, capture_output=True, text=True,
                              env={**self.env, **env}, check=True)
        return done.stdout.splitlines()

    def test_non_build_commands_pass_through(self) -> None:
        self.assertEqual(self.shim("-version"), ["-version"])
        self.assertEqual(self.shim("-list", "-project", "A.xcodeproj"), ["-list", "-project", "A.xcodeproj"])

    def test_build_in_a_worktree_goes_to_scratch_outside_it(self) -> None:
        args = self.shim("-scheme", "App", "build", cwd=self.repo)
        self.assertEqual(args[0], "-derivedDataPath")
        derived = Path(args[1])
        self.assertEqual(derived.parent.parent, self.tmp / "scratch" / "xcode")
        self.assertRegex(derived.parent.name, r"^App-[0-9a-f]{8}$")
        self.assertEqual(derived.name, "DerivedData")
        self.assertNotIn(str(self.repo), str(derived))
        self.assertEqual(args[2:], ["-scheme", "App", "build"])
        nested = self.repo / "sub"
        nested.mkdir()
        self.assertEqual(self.shim("-scheme", "App", cwd=nested)[1], str(derived), "same worktree, same folder")

    def test_build_inside_a_job_uses_the_job_folder(self) -> None:
        args = self.shim("test", "-scheme", "App", AGENT_JOB_DIR="/jobs/x")
        self.assertEqual(args[:2], ["-derivedDataPath", "/jobs/x/DerivedData"])

    def test_explicit_derived_data_path_is_kept(self) -> None:
        self.assertEqual(self.shim("-scheme", "App", "-derivedDataPath", "/elsewhere"),
                         ["-scheme", "App", "-derivedDataPath", "/elsewhere"])

    def test_explicit_build_outputs_in_worktree_report_the_required_path(self) -> None:
        for flag in ("-derivedDataPath", "-clonedSourcePackagesDirPath"):
            with self.subTest(flag=flag):
                done = subprocess.run([str(SHIM), "-scheme", "App", flag, ".build/output"],
                                      cwd=self.repo, env=self.env, text=True, capture_output=True)
                self.assertNotEqual(done.returncode, 0)
                self.assertIn(flag, done.stderr)
                self.assertIn(str(self.tmp / "scratch"), done.stderr)
                self.assertFalse(done.stdout)

    def test_outputs_in_explicit_project_or_workspace_are_protected(self) -> None:
        for flag, bundle, output in (("-project", "App.xcodeproj", "-derivedDataPath"),
                                     ("-workspace", "App.xcworkspace", "-clonedSourcePackagesDirPath")):
            with self.subTest(flag=flag):
                project = self.repo / bundle
                project.mkdir()
                done = subprocess.run([SHIM, flag, project, "-scheme", "App", output, self.repo / "out"],
                                      cwd=self.tmp, env=self.env, text=True, capture_output=True)
                self.assertNotEqual(done.returncode, 0)
                self.assertIn(output, done.stderr)

    def test_session_hook_puts_the_shim_first_on_path_once(self) -> None:
        env_file = self.tmp / "claude-env"
        subprocess.run(["bash", str(SESSION_HOOK)], env={**self.env, "CLAUDE_ENV_FILE": str(env_file)}, check=True)
        subprocess.run(["bash", str(SESSION_HOOK)], env={**self.env, "CLAUDE_ENV_FILE": str(env_file)}, check=True)
        out = subprocess.run(["bash", "-c", f'. "{env_file}"; echo "$PATH"; command -v xcodebuild'], capture_output=True,
                             text=True, env={**self.env, "PATH": "/usr/bin:/bin"}, check=True).stdout.splitlines()
        self.assertEqual(out[0], f"{SHIM.parent}:/usr/bin:/bin")
        self.assertEqual(out[1], str(SHIM))
        late = subprocess.check_output(["bash", "-c", '. "$1"; command -v xcodebuild', "bash", env_file],
                                       env={**self.env, "PATH": f"/usr/bin:/bin:{SHIM.parent}"}, text=True)
        self.assertEqual(late.strip(), str(SHIM))
        self.assertEqual(subprocess.run(["bash", str(SESSION_HOOK)], env=self.env).returncode, 0, "no env file is fine")


if __name__ == "__main__":
    unittest.main()
