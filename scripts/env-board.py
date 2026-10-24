#!/usr/bin/env python3
"""Build one HTML status page for the environment rebuild.

Live status comes from GitHub (open pull requests and issues, merged pull
requests) and from the installed checkout. Decisions, and work that exists
only in chats, come from docs/environment-log.md. Anything tracked on GitHub
is read from GitHub, never copied into the log.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MELBOURNE = ZoneInfo("Australia/Melbourne")
DEFAULT_REPO = "Artic0din/devkit"
DEFAULT_CHECKOUT = Path.home() / "Metisary/Enviroment/config"
# The rebuilt layout was adopted on this date (#6).
REBUILD_START = "2026-09-18"
VISIBLE = 5
FAILED = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
PASSED = {"SUCCESS", "NEUTRAL", "SKIPPED", "STALE"}
LOG_STATUS = {
    "waiting on you": "needs_you",
    "in progress": "in_progress",
    "blocked": "blocked",
    "pending": "outstanding",
    "done": "done",
}
ISSUE_REASONS = (
    ("needs-info", "Waiting for more information"),
    ("needs-triage", "Not looked at yet"),
    ("ready-for-agent", "Ready for an agent to pick up"),
    ("ready-for-human", "Ready for a person to pick up"),
)
LANES = (
    ("needs_you", "Needs you", "you"),
    ("in_progress", "In progress", "work"),
    ("blocked", "Blocked", "stop"),
    ("outstanding", "Outstanding", "wait"),
)

Item = Dict[str, str]
Runner = Callable[[Sequence[str], Optional[Path]], str]


def run(args: Sequence[str], cwd: Optional[Path] = None) -> str:
    try:
        result = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"`{' '.join(args[:3])}` took longer than 60 seconds") from error
    if result.returncode != 0:
        raise RuntimeError(f"`{' '.join(args[:3])}` failed: {result.stderr.strip() or result.returncode}")
    return result.stdout


def check_state(rollup: List[Dict[str, Any]]) -> str:
    states = []
    for check in rollup:
        if check.get("__typename") == "StatusContext":
            states.append(check.get("state") or "PENDING")
        elif check.get("status") != "COMPLETED":
            states.append("PENDING")
        else:
            states.append(check.get("conclusion") or "PENDING")
    if any(state in FAILED for state in states):
        return "failing"
    if any(state not in PASSED for state in states):
        return "running"
    return "passed"


def pr_item(pr: Dict[str, Any]) -> Item:
    checks = check_state(pr.get("statusCheckRollup") or [])
    merge = pr.get("mergeStateStatus")
    if pr.get("isDraft"):
        lane, reason = "in_progress", "Draft, not ready for review yet"
    elif checks == "failing":
        lane, reason = "blocked", "Checks are failing"
    elif merge == "DIRTY":
        lane, reason = "blocked", "Conflicts with main, so it needs updating before it can merge"
    elif checks == "running":
        lane, reason = "in_progress", "Checks are still running"
    elif merge in ("CLEAN", "HAS_HOOKS"):
        lane, reason = "needs_you", "Checks passed. Ready for you to merge"
    elif merge == "BEHIND":
        lane, reason = "in_progress", "Behind main, so it needs an update before merging"
    elif merge == "UNSTABLE":
        lane, reason = "in_progress", "Some optional checks did not pass; look before merging"
    elif merge == "BLOCKED":
        lane, reason = "in_progress", "Waiting on a required review or check"
    else:
        lane, reason = "in_progress", "GitHub is still working out whether it can merge"
    return {"lane": lane, "ref": f"#{pr['number']}", "title": pr["title"], "url": pr["url"], "reason": reason, "plain": "yes"}


def issue_item(issue: Dict[str, Any]) -> Item:
    labels = {label["name"] for label in issue.get("labels") or []}
    reason = next((text for name, text in ISSUE_REASONS if name in labels), "Not started")
    kind = "Bug" if "bug" in labels else "Docs" if "documentation" in labels else "Feature" if "enhancement" in labels else "Issue"
    return {"lane": "outstanding", "ref": f"#{issue['number']}", "title": issue["title"], "url": issue["url"],
            "reason": f"{kind}. {reason}", "kind": kind, "plain": "yes"}


def why_of(body: Optional[str]) -> str:
    text = re.sub(r"<!--.*?-->", "", (body or "").replace("\r\n", "\n"), flags=re.S)
    section = re.search(r"^#+\s*(?:Why|What was broken)\s*\n(.*?)(?=^#|\Z)", text, re.M | re.S | re.I)
    paragraphs = [p.strip() for p in (section.group(1) if section else text).split("\n\n")]
    first = next((p for p in paragraphs if p and not p.startswith(("#", "-", "|", "```"))), "")
    first = " ".join(first.replace("**", "").split())
    return first if len(first) <= 240 else first[:240].rsplit(" ", 1)[0] + "…"


def parse_log(text: str) -> Dict[str, List[Dict[str, str]]]:
    tables: Dict[str, List[Dict[str, str]]] = {"decisions": [], "work": []}
    section: Optional[str] = None
    header: Optional[List[str]] = None
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            title = line[3:].strip().lower()
            section = "decisions" if title == "decisions" else "work" if title == "work not on github" else None
            header = None
        elif section and line.startswith("|"):
            row_text = line.strip()[1:]
            row_text = row_text[:-1] if row_text.endswith("|") else row_text
            cells = [cell.strip() for cell in row_text.split("|")]
            if header is None:
                header = [cell.lower() for cell in cells]
            elif not set("".join(cells)) <= set("-: "):
                if len(cells) != len(header):
                    raise ValueError(f"environment log line {number}: expected {len(header)} cells, found {len(cells)}")
                row = dict(zip(header, cells))
                if section == "work" and row.get("status", "").lower() not in LOG_STATUS:
                    raise ValueError(f"environment log line {number}: status must be one of {', '.join(LOG_STATUS)}")
                tables[section].append(row)
    return tables


def live_state(runner: Runner, checkout: Path) -> Dict[str, Any]:
    state: Dict[str, Any] = {"path": str(checkout), "note": ""}
    try:
        runner(["git", "fetch", "--quiet", "origin", "main"], checkout)
    except RuntimeError:
        state["note"] = "Could not reach GitHub, so these counts use the last fetch."
    state["branch"] = runner(["git", "rev-parse", "--abbrev-ref", "HEAD"], checkout).strip()
    behind, ahead = runner(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"], checkout).split()
    state["behind"], state["ahead"] = int(behind), int(ahead)
    state["dirty"] = sum(1 for line in runner(["git", "status", "--porcelain"], checkout).splitlines() if line.strip())
    state["in_sync"] = state["branch"] == "main" and not (state["behind"] or state["ahead"] or state["dirty"])
    return state


def local_date(stamp: str) -> str:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(MELBOURNE).date().isoformat()


def build_board(prs: List[Dict[str, Any]], issues: List[Dict[str, Any]], merged: List[Dict[str, Any]],
                log: Dict[str, List[Dict[str, str]]], live: Dict[str, Any], since: str = REBUILD_START) -> Dict[str, Any]:
    lanes: Dict[str, List[Item]] = {key: [] for key, _, _ in LANES}
    changes: List[Item] = []
    for pr in prs:
        item = pr_item(pr)
        lanes[item["lane"]].append(item)
    for issue in sorted(issues, key=lambda issue: issue_item(issue)["kind"] != "Bug"):
        lanes["outstanding"].append(issue_item(issue))
    for row in log["work"]:
        lane = LOG_STATUS[row["status"].lower()]
        item = {"ref": "chat", "title": row.get("item", ""), "url": "", "date": row.get("date", "")}
        if lane == "done":
            changes.append({**item, "reason": row.get("why", "")})
        else:
            lanes[lane].append({**item, "reason": row.get("next step") or row.get("why", "")})
    for pr in merged:
        if local_date(pr["mergedAt"]) < since:
            continue
        changes.append({"ref": f"#{pr['number']}", "title": pr["title"], "url": pr["url"],
                        "date": local_date(pr["mergedAt"]), "reason": why_of(pr.get("body")), "plain": "yes"})
    changes.sort(key=lambda item: item["date"], reverse=True)
    decisions = sorted(log["decisions"], key=lambda row: row.get("date", ""), reverse=True)
    do_next = next((lanes[key][0] for key in ("needs_you", "blocked", "outstanding") if lanes[key]), None)
    return {"lanes": lanes, "changes": changes, "decisions": decisions, "do_next": do_next, "live": live}


def inline(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return re.sub(r"\[([^\]]+)\]\((https://[^)\s]+)\)", r'<a href="\2">\1</a>', escaped)


def text_of(item: Item, key: str) -> str:
    # GitHub titles and bodies come from anyone who can open an issue, so only log text gets links.
    return html.escape(item.get(key, ""), quote=True) if item.get("plain") else inline(item.get(key, ""))


def link(item: Item) -> str:
    title = text_of(item, "title")
    return f'<a href="{html.escape(item["url"], quote=True)}">{title}</a>' if item.get("url") else title


def item_html(item: Item) -> str:
    when = f'<span class="date">{html.escape(item["date"])}</span> ' if item.get("date") else ""
    return (f'<li><span class="ref">{html.escape(item["ref"])}</span> {when}{link(item)}'
            f'<div class="why">{text_of(item, "reason")}</div></li>')


def capped(rows: List[str]) -> str:
    if not rows:
        return '<p class="empty">Nothing here.</p>'
    shown = f'<ol>{"".join(rows[:VISIBLE])}</ol>'
    if len(rows) > VISIBLE:
        shown += f'<details><summary>Show {len(rows) - VISIBLE} more</summary><ol>{"".join(rows[VISIBLE:])}</ol></details>'
    return shown


def live_html(live: Dict[str, Any]) -> str:
    if "error" in live:
        return f'<section class="banner stop"><strong>Installed setup:</strong> could not be read. {inline(live["error"])}</section>'
    if live["in_sync"]:
        return f'<section class="banner done"><strong>Installed setup:</strong> matches main. {html.escape(live["note"])}</section>'
    parts = [f'on branch <code>{html.escape(live["branch"])}</code>']
    if live["behind"]:
        parts.append(f'{live["behind"]} commits behind main')
    if live["ahead"]:
        parts.append(f'{live["ahead"]} local commits not on main')
    if live["dirty"]:
        parts.append(f'{live["dirty"]} uncommitted changes')
    return (f'<section class="banner wait"><strong>Installed setup is out of date:</strong> {", ".join(parts)}. '
            f'Changes merged on GitHub do not reach your agents until it is updated. {html.escape(live["note"])}</section>')


def render(board: Dict[str, Any], repo: str, generated: datetime, since: str) -> str:
    counts = [(key, label, tone, len(board["lanes"][key])) for key, label, tone in LANES]
    counts += [("changed", "Changed", "done", len(board["changes"])), ("decisions", "Decisions", "info", len(board["decisions"]))]
    strip = "".join(f'<a class="count {tone}" href="#{key}"><b>{n}</b>{label}</a>' for key, label, tone, n in counts)
    do_next = board["do_next"]
    next_html = (f'<p class="next-title">{link(do_next)}</p><p>{text_of(do_next, "reason")}</p>'
                 if do_next else "<p>Nothing is waiting on you.</p>")
    lanes = "".join(f'<section id="{key}" class="lane {tone}"><h2>{label}</h2>'
                    f'{capped([item_html(item) for item in board["lanes"][key]])}</section>' for key, label, tone in LANES)
    changes = capped([item_html(item) for item in board["changes"]])
    decisions = capped([
        f'<li><span class="date">{html.escape(row.get("date", ""))}</span> <strong>{inline(row.get("decision", ""))}</strong>'
        f'<div class="why">Why: {inline(row.get("why", ""))}</div>'
        + (f'<div class="why">Where: {inline(row["where"])}</div>' if row.get("where") else "") + "</li>"
        for row in board["decisions"]])
    stamp = generated.astimezone(MELBOURNE).strftime("%a %d %b %Y, %H:%M")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Environment rebuild status</title><style>{CSS}</style></head>
<body><main>
<header><h1>Environment rebuild</h1><p class="meta">{html.escape(repo)} · updated {stamp} Melbourne time</p></header>
<section class="next"><h2>Do next</h2>{next_html}</section>
{live_html(board["live"])}
<nav class="counts" aria-label="Sections">{strip}</nav>
<div class="lanes">{lanes}</div>
<section id="changed" class="lane done"><h2>What changed and why</h2><p class="meta">Since {html.escape(since)}, newest first.</p>{changes}</section>
<section id="decisions" class="lane info"><h2>Decisions</h2><p class="meta">From <code>docs/environment-log.md</code>, newest first.</p>{decisions}</section>
</main></body></html>
"""


CSS = """
:root{color-scheme:light dark;--bg:#fafaf9;--fg:#1c1917;--muted:#57534e;--card:#fff;--line:#d6d3d1;
--you:#1d4ed8;--work:#6d28d9;--stop:#b91c1c;--wait:#a16207;--done:#15803d;--info:#0f766e}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--muted:#d6d3d1;--card:#292524;--line:#57534e;
--you:#93c5fd;--work:#c4b5fd;--stop:#fca5a5;--wait:#fcd34d;--done:#86efac;--info:#5eead4}}
*{box-sizing:border-box}main{overflow-wrap:anywhere}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 system-ui,-apple-system,sans-serif}
main{max-width:64rem;margin:0 auto;padding:1.5rem 1rem 4rem}h1{margin:0;font-size:1.8rem}h2{margin:0 0 .5rem;font-size:1.15rem}
a{color:inherit}.meta{color:var(--muted);margin:.25rem 0 .75rem;font-size:.9rem}code{font-size:.9em}
.next{background:var(--card);border:3px solid var(--you);border-radius:12px;padding:1rem 1.25rem;margin:1rem 0}
.next-title{font-size:1.3rem;font-weight:600;margin:.25rem 0}
.banner{border-left:6px solid var(--wait);background:var(--card);padding:.75rem 1rem;border-radius:8px;margin:1rem 0}
.banner.done{border-color:var(--done)}.banner.stop{border-color:var(--stop)}
.counts{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0}
.count{display:flex;flex-direction:column;min-width:7rem;padding:.5rem .75rem;border-radius:10px;background:var(--card);
border:1px solid var(--line);border-top:5px solid;text-decoration:none}.count b{font-size:1.6rem;line-height:1.1}
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(28rem,100%),1fr));gap:0 1rem;align-items:start}
.lane{background:var(--card);border:1px solid var(--line);border-left:6px solid;border-radius:10px;padding:1rem;margin-top:1rem}
.you{border-color:var(--you)}.work{border-color:var(--work)}.stop{border-color:var(--stop)}.wait{border-color:var(--wait)}
.done{border-color:var(--done)}.info{border-color:var(--info)}
ol{margin:0;padding-left:1.25rem}li{margin:.5rem 0}.why{color:var(--muted);font-size:.92rem}
.ref{font-weight:600;font-variant-numeric:tabular-nums}.date{color:var(--muted);font-variant-numeric:tabular-nums}
.empty{color:var(--muted);margin:0}summary{cursor:pointer;margin-top:.5rem;font-weight:600}
"""


def collect(runner: Runner, repo: str, checkout: Path, log_path: Path, since: str) -> Dict[str, Any]:
    def gh(*args: str) -> List[Dict[str, Any]]:
        return json.loads(runner(["gh", *args, "-R", repo], None))

    prs = gh("pr", "list", "--state", "open", "--limit", "100",
             "--json", "number,title,url,isDraft,mergeStateStatus,statusCheckRollup")
    issues = gh("issue", "list", "--state", "open", "--limit", "200", "--json", "number,title,url,labels")
    # GitHub search dates are UTC; start a day early and filter on the Melbourne date in build_board.
    utc_start = (date.fromisoformat(since) - timedelta(days=1)).isoformat()
    merged = gh("pr", "list", "--state", "merged", "--search", f"merged:>={utc_start}", "--limit", "200",
                "--json", "number,title,url,mergedAt,body")
    log = parse_log(log_path.read_text(encoding="utf-8"))
    try:
        live = live_state(runner, checkout)
    except (RuntimeError, OSError, ValueError) as error:
        live = {"error": str(error)}
    return build_board(prs, issues, merged, log, live, since)


def iso_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from error


def main(argv: Optional[Sequence[str]] = None, runner: Runner = run) -> int:
    parser = argparse.ArgumentParser(description="Build the environment rebuild status page.")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--checkout", type=Path, default=DEFAULT_CHECKOUT, help="installed checkout agents load")
    parser.add_argument("--log", type=Path, default=ROOT / "docs/environment-log.md")
    parser.add_argument("--since", default=REBUILD_START, type=iso_date, help="show merged changes from this date (YYYY-MM-DD)")
    parser.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "devkit-env-board.html")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = parser.parse_args(argv)
    try:
        board = collect(runner, args.repo, args.checkout, args.log, args.since)
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"env-board: {error}", file=sys.stderr)
        return 1
    args.out.write_text(render(board, args.repo, datetime.now(tz=MELBOURNE), args.since), encoding="utf-8")
    print(args.out)
    if args.open:
        webbrowser.open(args.out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
