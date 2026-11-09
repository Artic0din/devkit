#!/usr/bin/env python3
"""Claude Code WorktreeCreate / WorktreeRemove hook: keep Claude's worktrees in the
shared folder, <worktrees root>/claude/<repo>/<name>, instead of <repo>/.claude/worktrees.

  claude-worktree.py create   stdin {"name", "cwd", ...}; prints the worktree path last
  claude-worktree.py remove   stdin {"worktree_path", ...}; removes it, keeping its branch

A WorktreeCreate hook replaces Claude's own git logic, so this runs `git worktree add`
itself. The root is $AGENT_WORKTREES_ROOT, default ~/Metisary/Enviroment/worktrees.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("AGENT_WORKTREES_ROOT", "~/Metisary/Enviroment/worktrees")).expanduser() / "claude"


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def ok(cwd: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True).returncode == 0


def create(event: dict) -> None:
    cwd = Path(event.get("cwd") or os.getcwd())
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(event.get("name") or "")).strip(".-")
    if not name:
        raise SystemExit("WorktreeCreate needs a name")
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    repo = Path(common).parent.name if Path(common).name == ".git" else Path(common).stem
    path = ROOT / repo / name
    if path.is_dir():
        if git(path, "rev-parse", "--path-format=absolute", "--git-common-dir") == common:
            print(path)  # resuming a session whose worktree already exists
            return
        # Another repository with the same folder name owns that path.
        path = ROOT / f"{repo}-{hashlib.sha1(common.encode()).hexdigest()[:6]}" / name
        if path.is_dir():
            print(path)
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    branch = f"worktree-{name}"
    if ok(cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        git(cwd, "worktree", "add", "-q", str(path), branch)  # Claude keeps old worktree branches
    else:
        # Same base as Claude's default: the remote default branch, else HEAD.
        base = "origin/HEAD" if ok(cwd, "rev-parse", "--verify", "--quiet", "origin/HEAD") else "HEAD"
        git(cwd, "worktree", "add", "-q", "-b", branch, str(path), base)
    print(path)


def remove(event: dict) -> None:
    path = Path(str(event.get("worktree_path") or "")).expanduser()
    if not path.is_dir():
        return
    if ROOT.resolve() not in path.resolve().parents:
        raise SystemExit(f"refusing to remove {path}: not under {ROOT}")
    # Like Claude's own removal, the branch stays; agent-sweep deletes it once merged.
    main = Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent
    git(main, "worktree", "remove", "--force", str(path))


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("create", "remove"):
        raise SystemExit(__doc__)
    event = json.load(sys.stdin)
    (create if sys.argv[1] == "create" else remove)(event)


if __name__ == "__main__":
    main()
