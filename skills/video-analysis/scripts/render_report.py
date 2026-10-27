#!/usr/bin/env python3
"""Render <folder>/analysis.json plus <folder>/meta.json into a self-contained <folder>/report.html.

Exit codes: 0 ok, 1 missing files or invalid analysis (the message names the bad field).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

MELBOURNE = ZoneInfo("Australia/Melbourne")
WHEN_VALUES = ("now", "later")
CLOCK = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--muted:#5d5d58;--line:#e2e2dc;--accent:#1f5fbf;--accent-soft:#e6eefb;--warn:#8a5a00;--warn-soft:#fff4dc;--ok:#1d7a46}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ededea;--muted:#a3a39c;--line:#33332f;--accent:#7fb0ff;--accent-soft:#1d2a40;--warn:#ffc966;--warn-soft:#3a2d12;--ok:#6fd39b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 20px 64px}
a{color:var(--accent)}
h1{font-size:1.6rem;line-height:1.25;margin:0 0 6px}
h2{font-size:1.15rem;margin:40px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.meta{color:var(--muted);font-size:.9rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.tldr{border-left:4px solid var(--accent);font-size:1.08rem;margin-top:20px}
.tldr p{margin:.3em 0}
.subject{color:var(--muted);margin-top:10px}
.chip{display:inline-block;font-size:.75rem;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--accent-soft);color:var(--accent);margin-right:6px;white-space:nowrap}
.chip.muted{background:transparent;border:1px solid var(--line);color:var(--muted)}
.chip.opinion{background:var(--warn-soft);color:var(--warn)}
.ts{font-variant-numeric:tabular-nums;font-size:.85rem;font-weight:600;text-decoration:none;padding:1px 7px;border-radius:6px;background:var(--accent-soft);margin-right:8px;white-space:nowrap}
.timeline{position:relative;height:44px;margin:8px 13px 18px}
.timeline .bar{position:absolute;left:0;right:0;top:20px;height:4px;border-radius:2px;background:var(--line)}
.timeline .tick{position:absolute;top:8px;width:26px;height:26px;margin-left:-13px;border-radius:50%;background:var(--accent);color:var(--card);font-size:.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;text-decoration:none}
.timeline .end{position:absolute;right:0;top:30px;font-size:.75rem;color:var(--muted)}
ol.moments{list-style:none;padding:0;margin:0}
ol.moments li{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--line)}
.num{flex:none;width:22px;height:22px;border-radius:50%;border:1px solid var(--accent);color:var(--accent);font-size:.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.grid h3{font-size:1rem;margin:0 0 4px}
.grid p{margin:0;color:var(--muted);font-size:.93rem}
.group{font-size:.8rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:18px 0 8px}
.action{margin-bottom:10px}
.action .what{font-weight:600;margin:0 0 6px}
.action .chips{margin-top:4px}
ul.plain{margin:6px 0 0;padding-left:20px}
.callout{border-radius:10px;padding:12px 16px;margin-top:12px;border:1px solid var(--line)}
.callout h3{font-size:.95rem;margin:0 0 4px}
.callout.warn{background:var(--warn-soft);border-color:transparent}
.callout.warn h3{color:var(--warn)}
.progress{font-size:.9rem;color:var(--muted);margin:4px 0 10px}
ol.steps{list-style:none;padding:0;margin:0;counter-reset:step}
ol.steps li{counter-increment:step;padding:10px 0;border-bottom:1px solid var(--line)}
ol.steps label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}
ol.steps input{margin-top:5px;width:18px;height:18px;flex:none}
ol.steps .text::before{content:counter(step) ". ";font-weight:700}
ol.steps li.done .text{color:var(--muted);text-decoration:line-through}
.code{position:relative;margin:8px 0 0 28px}
pre{margin:0;padding:12px 14px;border-radius:8px;background:var(--bg);border:1px solid var(--line);overflow-x:auto;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.copy{position:absolute;top:6px;right:6px;font:inherit;font-size:.75rem;padding:2px 8px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
footer{margin-top:48px;font-size:.82rem;color:var(--muted)}
footer p{margin:.3em 0}
"""

SCRIPT = """
const key = document.body.dataset.storeKey;
const boxes = [...document.querySelectorAll('ol.steps input[type=checkbox]')];
// file:// pages and sandboxed previews can block storage; ticking still works, it just isn't saved.
let saved = [];
let canSave = true;
try { saved = JSON.parse(localStorage.getItem(key) || '[]'); } catch { canSave = false; }
const progress = document.getElementById('progress');
function update() {
  const done = boxes.filter(b => b.checked).length;
  boxes.forEach(b => b.closest('li').classList.toggle('done', b.checked));
  if (progress) progress.textContent = done + ' of ' + boxes.length + ' steps done';
  try { localStorage.setItem(key, JSON.stringify(boxes.map(b => b.checked))); } catch { canSave = false; }
  const note = document.getElementById('save-note');
  if (note && boxes.length) note.textContent = canSave
    ? 'Ticked steps are saved in this browser.'
    : 'This browser is blocking storage, so ticked steps will not be saved when you close the page.';
}
boxes.forEach((b, i) => { b.checked = Boolean(saved[i]); b.addEventListener('change', update); });
update();
document.querySelectorAll('.copy').forEach(btn => btn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(btn.nextElementSibling.innerText);
    btn.textContent = 'Copied';
  } catch { btn.textContent = 'Select and copy'; }
  setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
}));
"""


class AnalysisError(ValueError):
    pass


def seconds(value: object, where: str) -> int:
    if isinstance(value, bool):
        raise AnalysisError(f"{where}: expected seconds or m:ss, got {value!r}")
    if isinstance(value, (int, float)) and value >= 0:
        return int(value)
    if isinstance(value, str) and (match := CLOCK.match(value.strip())):
        hours, minutes, secs = match.groups()
        return int(hours or 0) * 3600 + int(minutes) * 60 + int(secs)
    raise AnalysisError(f"{where}: expected seconds or m:ss, got {value!r}")


def clock(total: float) -> str:
    total = int(total)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def text(item: dict, field: str, where: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AnalysisError(f"{where}.{field}: required non-empty text")
    return value.strip()


def items(parent: dict, field: str, where: str, *, required: bool = True) -> list:
    value = parent.get(field, None if required else [])
    if not isinstance(value, list) or (required and not value):
        raise AnalysisError(f"{where}.{field}: required non-empty list")
    return value


def strings(parent: dict, field: str, where: str) -> list[str]:
    values = items(parent, field, where, required=False)
    for i, value in enumerate(values):
        if not isinstance(value, str):
            raise AnalysisError(f"{where}.{field}[{i}]: expected text")
    return values


def time_link(url: str, site: str, at: int) -> str:
    if not url.startswith(("https://", "http://")):
        return ""
    parts = urlsplit(url)
    if site == "Youtube":
        query = [(k, v) for k, v in parse_qsl(parts.query) if k != "t"] + [("t", f"{at}s")]
        return urlunsplit(parts._replace(query=urlencode(query)))
    if site == "Vimeo":
        return urlunsplit(parts._replace(fragment=f"t={at}s"))
    return ""


def stamp(meta: dict, at: int) -> str:
    href = time_link(meta.get("url") or "", meta.get("site") or "", at)
    label = escape(clock(at))
    if not href:
        return f'<span class="ts">{label}</span>'
    return f'<a class="ts" href="{escape(href)}" target="_blank" rel="noopener">{label}</a>'


def opinion_chip(item: dict) -> str:
    return '<span class="chip opinion">Presenter\'s opinion</span>' if item.get("opinion") is True else ""


def render_summary(meta: dict, moments: list) -> str:
    parsed = []
    for i, moment in enumerate(moments):
        where = f"summary[{i}]"
        if not isinstance(moment, dict):
            raise AnalysisError(f"{where}: expected an object with t and text")
        parsed.append((seconds(moment.get("t"), f"{where}.t"), text(moment, "text", where), moment))
    parsed.sort(key=lambda entry: entry[0])
    duration = meta.get("duration_seconds") or 0
    span = max(duration, parsed[-1][0] + 1)
    ticks = "".join(
        f'<a class="tick" style="left:{min(at / span * 100, 100):.2f}%" '
        f'href="{escape(time_link(meta.get("url") or "", meta.get("site") or "", at) or "#m" + str(n))}" '
        f'target="_blank" rel="noopener" title="{escape(clock(at))}: {escape(body)}">{n}</a>'
        for n, (at, body, _) in enumerate(parsed, 1)
    )
    end = f'<span class="end">{escape(clock(duration))}</span>' if duration else ""
    rows = "".join(
        f'<li id="m{n}"><span class="num">{n}</span><div>{stamp(meta, at)}{escape(body)} {opinion_chip(item)}</div></li>'
        for n, (at, body, item) in enumerate(parsed, 1)
    )
    return f'<div class="timeline" aria-hidden="true"><div class="bar"></div>{ticks}{end}</div><ol class="moments">{rows}</ol>'


def render_themes(themes: list) -> str:
    cards = []
    for i, theme in enumerate(themes):
        where = f"themes[{i}]"
        if not isinstance(theme, dict):
            raise AnalysisError(f"{where}: expected an object with name and why")
        cards.append(
            f'<div class="card"><h3>{escape(text(theme, "name", where))}</h3>'
            f'<p>{escape(text(theme, "why", where))}</p>{opinion_chip(theme)}</div>'
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def render_actions(actions: list) -> str:
    groups: dict[str, list[str]] = {"now": [], "later": []}
    for i, action in enumerate(actions):
        where = f"actions[{i}]"
        if not isinstance(action, dict):
            raise AnalysisError(f"{where}: expected an object")
        when = action.get("when")
        if when not in WHEN_VALUES:
            raise AnalysisError(f"{where}.when: expected one of {WHEN_VALUES}, got {when!r}")
        why = action.get("why")
        groups[when].append(
            f'<div class="card action"><p class="what">{escape(text(action, "action", where))}</p>'
            + (f'<p class="meta">{escape(why)}</p>' if isinstance(why, str) and why.strip() else "")
            + f'<div class="chips"><span class="chip">{escape(text(action, "area", where))}</span>'
            f'<span class="chip muted">Effort: {escape(text(action, "effort", where))}</span>{opinion_chip(action)}</div></div>'
        )
    out = ""
    for when, title in (("now", "Practical now"), ("later", "Worth it later")):
        if groups[when]:
            out += f'<div class="group">{title}</div>' + "".join(groups[when])
    return out


def bullet_callout(title: str, values: list[str], css: str = "") -> str:
    if not values:
        return ""
    lis = "".join(f"<li>{escape(v)}</li>" for v in values)
    return f'<div class="callout{" " + css if css else ""}"><h3>{escape(title)}</h3><ul class="plain">{lis}</ul></div>'


def render_tutorial(meta: dict, tutorial: object, not_tutorial: object) -> str:
    if tutorial is None:
        if not isinstance(not_tutorial, str) or not not_tutorial.strip():
            raise AnalysisError("not_tutorial: required one-line reason when tutorial is null")
        return f'<p class="meta">{escape(not_tutorial.strip())}</p>'
    if not isinstance(tutorial, dict):
        raise AnalysisError("tutorial: expected an object or null")
    where = "tutorial"
    if "costs" not in tutorial:
        raise AnalysisError("tutorial.costs: required; use [] only after checking that nothing needs a paid tier")
    steps = []
    for i, step in enumerate(items(tutorial, "steps", where)):
        step_where = f"{where}.steps[{i}]"
        if not isinstance(step, dict):
            raise AnalysisError(f"{step_where}: expected an object with t and text")
        at = step.get("t")
        when = stamp(meta, seconds(at, f"{step_where}.t")) if at is not None else ""
        code = step.get("code")
        block = (
            f'<div class="code"><button class="copy" type="button">Copy</button><pre><code>{escape(code)}</code></pre></div>'
            if isinstance(code, str) and code.strip()
            else ""
        )
        steps.append(
            f'<li><label><input type="checkbox"><span class="text">{when}{escape(text(step, "text", step_where))}</span></label>{block}</li>'
        )
    prereqs = strings(tutorial, "prerequisites", where)
    return (
        f'<div class="card"><p><strong>Goal:</strong> {escape(text(tutorial, "goal", where))}</p>'
        + (f'<p><strong>Prerequisites</strong></p><ul class="plain">{"".join(f"<li>{escape(p)}</li>" for p in prereqs)}</ul>' if prereqs else "")
        + "</div>"
        + '<p class="progress" id="progress"></p>'
        + f'<ol class="steps">{"".join(steps)}</ol>'
        + bullet_callout("Gotchas", strings(tutorial, "gotchas", where))
        + bullet_callout("Gaps: not shown in the video", strings(tutorial, "gaps", where), "warn")
        + bullet_callout("Cost check", strings(tutorial, "costs", where) or ["Nothing in the video needs an API key, subscription or paid tier."])
    )


def render(meta: dict, analysis: object) -> str:
    if not isinstance(analysis, dict):
        raise AnalysisError("analysis.json: expected a JSON object")
    tldr = text(analysis, "tldr", "analysis")
    subject = text(analysis, "subject", "analysis")
    summary = render_summary(meta, items(analysis, "summary", "analysis"))
    themes = render_themes(items(analysis, "themes", "analysis"))
    actions = items(analysis, "actions", "analysis", required=False)
    actions_html = render_actions(actions) if actions else '<p class="meta">Nothing in this video fits how you work closely enough to act on.</p>'
    tutorial = render_tutorial(meta, analysis.get("tutorial"), analysis.get("not_tutorial"))
    notes = bullet_callout("Uncertain or unverified", strings(analysis, "uncertain", "analysis"), "warn")

    title = meta.get("title") or "Video analysis"
    url = meta.get("url") or ""
    link = f'<a href="{escape(url)}" target="_blank" rel="noopener">Watch</a>' if url.startswith(("https://", "http://")) else ""
    facts = [meta.get("channel"), clock(meta["duration_seconds"]) if meta.get("duration_seconds") else None, meta.get("upload_date")]
    kind = {
        "creator": "creator captions",
        "auto": "auto-generated captions",
    }.get(meta.get("caption_kind") or "", "captions (this site does not say whether they are creator-made or auto-generated)")
    skipped = strings(analysis, "skipped_methods", "analysis")
    generated = datetime.now(tz=MELBOURNE).strftime("%Y-%m-%d %H:%M %Z")
    # Ticks are stored by position, so a changed step list gets a fresh key instead of misplaced ticks.
    tutorial_data = analysis.get("tutorial")
    steps = tutorial_data.get("steps") if isinstance(tutorial_data, dict) else None
    steps_fingerprint = hashlib.sha256(json.dumps(steps, sort_keys=True).encode()).hexdigest()[:12]
    store_key = f"video-analysis:{meta.get('id') or title}:{steps_fingerprint}"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style></head>
<body data-store-key="{escape(store_key)}"><main>
<h1>{escape(title)}</h1>
<div class="meta">{" · ".join(escape(str(f)) for f in facts if f)}{" · " + link if link else ""}</div>
<div class="card tldr">{"".join(f"<p>{escape(p.strip())}</p>" for p in tldr.split(chr(10)) if p.strip())}</div>
<p class="subject"><strong>Subject:</strong> {escape(subject)}</p>
{notes}
<h2>Key moments</h2>{summary}
<h2>Themes</h2>{themes}
<h2>How you could use this</h2>{actions_html}
<h2>Step-by-step guide</h2>{tutorial}
<footer>
<p>Transcript: {escape(kind)} ({escape(meta.get("caption_language") or "unknown")}), fetched with {escape(meta.get("transcript_method") or "yt-dlp")}. No API keys used.</p>
{"".join(f"<p>Skipped: {escape(s)}</p>" for s in skipped)}
<p>Generated {escape(generated)}. <span id="save-note"></span></p>
</footer>
</main><script>{SCRIPT}</script></body></html>
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_report.py <video-folder>", file=sys.stderr)
        return 1
    folder = Path(sys.argv[1]).expanduser()
    try:
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        analysis = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
        html = render(meta, analysis)
    except FileNotFoundError as error:
        print(f"error: missing {error.filename}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, AnalysisError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    out = folder / "report.html"
    out.write_text(html, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
