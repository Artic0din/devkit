#!/usr/bin/env python3
"""Offline tests for scripts/env-board.py against fake gh and git output."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SPEC = importlib.util.spec_from_file_location("env_board", Path(__file__).with_name("env-board.py"))
assert SPEC and SPEC.loader
board = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(board)

PASS = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"}
FAIL = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "FAILURE"}
RUNNING = {"__typename": "CheckRun", "status": "IN_PROGRESS", "conclusion": ""}
LOG = """# Environment log

## Decisions

| Date | Decision | Why | Where |
|---|---|---|---|
| 2026-09-18 | Older decision | Old reason | chat |
| 2026-10-25 | Newer decision | New reason | [#61](https://github.com/o/r/pull/61) |

## Work not on GitHub

| Date | Item | Status | Why | Next step |
|---|---|---|---|---|
| 2026-10-17 | Update the installed checkout | waiting on you | Agents read it | Switch it to `main` |
| 2026-10-20 | Removed a local schedule | done | Nothing used it | |
"""


def pr(number: int, merge: str = "CLEAN", checks: Optional[List[Dict[str, Any]]] = None, draft: bool = False) -> Dict[str, Any]:
    return {"number": number, "title": f"PR {number}", "url": f"https://github.com/o/r/pull/{number}",
            "isDraft": draft, "mergeStateStatus": merge, "statusCheckRollup": [PASS] if checks is None else checks}


def issue(number: int, *labels: str) -> Dict[str, Any]:
    return {"number": number, "title": f"Issue {number}", "url": f"https://github.com/o/r/issues/{number}",
            "labels": [{"name": name} for name in labels]}


IN_SYNC = {"path": "/x", "note": "", "branch": "main", "behind": 0, "ahead": 0, "dirty": 0, "in_sync": True}


class FakeRunner:
    def __init__(self, prs: List[Dict[str, Any]], issues: List[Dict[str, Any]], merged: List[Dict[str, Any]],
                 fetch_fails: bool = False) -> None:
        self.prs, self.issues, self.merged, self.fetch_fails = prs, issues, merged, fetch_fails
        self.calls: List[List[str]] = []

    def __call__(self, args: Sequence[str], cwd: Optional[Path]) -> str:
        args = list(args)
        self.calls.append(args)
        if args[:3] == ["gh", "pr", "list"]:
            return json.dumps(self.merged if "merged" in args else self.prs)
        if args[:3] == ["gh", "issue", "list"]:
            return json.dumps(self.issues)
        if args[:2] == ["git", "fetch"]:
            if self.fetch_fails:
                raise RuntimeError("offline")
            return ""
        if args[:2] == ["git", "rev-parse"]:
            return "chore/old-branch\n"
        if args[:2] == ["git", "rev-list"]:
            return "14\t0\n"
        if args[:2] == ["git", "status"]:
            return " M AGENTS.MD\n?? new-file\n"
        raise AssertionError(f"unexpected command {args}")


class ChecksAndLanes(unittest.TestCase):
    def test_check_state_reads_both_check_shapes(self) -> None:
        self.assertEqual(board.check_state([]), "passed")
        self.assertEqual(board.check_state([PASS, {"__typename": "StatusContext", "state": "SUCCESS"}]), "passed")
        self.assertEqual(board.check_state([PASS, RUNNING]), "running")
        self.assertEqual(board.check_state([{"__typename": "StatusContext", "state": "PENDING"}]), "running")
        self.assertEqual(board.check_state([RUNNING, FAIL]), "failing")
        self.assertEqual(board.check_state([{"__typename": "StatusContext", "state": "ERROR"}]), "failing")

    def test_pull_requests_land_in_the_right_lane(self) -> None:
        cases = [
            (pr(1), "needs_you"),
            (pr(2, draft=True), "in_progress"),
            (pr(3, checks=[FAIL]), "blocked"),
            (pr(4, merge="DIRTY"), "blocked"),
            (pr(5, merge="UNSTABLE", checks=[RUNNING]), "in_progress"),
            (pr(6, merge="BEHIND"), "in_progress"),
            (pr(7, merge="BLOCKED"), "in_progress"),
            (pr(8, merge="UNKNOWN"), "in_progress"),
            (pr(9, merge="HAS_HOOKS"), "needs_you"),
            (pr(10, merge="UNSTABLE"), "in_progress"),
            (pr(11, checks=[{"__typename": "StatusContext", "state": "EXPECTED"}]), "in_progress"),
            (pr(12, checks=[{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "STALE"}]), "needs_you"),
        ]
        for data, lane in cases:
            with self.subTest(number=data["number"]):
                self.assertEqual(board.pr_item(data)["lane"], lane)

    def test_issue_reason_follows_labels(self) -> None:
        self.assertEqual(board.issue_item(issue(1, "bug", "ready-for-human"))["reason"], "Bug. Ready for a person to pick up")
        self.assertEqual(board.issue_item(issue(2, "documentation", "needs-info"))["reason"], "Docs. Waiting for more information")
        self.assertEqual(board.issue_item(issue(3))["reason"], "Issue. Not started")


class WhyAndLog(unittest.TestCase):
    def test_why_prefers_the_why_section(self) -> None:
        body = "## What changed\n\nMoved files.\n\n## Why\n\nGitHub does not redirect\nreferences.\n\n## Risk\n\nLow."
        self.assertEqual(board.why_of(body), "GitHub does not redirect references.")

    def test_why_falls_back_to_the_first_paragraph(self) -> None:
        self.assertEqual(board.why_of("<!-- hidden -->\nThe hook ran on every push.\n\n- detail"), "The hook ran on every push.")
        self.assertEqual(board.why_of(None), "")
        self.assertEqual(board.why_of("## Why\r\n\r\nShort reason.\r\n\r\n- bullet"), "Short reason.")
        self.assertEqual(board.why_of("**Expected:** paths stay inside."), "Expected: paths stay inside.")
        long = board.why_of("word " * 100)
        self.assertLessEqual(len(long), 241)
        self.assertTrue(long.endswith("…"))

    def test_parse_log_reads_both_tables(self) -> None:
        log = board.parse_log(LOG)
        self.assertEqual([row["decision"] for row in log["decisions"]], ["Older decision", "Newer decision"])
        self.assertEqual(log["work"][0]["next step"], "Switch it to `main`")
        self.assertEqual(log["work"][1]["status"], "done")

    def test_parse_log_keeps_a_blank_last_cell_written_without_a_space(self) -> None:
        log = board.parse_log("## Work not on GitHub\n\n| Date | Item | Status | Next step |\n|---|---|---|---|\n| 2026-10-25 | x | done ||\n")
        self.assertEqual(log["work"][0]["next step"], "")

    def test_parse_log_rejects_unknown_status_and_bad_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "line 5: status must be one of"):
            board.parse_log("## Work not on GitHub\n\n| Date | Item | Status |\n|---|---|---|\n| 2026-10-25 | x | someday |\n")
        with self.assertRaisesRegex(ValueError, "line 5: expected 3 cells, found 2"):
            board.parse_log("## Decisions\n\n| Date | Decision | Why |\n|---|---|---|\n| 2026-10-25 | x |\n")


class BoardAndPage(unittest.TestCase):
    def build(self) -> Dict[str, Any]:
        prs = [pr(61), pr(24, merge="DIRTY")]
        issues = [issue(47, "enhancement"), issue(60, "bug")]
        merged = [{"number": 55, "title": "Remove CoS", "url": "https://github.com/o/r/pull/55",
                   "mergedAt": "2026-10-12T22:30:00Z", "body": "## Why\n\nYou chose P3 Stack."},
                  {"number": 2, "title": "Before the rebuild", "url": "https://github.com/o/r/pull/2",
                   "mergedAt": "2026-09-17T13:00:00Z", "body": ""}]
        return board.build_board(prs, issues, merged, board.parse_log(LOG), IN_SYNC)

    def test_github_and_chat_items_share_lanes(self) -> None:
        built = self.build()
        self.assertEqual([item["ref"] for item in built["lanes"]["needs_you"]], ["#61", "chat"])
        self.assertEqual([item["ref"] for item in built["lanes"]["outstanding"]], ["#60", "#47"])
        self.assertEqual(built["lanes"]["needs_you"][1]["reason"], "Switch it to `main`")
        self.assertEqual(built["do_next"]["ref"], "#61")

    def test_changes_mix_merged_prs_and_done_chat_rows_newest_first(self) -> None:
        changes = self.build()["changes"]
        self.assertEqual([(item["ref"], item["date"]) for item in changes], [("chat", "2026-10-20"), ("#55", "2026-10-13")])
        self.assertEqual(changes[1]["reason"], "You chose P3 Stack.")

    def test_do_next_falls_through_to_blocked_then_outstanding(self) -> None:
        empty = {"decisions": [], "work": []}
        self.assertEqual(board.build_board([pr(3, checks=[FAIL])], [issue(9)], [], empty, IN_SYNC)["do_next"]["ref"], "#3")
        self.assertEqual(board.build_board([], [issue(9)], [], empty, IN_SYNC)["do_next"]["ref"], "#9")
        self.assertIsNone(board.build_board([], [], [], empty, IN_SYNC)["do_next"])

    def test_decisions_show_where_they_were_made(self) -> None:
        page = board.render(self.build(), "o/r", datetime(2026, 10, 25, tzinfo=board.MELBOURNE), "2026-09-18")
        self.assertIn('Where: <a href="https://github.com/o/r/pull/61">#61</a>', page)
        self.assertIn("Where: chat", page)

    def test_github_titles_never_become_links(self) -> None:
        hostile = dict(pr(1), title="Fix [login](https://evil.example/phish)")
        built = board.build_board([hostile], [], [], {"decisions": [], "work": []}, IN_SYNC)
        page = board.render(built, "o/r", datetime(2026, 10, 25, tzinfo=board.MELBOURNE), "2026-09-18")
        self.assertNotIn("evil.example/phish\"", page)
        self.assertIn("Fix [login](https://evil.example/phish)", page)

    def test_page_escapes_text_and_caps_long_lists(self) -> None:
        prs = [dict(pr(n), title=f"<script>alert({n})</script>") for n in range(1, 9)]
        built = board.build_board(prs, [], [], {"decisions": [], "work": []}, IN_SYNC)
        page = board.render(built, "o/r", datetime(2026, 10, 25, 9, 0, tzinfo=board.MELBOURNE), "2026-09-18")
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("<summary>Show 3 more</summary>", page)
        self.assertIn("Sun 25 Oct 2026, 09:00", page)
        self.assertIn("Installed setup:</strong> matches main", page)

    def test_inline_links_only_https(self) -> None:
        self.assertEqual(board.inline("[#61](https://github.com/o/r/pull/61)"), '<a href="https://github.com/o/r/pull/61">#61</a>')
        self.assertNotIn("<a", board.inline("[x](javascript:alert(1))"))


class LiveAndMain(unittest.TestCase):
    def test_live_state_reports_drift_and_offline_fetch(self) -> None:
        live = board.live_state(FakeRunner([], [], [], fetch_fails=True), Path("/x"))
        self.assertEqual((live["branch"], live["behind"], live["ahead"], live["dirty"]), ("chore/old-branch", 14, 0, 2))
        self.assertFalse(live["in_sync"])
        self.assertIn("last fetch", live["note"])
        self.assertIn("last fetch", board.live_html(dict(IN_SYNC, note=live["note"])))
        html = board.live_html(live)
        self.assertIn("14 commits behind main", html)
        self.assertIn("2 uncommitted changes", html)

    def test_main_writes_the_page_from_fake_sources(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            log, out = Path(folder) / "log.md", Path(folder) / "board.html"
            log.write_text(LOG, encoding="utf-8")
            runner = FakeRunner([pr(61)], [issue(60, "bug")], [])
            code = board.main(["--repo", "o/r", "--checkout", folder, "--log", str(log), "--out", str(out)], runner)
            self.assertEqual(code, 0)
            page = out.read_text(encoding="utf-8")
            self.assertIn("Do next", page)
            self.assertIn("Newer decision", page)
            self.assertIn("merged:>=2026-09-17", " ".join(runner.calls[2]))
            self.assertTrue(all("-R" in call and "o/r" in call for call in runner.calls if call[0] == "gh"))

    def test_main_fails_visibly_when_github_fails(self) -> None:
        def broken(args: Sequence[str], cwd: Optional[Path]) -> str:
            raise RuntimeError("`gh pr list` failed: not logged in")

        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "log.md"
            log.write_text(LOG, encoding="utf-8")
            out = Path(folder) / "board.html"
            self.assertEqual(board.main(["--log", str(log), "--out", str(out)], broken), 1)
            self.assertFalse(out.exists())

    def test_a_slow_command_is_reported_not_crashed(self) -> None:
        def timeout(*args: Any, **kwargs: Any) -> Any:
            raise board.subprocess.TimeoutExpired(cmd="gh pr list", timeout=60)

        with mock.patch.object(board.subprocess, "run", timeout):
            with self.assertRaisesRegex(RuntimeError, "took longer than 60 seconds"):
                board.run(["gh", "pr", "list"])

    def test_a_missing_checkout_shows_an_error_banner(self) -> None:
        def missing(args: Sequence[str], cwd: Optional[Path]) -> str:
            if args[0] == "git":
                raise RuntimeError("`git rev-parse --abbrev-ref` failed: not a git repository")
            return FakeRunner([], [], [])(args, cwd)

        with tempfile.TemporaryDirectory() as folder:
            log, out = Path(folder) / "log.md", Path(folder) / "board.html"
            log.write_text(LOG, encoding="utf-8")
            self.assertEqual(board.main(["--checkout", "/nowhere", "--log", str(log), "--out", str(out)], missing), 0)
            self.assertIn("could not be read", out.read_text(encoding="utf-8"))

    def test_rejects_a_bad_since_date(self) -> None:
        with self.assertRaises(SystemExit):
            board.main(["--since", "last week"], FakeRunner([], [], []))


if __name__ == "__main__":
    unittest.main()
