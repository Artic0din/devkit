"""Execute the baseline workflow's actual shell step in consumer fixtures."""

import json
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
        self.root = Path(temporary.name) / "checkout"
        self.root.mkdir()
        job = (ROOT / ".github/workflows/baseline.yml").read_text().partition("\n  pr-hygiene:\n")[0]
        # The baseline job has one shell step, at its end; fail if extraction becomes ambiguous.
        self.assertEqual(job.count("        run: |\n"), 1)
        self.script = textwrap.dedent(job.partition("        run: |\n")[2])

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
        result = self.run_step(REQUIRED_FILES="README.md, missing, dangling, absent-directory/../README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Required paths do not exist", result.stderr)
        self.assertIn("missing", result.stderr)
        self.assertIn("dangling", result.stderr)
        self.assertIn("absent-directory/../README.md", result.stderr)

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

    def test_rejects_absolute_paths_and_parent_traversal(self) -> None:
        (self.root / "README.md").write_text("fixture\n")
        outside = self.root.parent / "outside.md"
        outside.write_text("outside fixture\n")
        for value in (str(outside), str(self.root / "README.md"), "../outside.md", "..", "../missing"):
            with self.subTest(value=value):
                result = self.run_step(REQUIRED_FILES=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Required paths must be relative and stay within the checkout", result.stderr)
                self.assertIn(repr(value), result.stderr)

    def test_rejects_symlink_escapes_and_sibling_prefixes(self) -> None:
        sibling = self.root.parent / "checkout-sibling"
        sibling.mkdir()
        (sibling / "file.md").write_text("outside fixture\n")
        (self.root / "escape-file").symlink_to(sibling / "file.md")
        (self.root / "escape-directory").symlink_to(sibling, target_is_directory=True)
        for value in ("escape-file", "escape-directory", "escape-directory/file.md", "../checkout-sibling/file.md"):
            with self.subTest(value=value):
                result = self.run_step(REQUIRED_FILES=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Required paths must be relative and stay within the checkout", result.stderr)
                self.assertIn(repr(value), result.stderr)

    def test_reports_all_invalid_paths(self) -> None:
        (self.root / "README.md").write_text("fixture\n")
        absolute = str(self.root / "README.md")
        result = self.run_step(REQUIRED_FILES=f"README.md, .., {absolute}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(repr(".."), result.stderr)
        self.assertIn(repr(absolute), result.stderr)

    def test_accepts_normalized_paths_and_internal_symlinks(self) -> None:
        (self.root / "README.md").write_text("fixture\n")
        (self.root / "docs").mkdir()
        (self.root / "absolute-link").symlink_to(self.root / "README.md")
        result = self.run_step(REQUIRED_FILES="./README.md, docs/../README.md, absolute-link")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 3 required paths", result.stdout)

    def test_rejects_symlink_loops_with_path_diagnostic(self) -> None:
        (self.root / "loop-one").symlink_to("loop-two")
        (self.root / "loop-two").symlink_to("loop-one")
        result = self.run_step(REQUIRED_FILES="loop-one")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(result.stderr.startswith((
            "Cannot resolve required path 'loop-one':",
            "Required paths do not exist: ['loop-one']",
        )), result.stderr)

    def test_reports_resolution_invalid_and_missing_failures_together(self) -> None:
        (self.root / "loop-one").symlink_to("loop-two")
        (self.root / "loop-two").symlink_to("loop-one")
        result = self.run_step(REQUIRED_FILES="loop-one, ../outside.md, missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        for path in ("loop-one", "../outside.md", "missing"):
            self.assertIn(repr(path), result.stderr)



class PullRequestHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "checkout"
        self.root.mkdir()
        job = (ROOT / ".github/workflows/baseline.yml").read_text().partition("\n  pr-hygiene:\n")[2]
        self.assertEqual(job.count("        run: |\n"), 1)
        self.script = textwrap.dedent(job.partition("        run: |\n")[2])
        self.git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("fixture\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "chore: base")
        self.base = self.git("rev-parse", "HEAD")
        self.commits = Path(temporary.name) / "commits.jsonl"
        self.commits.write_text("")

    def git(self, *arguments: str) -> str:
        identity = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.com"]
        return subprocess.run(["git", *identity, *arguments], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def change(self, path: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(target.read_text() + "more\n" if target.exists() else "new\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: change")
        return self.git("rev-parse", "HEAD")

    def run_step(self, head: str | None = None, commits: list[dict[str, str]] | None = None,
                 **values: str) -> subprocess.CompletedProcess[str]:
        self.commits.write_text("".join(json.dumps(commit) + "\n" for commit in commits or []))
        environment = dict(os.environ)
        environment.update(TITLE="feat(core): add a thing", BODY="## ELI5\nA thing.", BASE=self.base,
                           HEAD=head or self.base, AUTHOR="author", FORBIDDEN="node_modules",
                           COMMITS_FILE=str(self.commits))
        environment.update(values)
        return subprocess.run(["bash", "-euo", "pipefail", "-c", self.script], cwd=self.root,
                              env=environment, capture_output=True, text=True, timeout=15, check=False)

    def test_accepts_a_clean_pull_request(self) -> None:
        human = ("fix(core): x\n\nCo-authored-by: Sam <sam@example.com>\nCo-authored-by: Claude Martin <claude@example.org>"
                 "\nCo-authored-by: Sam Lee <sam@openai.com>")
        result = self.run_step(commits=[{"sha": "a" * 40, "login": "author", "message": human}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Pull request hygiene passed", result.stdout)

    def test_rejects_non_conventional_titles_and_own_commits_only(self) -> None:
        commits = [
            {"sha": "a" * 40, "login": "author", "message": "wip: other Sonarr instances"},
            {"sha": "b" * 40, "login": "upstream", "message": "Add a feature upstream"},
            {"sha": "c" * 40, "login": "author", "parents": 2, "message": "merge: main into feature"},
        ]
        result = self.run_step(commits=commits, TITLE="Sync published 0.4.1 source")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Title is not a conventional commit", result.stderr)
        self.assertIn("Commit aaaaaaaa is not a conventional commit: 'wip: other Sonarr instances'", result.stderr)
        self.assertNotIn("bbbbbbbb", result.stderr)
        self.assertNotIn("cccccccc", result.stderr)

    def test_checks_commits_beyond_the_listed_250_by_author_email(self) -> None:
        listed = self.change("a.txt")
        self.git("commit", "-q", "--allow-empty", "-m", "wip: unlisted own commit")
        self.git("-c", "user.email=upstream@example.com", "commit", "-q", "--allow-empty", "-m", "Upstream change")
        result = self.run_step(head=self.git("rev-parse", "HEAD"), TOTAL_COMMITS="3",
                               commits=[{"sha": listed, "login": "author", "parents": 1, "message": "feat: change"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("'wip: unlisted own commit'", result.stderr)
        self.assertNotIn("Upstream change", result.stderr)

    def test_rejects_agent_attribution_in_body_and_commits(self) -> None:
        commits = [{"sha": "a" * 40, "login": "author", "message": "fix(x): y\n\nCo-authored-by: Cursor <cursoragent@cursor.com>"}]
        result = self.run_step(commits=commits, BODY="Fixes #1\n\nCreated with Kimi K3 in T3 Code.")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pull request body carries agent attribution: 'Created with '", result.stderr)
        self.assertIn("Commit aaaaaaaa carries agent attribution", result.stderr)
        for footer in ("🤖 Generated with [Claude Code](https://claude.com/claude-code)",
                       "Made with [Cursor](https://cursor.com)",
                       "> 🤖 **kimi-k3 responding on behalf of author**",
                       "Created with Composer in T3 Code."):
            with self.subTest(footer=footer):
                result = self.run_step(BODY=f"Fixes #1\n\n{footer}")
                self.assertIn("Pull request body carries agent attribution", result.stderr)
                result = self.run_step(commits=[{"sha": "d" * 40, "login": "author", "message": f"fix(x): y\n\n{footer}"}])
                self.assertIn("Commit dddddddd carries agent attribution", result.stderr)
        for trailer in ("Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
                        "Co-authored-by: Copilot <198982749+Copilot@users.noreply.github.com>"):
            with self.subTest(trailer=trailer):
                result = self.run_step(commits=[{"sha": "b" * 40, "login": "author", "message": f"fix(x): y\n\n{trailer}"}])
                self.assertIn("Commit bbbbbbbb carries agent attribution", result.stderr)

    def test_accepts_bodies_that_quote_the_patterns(self) -> None:
        body = 'Rejects a `Generated with [` footer or a "responding on behalf of" note.\n```\nCreated with Codex.\n```'
        result = self.run_step(BODY=body)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_step(BODY="Fixes #1\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)")
        self.assertIn("Pull request body carries agent attribution: 'Generated with ['", result.stderr)

    def test_allows_attribution_when_the_template_requires_ai_disclosure(self) -> None:
        signed = "> 🤖 **Codex responding on behalf of author**"
        head = self.change(".github/PULL_REQUEST_TEMPLATE.md")
        (self.root / ".github/PULL_REQUEST_TEMPLATE.md").write_text("## AI disclosure\nState which AI tools assisted with this change.\n")
        self.git("commit", "-q", "-am", "docs: ask for AI disclosure")
        head = self.git("rev-parse", "HEAD")
        result = self.run_step(head=head, BODY=signed)
        self.assertIn("carries agent attribution", result.stderr, "a pull request must not exempt itself")
        self.base = head
        result = self.run_step(head=head, BODY=signed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Agent attribution allowed: AI disclosure is required by .github/PULL_REQUEST_TEMPLATE.md", result.stdout)

    def test_a_template_that_bans_attribution_does_not_unlock_it(self) -> None:
        self.change(".github/pull_request_template.md")
        (self.root / ".github/pull_request_template.md").write_text("Do not include AI attribution or co-author trailers.\n")
        self.git("commit", "-q", "-am", "docs: ban attribution")
        self.base = self.git("rev-parse", "HEAD")
        result = self.run_step(head=self.base, BODY="Created with Kimi K3 in T3 Code.")
        self.assertIn("Pull request body carries agent attribution", result.stderr)
        (self.root / ".github/pull_request_template.md").write_text(
            'Disclose AI assistance; otherwise write "not applicable"; do not include agent co-author trailers.\n'
            "Do not forget to disclose AI assistance.\n")
        self.git("commit", "-q", "-am", "docs: ask for AI disclosure")
        self.base = self.git("rev-parse", "HEAD")
        result = self.run_step(head=self.base, BODY="Created with Kimi K3 in T3 Code.")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_warns_when_no_listed_commit_is_the_authors(self) -> None:
        listed = self.change("a.txt")
        result = self.run_step(head=listed, TOTAL_COMMITS="300",
                               commits=[{"sha": listed, "login": "upstream", "parents": 1, "message": "Upstream"}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("::warning::Only the first 1 of 300 commits could be listed", result.stdout)

    def test_skips_title_commit_and_attribution_checks_for_bots(self) -> None:
        result = self.run_step(AUTHOR="dependabot[bot]", TITLE="Bump x from 1 to 2", BODY="Generated with [tool](x)")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_forbidden_paths_added_or_modified_at_any_depth(self) -> None:
        result = self.run_step(head=self.change("web/node_modules/pkg/index.js"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Changes forbidden path node_modules", result.stderr)
        result = self.run_step(head=self.change("README.md"), FORBIDDEN="README.md")
        self.assertIn("Changes forbidden path README.md: ['README.md']", result.stderr)
        result = self.run_step(head=self.change("dist/app.html"), FORBIDDEN="node_modules, dist")
        self.assertIn("Changes forbidden path dist", result.stderr)
        self.base = self.git("rev-parse", "HEAD")
        self.change("vendor/lib.js")
        start = self.base
        self.base = self.git("rev-parse", "HEAD")
        (self.root / "node_modules").mkdir(exist_ok=True)
        self.git("mv", "vendor/lib.js", "node_modules/lib.js")
        self.git("commit", "-q", "-m", "chore: move into node_modules")
        result = self.run_step(head=self.git("rev-parse", "HEAD"))
        self.assertIn("Changes forbidden path node_modules: ['node_modules/lib.js']", result.stderr)
        moved_in = self.git("rev-parse", "HEAD")
        self.base = moved_in
        self.git("mv", "node_modules/lib.js", "lib.js")
        self.git("commit", "-q", "-m", "chore: move out of node_modules")
        result = self.run_step(head=self.git("rev-parse", "HEAD"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.base = start
        result = self.run_step(head=self.change("node_modules/café.js"))
        self.assertIn("'node_modules/café.js'", result.stderr)
        (self.root / "LICENSE").write_text("text\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "chore: add license")
        self.base = self.git("rev-parse", "HEAD")
        (self.root / "LICENSE").unlink()
        (self.root / "LICENSE").symlink_to("README.md")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "chore: link license")
        result = self.run_step(head=self.git("rev-parse", "HEAD"), FORBIDDEN="LICENSE")
        self.assertIn("Changes forbidden path LICENSE: ['LICENSE']", result.stderr)


if __name__ == "__main__":
    unittest.main()
