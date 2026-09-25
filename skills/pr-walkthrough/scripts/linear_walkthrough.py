#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

REQUIRED_STEP_FIELDS = {
    "id",
    "title",
    "orientation",
    "explanation",
    "diffs",
    "reviewChecks",
}


class DataExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.parts: list[str] = []
        self.runtime_parts: list[str] = []
        self.capture_runtime = False
        self.asset_reference = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "link", "img"} and ("src" in attributes or "href" in attributes):
            self.asset_reference = True
        if tag == "script":
            self.capture = attributes.get("id") == "walkthrough-data"
            self.capture_runtime = not self.capture

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.capture = False
            self.capture_runtime = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)
        if self.capture_runtime:
            self.runtime_parts.append(data)


def is_web_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def validate_data(data: dict) -> list[str]:
    if not isinstance(data, dict):
        return ["Walkthrough data must be an object"]
    errors: list[str] = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("Missing meta object")
    else:
        for field in ("title", "summary", "baseRef", "headRef", "prUrl"):
            if not isinstance(meta.get(field), str) or not meta[field]:
                errors.append(f"Missing meta.{field}")
        if not is_web_url(meta.get("prUrl")):
            errors.append("meta.prUrl must be an HTTP(S) URL")

    findings = data.get("findings")
    if not isinstance(findings, list):
        errors.append("Missing findings array")
    else:
        required_finding_fields = {
            "severity",
            "title",
            "body",
            "file",
            "evidence",
            "remediation",
        }
        for index, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                errors.append(f"Finding {index} is not an object")
                continue
            missing = required_finding_fields - finding.keys()
            if missing:
                errors.append(
                    f"Finding {index} missing fields: {', '.join(sorted(missing))}"
                )
            for field in required_finding_fields:
                if field in finding and not finding.get(field):
                    errors.append(f"Finding {index} has empty {field}")
            if finding.get("severity") not in ("critical", "major"):
                errors.append(
                    f"Finding {index} severity must be critical or major"
                )

    interfaces = data.get("interfaces")
    if interfaces is None:
        errors.append("Missing interfaces array")
    if interfaces is not None:
        if not isinstance(interfaces, list):
            errors.append("interfaces must be an array")
        else:
            required_iface_fields = {"category", "file", "description"}
            valid_categories = {
                "firestore", "grpc", "http-api", "database",
                "storage", "messaging", "config",
            }
            for index, iface in enumerate(interfaces, start=1):
                if not isinstance(iface, dict):
                    errors.append(f"Interface {index} is not an object")
                    continue
                missing = required_iface_fields - iface.keys()
                if missing:
                    errors.append(
                        f"Interface {index} missing fields: {', '.join(sorted(missing))}"
                    )
                if not isinstance(iface.get("category"), str) or iface["category"] not in valid_categories:
                    errors.append(
                        f"Interface {index} category must be one of: {', '.join(sorted(valid_categories))}"
                    )
                for field in ("addedLines", "removedLines"):
                    if not isinstance(iface.get(field, []), list):
                        errors.append(f"Interface {index} {field} must be an array")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        return errors + ["Walkthrough must contain at least one step"]

    seen_ids: set[str] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"Step {index} is not an object")
            continue
        missing = REQUIRED_STEP_FIELDS - step.keys()
        if missing:
            errors.append(f"Step {index} missing fields: {', '.join(sorted(missing))}")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            errors.append(f"Step {index} id must be a nonempty string")
        elif step_id in seen_ids:
            errors.append(f"Duplicate step id: {step_id}")
        if isinstance(step_id, str):
            seen_ids.add(step_id)
        for field in ("diffs", "explanation", "reviewChecks", "productionExamples"):
            if not isinstance(step.get(field, []), list):
                errors.append(f"Step {index} {field} must be an array")
        diffs = step.get("diffs")
        if not diffs:
            errors.append(f"Step {index} has no code diff")
        for diff_index, diff in enumerate(diffs if isinstance(diffs, list) else [], start=1):
            if not isinstance(diff, dict):
                errors.append(f"Step {index} diff {diff_index} must be an object")
                continue
            if not diff.get("file") or not diff.get("lines"):
                errors.append(f"Step {index} diff {diff_index} needs file and lines")
            lines = diff.get("lines")
            if not isinstance(lines, list) or any(not isinstance(line, dict) for line in lines):
                errors.append(f"Step {index} diff {diff_index} lines must be an array of objects")
            elif not any(line.get("type") in ("add", "remove") for line in lines):
                errors.append(f"Step {index} diff {diff_index} needs at least one changed line")
            if diff.get("url") and not is_web_url(diff["url"]):
                errors.append(f"Step {index} diff {diff_index} URL must be HTTP(S)")
        examples = step.get("productionExamples", [])
        if isinstance(examples, list) and any(not isinstance(example, dict) for example in examples):
            errors.append(f"Step {index} productionExamples must contain objects")
        elif isinstance(examples, list):
            for example in examples:
                for field in ("title", "note", "content"):
                    if not isinstance(example.get(field), str) or not example[field].strip():
                        errors.append(f"Step {index} production example needs nonempty {field}")
        if step.get("kind") in ("interface", "data-model") and not step.get(
            "productionExamples"
        ):
            errors.append(
                f"Step {index} describes {step.get('kind')} but has no production example"
            )
    return errors


def css() -> str:
    return """
:root {
  color-scheme: dark;
  --bg: #111214;
  --panel: #181a1f;
  --panel-2: #20232a;
  --border: #353944;
  --text: #f5f7fa;
  --muted: #aeb5c2;
  --accent: #78a9ff;
  --add-bg: #12351f;
  --add-border: #39a55a;
  --remove-bg: #3b171a;
  --remove-border: #d95562;
  --context-bg: #17191e;
  --example-bg: #151d2b;
  --critical: #ff6675;
  --critical-bg: #35181d;
  --major: #ffb454;
  --major-bg: #302315;
  --success: #62c87a;
  --success-bg: #14291a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 system-ui, sans-serif; }
button, input { font: inherit; }
a { color: var(--accent); }
.shell { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
.header { position: sticky; top: 0; z-index: 4; padding: 18px 24px; border-bottom: 1px solid var(--border); background: #111214f5; backdrop-filter: blur(12px); }
.header-row { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }
.eyebrow { color: var(--accent); font: 12px/1.3 ui-monospace, monospace; text-transform: uppercase; letter-spacing: .08em; }
h1 { margin: 5px 0 4px; font-size: 26px; line-height: 1.15; }
.summary { margin: 0; max-width: 920px; color: var(--muted); }
.progress { min-width: 160px; text-align: right; color: var(--muted); font: 12px/1.4 ui-monospace, monospace; }
.progress-track { margin-top: 8px; height: 5px; border-radius: 9px; background: var(--panel-2); overflow: hidden; }
.progress-fill { height: 100%; width: 0; background: var(--accent); transition: width .2s ease; }
.layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 0; transition: grid-template-columns .2s ease; }
.layout.full-width { grid-template-columns: minmax(0, 1fr); }
.nav { position: sticky; top: 111px; align-self: start; max-height: calc(100vh - 111px); overflow: auto; padding: 18px; border-right: 1px solid var(--border); }
.nav-title { color: var(--muted); font: 12px/1.3 ui-monospace, monospace; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 10px; }
.nav-list { display: grid; gap: 7px; }
.nav-step { border: 1px solid transparent; border-radius: 8px; padding: 10px 12px; background: transparent; color: var(--muted); text-align: left; cursor: pointer; }
.nav-step:hover, .nav-step:focus { border-color: var(--border); color: var(--text); outline: none; }
.nav-step[aria-current="step"] { border-color: var(--accent); background: #78a9ff14; color: var(--text); }
.nav-number { display: block; margin-bottom: 3px; color: var(--accent); font: 11px/1 ui-monospace, monospace; }
.main { width: min(1120px, 100%); margin: 0 auto; padding: 0 34px 56px; }
.tab-bar { position: sticky; top: 0; z-index: 3; display: flex; gap: 4px; padding: 16px 0 12px; background: var(--bg); border-bottom: 1px solid var(--border); margin-bottom: 26px; }
.tab-button { display: inline-flex; align-items: center; gap: 8px; border: 1px solid transparent; border-radius: 8px; padding: 8px 14px; background: transparent; color: var(--muted); font: 14px/1.3 system-ui, sans-serif; cursor: pointer; transition: all .15s ease; }
.tab-button:hover, .tab-button:focus { border-color: var(--border); color: var(--text); outline: none; }
.tab-button[aria-selected="true"] { border-color: var(--accent); background: #78a9ff14; color: var(--text); }
.tab-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px; font: 700 11px/1 ui-monospace, monospace; }
.tab-badge.has-findings { background: var(--critical-bg); color: var(--critical); }
.tab-badge.no-findings { background: var(--success-bg); color: var(--success); }
.tab-panel { display: none; }
.tab-panel[data-active="true"] { display: block; }
.findings-panel { padding: 4px 0 8px; max-width: 960px; }
.findings-header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.findings-title { margin: 0; font-size: 20px; }
.findings-count { color: var(--muted); font: 12px/1.4 ui-monospace, monospace; }
.findings-list { display: grid; gap: 16px; }
.finding { padding: 18px 22px; border: 1px solid var(--border); border-left-width: 4px; border-radius: 10px; background: var(--panel); }
.finding.critical { border-left-color: var(--critical); background: var(--critical-bg); }
.finding.major { border-left-color: var(--major); background: var(--major-bg); }
.finding-heading { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.finding-severity { font: 700 11px/1.3 ui-monospace, monospace; text-transform: uppercase; letter-spacing: .06em; }
.finding.critical .finding-severity { color: var(--critical); }
.finding.major .finding-severity { color: var(--major); }
.finding-title { margin: 0; font-size: 16px; }
.finding-location { margin: 5px 0 0; color: var(--muted); font: 12px/1.4 ui-monospace, monospace; }
.finding-body { margin: 12px 0; }
.finding-detail { margin: 7px 0 0; color: var(--muted); }
.finding-detail strong { color: var(--text); }
.findings-empty { margin: 0; padding: 14px 16px; border: 1px solid #315a3a; border-radius: 10px; color: var(--success); background: var(--success-bg); }
.interfaces-panel { padding: 4px 0 8px; max-width: 960px; }
.interfaces-header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.interfaces-title { margin: 0; font-size: 20px; }
.interfaces-count { color: var(--muted); font: 12px/1.4 ui-monospace, monospace; }
.interfaces-empty { margin: 0; padding: 14px 16px; border: 1px solid #315a3a; border-radius: 10px; color: var(--success); background: var(--success-bg); }
.interfaces-list { display: grid; gap: 14px; }
.iface-group-label { display: flex; align-items: center; gap: 8px; margin: 16px 0 8px; font: 700 13px/1.3 system-ui, sans-serif; color: var(--text); }
.iface-group-label:first-child { margin-top: 0; }
.iface-group-icon { font-size: 16px; }
.iface-card { padding: 16px 20px; border: 1px solid var(--border); border-left-width: 4px; border-radius: 10px; background: var(--panel); }
.iface-card[data-category="firestore"]  { border-left-color: #ff9100; }
.iface-card[data-category="grpc"]       { border-left-color: #78a9ff; }
.iface-card[data-category="http-api"]   { border-left-color: #62c87a; }
.iface-card[data-category="database"]   { border-left-color: #d4a5ff; }
.iface-card[data-category="storage"]    { border-left-color: #ffb454; }
.iface-card[data-category="messaging"]  { border-left-color: #ff6675; }
.iface-card[data-category="config"]     { border-left-color: #aeb5c2; }
.iface-file { margin: 0 0 4px; color: var(--accent); font: 12px/1.4 ui-monospace, monospace; }
.iface-desc { margin: 0; color: var(--muted); }
.iface-snippets { margin: 10px 0 0; display: grid; gap: 6px; }
.iface-snippet-label { font: 700 10px/1.3 ui-monospace, monospace; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
.iface-snippet-label.added { color: var(--add-border); }
.iface-snippet-label.removed { color: var(--remove-border); }
.iface-snippet-code { font: 12px/1.55 ui-monospace, monospace; white-space: pre-wrap; overflow-wrap: anywhere; padding: 8px 12px; border-radius: 6px; background: var(--panel-2); }
.iface-snippet-code.added { border-left: 3px solid var(--add-border); }
.iface-snippet-code.removed { border-left: 3px solid var(--remove-border); }
.step-label { color: var(--accent); font: 12px/1.3 ui-monospace, monospace; text-transform: uppercase; letter-spacing: .08em; }
.step-title { margin: 7px 0 8px; font-size: 30px; line-height: 1.15; }
.orientation { margin: 0 0 22px; max-width: 820px; color: var(--muted); font-size: 17px; }
.section { margin-top: 24px; }
.section-title { margin: 0 0 10px; font-size: 15px; }
.explanation { display: grid; gap: 8px; margin: 0; padding-left: 22px; }
.explanation li, .checks li { color: var(--muted); }
.diff-card { margin: 12px 0 20px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--context-bg); }
.diff-header { display: flex; justify-content: space-between; gap: 14px; padding: 11px 14px; border-bottom: 1px solid var(--border); background: var(--panel-2); font: 12px/1.4 ui-monospace, monospace; }
.diff-hunk { padding: 7px 14px; color: var(--accent); border-bottom: 1px solid var(--border); font: 12px/1.4 ui-monospace, monospace; }
.diff-lines { overflow-x: auto; }
.diff-line { display: grid; grid-template-columns: 54px 54px 24px minmax(max-content, 1fr); min-height: 25px; border-left: 3px solid transparent; font: 12px/1.55 ui-monospace, monospace; }
.diff-line.add { background: var(--add-bg); border-left-color: var(--add-border); }
.diff-line.remove { background: var(--remove-bg); border-left-color: var(--remove-border); }
.line-number { padding: 3px 8px; color: #77808f; text-align: right; user-select: none; }
.line-prefix { padding: 3px 4px; color: var(--muted); user-select: none; }
.line-code { padding: 3px 12px 3px 4px; white-space: pre; }
.examples { display: grid; gap: 12px; }
.example { border: 1px solid #30496d; border-radius: 10px; overflow: hidden; background: var(--example-bg); }
.example-title { padding: 10px 13px; color: #b9d2ff; border-bottom: 1px solid #30496d; font-weight: 650; }
.example-note { margin: 0; padding: 10px 13px 0; color: var(--muted); }
.example pre { margin: 0; padding: 13px; overflow-x: auto; color: #dbe8ff; font: 12px/1.55 ui-monospace, monospace; }
.checks { display: grid; gap: 8px; margin: 0; padding-left: 22px; }
.controls { display: flex; justify-content: space-between; gap: 12px; margin-top: 34px; padding-top: 20px; border-top: 1px solid var(--border); }
.control { border: 1px solid var(--border); border-radius: 8px; padding: 9px 14px; background: var(--panel-2); color: var(--text); cursor: pointer; }
.control:hover, .control:focus { border-color: var(--accent); outline: none; }
.control:disabled { opacity: .35; cursor: default; }
@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; }
  .nav { position: static; max-height: none; border-right: 0; border-bottom: 1px solid var(--border); }
  .nav-list { grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
  .main { padding: 24px 18px 44px; }
  .header-row { display: block; }
  .progress { margin-top: 12px; text-align: left; }
}
""".strip()


def runtime() -> str:
    return """
(() => {
  const data = JSON.parse(document.getElementById('walkthrough-data').textContent);
  let activeIndex = 0;
  const nav = document.querySelector('.nav-list');
  const content = document.querySelector('.step-content');
  const progressText = document.querySelector('.progress-text');
  const progressFill = document.querySelector('.progress-fill');
  const previous = document.querySelector('[data-action="previous"]');
  const next = document.querySelector('[data-action="next"]');
  const findingsContent = document.querySelector('.findings-content');
  const interfacesContent = document.querySelector('.interfaces-content');
  const tabButtons = document.querySelectorAll('.tab-button[role="tab"]');
  const tabPanels = document.querySelectorAll('.tab-panel[role="tabpanel"]');
  const findingsBadge = document.querySelector('.tab-badge:not(.iface-badge)');
  const ifaceBadge = document.querySelector('.iface-badge');
  const navEl = document.querySelector('.nav');

  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const renderList = (items, className) => {
    const list = element('ul', className);
    items.forEach(item => list.appendChild(element('li', '', item)));
    return list;
  };

  const renderDiff = diff => {
    const card = element('section', 'diff-card');
    const header = element('div', 'diff-header');
    const path = element('span', '', diff.file);
    header.appendChild(path);
    if (diff.url) {
      const link = element('a', '', 'Open in PR');
      link.href = diff.url;
      link.target = '_blank';
      link.rel = 'noreferrer';
      header.appendChild(link);
    }
    card.appendChild(header);
    if (diff.hunk) card.appendChild(element('div', 'diff-hunk', diff.hunk));
    const lines = element('div', 'diff-lines');
    diff.lines.forEach(line => {
      const row = element('div', `diff-line ${line.type || 'context'}`);
      row.appendChild(element('span', 'line-number', line.oldLine ?? ''));
      row.appendChild(element('span', 'line-number', line.newLine ?? ''));
      const prefix = line.type === 'add' ? '+' : line.type === 'remove' ? '−' : ' ';
      row.appendChild(element('span', 'line-prefix', prefix));
      row.appendChild(element('span', 'line-code', line.content));
      lines.appendChild(row);
    });
    card.appendChild(lines);
    return card;
  };

  const renderExample = example => {
    const card = element('section', 'example');
    card.appendChild(element('div', 'example-title', example.title));
    if (example.note) card.appendChild(element('p', 'example-note', example.note));
    const pre = element('pre');
    pre.appendChild(element('code', '', example.content));
    card.appendChild(pre);
    return card;
  };

  const renderFindings = () => {
    findingsContent.replaceChildren();
    const findings = data.findings || [];
    const header = element('div', 'findings-header');
    header.appendChild(element('h2', 'findings-title', 'Critical and major findings'));
    header.appendChild(element(
      'span',
      'findings-count',
      `${findings.length} finding${findings.length === 1 ? '' : 's'}`
    ));
    findingsContent.appendChild(header);

    if (!findings.length) {
      findingsContent.appendChild(element(
        'p',
        'findings-empty',
        'No critical or major findings were identified.'
      ));
      return;
    }

    const list = element('div', 'findings-list');
    findings.forEach(finding => {
      const card = element('article', `finding ${finding.severity}`);
      const heading = element('div', 'finding-heading');
      heading.appendChild(element('span', 'finding-severity', finding.severity));
      heading.appendChild(element('h3', 'finding-title', finding.title));
      card.appendChild(heading);
      const location = finding.line
        ? `${finding.file}:${finding.line}`
        : finding.file;
      card.appendChild(element('p', 'finding-location', location));
      card.appendChild(element('p', 'finding-body', finding.body));

      const evidence = element('p', 'finding-detail');
      evidence.appendChild(element('strong', '', 'Evidence: '));
      evidence.appendChild(document.createTextNode(finding.evidence));
      card.appendChild(evidence);

      const remediation = element('p', 'finding-detail');
      remediation.appendChild(element('strong', '', 'Remediation: '));
      remediation.appendChild(document.createTextNode(finding.remediation));
      card.appendChild(remediation);
      list.appendChild(card);
    });
    findingsContent.appendChild(list);
  };

  const CATEGORY_META = {
    'firestore': 'Firestore',
    'grpc': 'gRPC',
    'http-api': 'HTTP API',
    'database': 'Database',
    'storage': 'Storage',
    'messaging': 'Messaging',
    'config': 'Config',
  };

  const renderInterfaces = () => {
    interfacesContent.replaceChildren();
    const interfaces = data.interfaces || [];
    const header = element('div', 'interfaces-header');
    header.appendChild(element('h2', 'interfaces-title', 'Interface & adjacent-system changes'));
    header.appendChild(element(
      'span',
      'interfaces-count',
      `${interfaces.length} change${interfaces.length === 1 ? '' : 's'}`
    ));
    interfacesContent.appendChild(header);

    if (!interfaces.length) {
      interfacesContent.appendChild(element(
        'p',
        'interfaces-empty',
        'No Firestore, gRPC, HTTP, database, storage, or messaging changes detected.'
      ));
      return;
    }

    const groups = {};
    const order = [];
    interfaces.forEach(iface => {
      if (!groups[iface.category]) {
        groups[iface.category] = [];
        order.push(iface.category);
      }
      groups[iface.category].push(iface);
    });

    const list = element('div', 'interfaces-list');
    order.forEach(cat => {
      const label = element('div', 'iface-group-label');
      label.appendChild(document.createTextNode(`${CATEGORY_META[cat] || cat} (${groups[cat].length})`));
      list.appendChild(label);

      groups[cat].forEach(iface => {
        const card = element('article', 'iface-card');
        card.dataset.category = cat;
        card.appendChild(element('p', 'iface-file', iface.file));
        card.appendChild(element('p', 'iface-desc', iface.description));

        const added = iface.addedLines || [];
        const removed = iface.removedLines || [];
        if (added.length || removed.length) {
          const snippets = element('div', 'iface-snippets');
          if (added.length) {
            snippets.appendChild(element('div', 'iface-snippet-label added', 'Added'));
            const code = element('div', 'iface-snippet-code added');
            code.textContent = added.map(l => '+ ' + l).join('\\n');
            snippets.appendChild(code);
          }
          if (removed.length) {
            snippets.appendChild(element('div', 'iface-snippet-label removed', 'Removed'));
            const code = element('div', 'iface-snippet-code removed');
            code.textContent = removed.map(l => '- ' + l).join('\\n');
            snippets.appendChild(code);
          }
          card.appendChild(snippets);
        }

        list.appendChild(card);
      });
    });
    interfacesContent.appendChild(list);
  };

  const renderStep = () => {
    const step = data.steps[activeIndex];
    content.replaceChildren();
    content.appendChild(element('div', 'step-label', `Step ${activeIndex + 1} of ${data.steps.length} · ${step.kind || 'code path'}`));
    content.appendChild(element('h2', 'step-title', step.title));
    content.appendChild(element('p', 'orientation', step.orientation));

    const diffSection = element('section', 'section');
    diffSection.appendChild(element('h3', 'section-title', 'Relevant code diff'));
    step.diffs.forEach(diff => diffSection.appendChild(renderDiff(diff)));
    content.appendChild(diffSection);

    const explanationSection = element('section', 'section');
    explanationSection.appendChild(element('h3', 'section-title', 'How this works'));
    explanationSection.appendChild(renderList(step.explanation, 'explanation'));
    content.appendChild(explanationSection);

    if ((step.productionExamples || []).length) {
      const examplesSection = element('section', 'section');
      examplesSection.appendChild(element('h3', 'section-title', 'Production-shaped example'));
      const examples = element('div', 'examples');
      step.productionExamples.forEach(example => examples.appendChild(renderExample(example)));
      examplesSection.appendChild(examples);
      content.appendChild(examplesSection);
    }

    const checksSection = element('section', 'section');
    checksSection.appendChild(element('h3', 'section-title', 'What to verify as reviewer'));
    checksSection.appendChild(renderList(step.reviewChecks, 'checks'));
    content.appendChild(checksSection);

    document.querySelectorAll('.nav-step').forEach((button, index) => {
      button.setAttribute('aria-current', index === activeIndex ? 'step' : 'false');
    });
    progressText.textContent = `Step ${activeIndex + 1} / ${data.steps.length}`;
    progressFill.style.width = `${((activeIndex + 1) / data.steps.length) * 100}%`;
    previous.disabled = activeIndex === 0;
    next.disabled = activeIndex === data.steps.length - 1;
    document.title = `${activeIndex + 1}/${data.steps.length} · ${step.title}`;
    window.scrollTo({ top: 0, behavior: 'instant' });
  };

  data.steps.forEach((step, index) => {
    const button = element('button', 'nav-step');
    button.type = 'button';
    button.dataset.stepIndex = String(index);
    button.appendChild(element('span', 'nav-number', `STEP ${index + 1}`));
    button.appendChild(document.createTextNode(step.title));
    button.addEventListener('click', () => { activeIndex = index; renderStep(); });
    nav.appendChild(button);
  });

  previous.addEventListener('click', () => {
    if (activeIndex > 0) { activeIndex -= 1; renderStep(); }
  });
  next.addEventListener('click', () => {
    if (activeIndex < data.steps.length - 1) { activeIndex += 1; renderStep(); }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key.toLowerCase() === 'n') next.click();
    if (event.key === 'ArrowLeft' || event.key.toLowerCase() === 'p') previous.click();
  });

  const layoutEl = document.querySelector('.layout');
  const switchTab = tabId => {
    tabButtons.forEach(btn => btn.setAttribute('aria-selected', btn.dataset.tab === tabId ? 'true' : 'false'));
    tabPanels.forEach(panel => panel.dataset.active = panel.id === `panel-${tabId}` ? 'true' : 'false');
    navEl.style.display = tabId === 'steps' ? '' : 'none';
    layoutEl.classList.toggle('full-width', tabId !== 'steps');
    window.scrollTo({ top: 0, behavior: 'instant' });
  };
  tabButtons.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));

  const findingsCount = (data.findings || []).length;
  findingsBadge.textContent = String(findingsCount);
  findingsBadge.className = `tab-badge ${findingsCount > 0 ? 'has-findings' : 'no-findings'}`;

  const ifaceCount = (data.interfaces || []).length;
  ifaceBadge.textContent = String(ifaceCount);
  ifaceBadge.className = `tab-badge iface-badge ${ifaceCount > 0 ? 'has-findings' : 'no-findings'}`;

  renderFindings();
  renderInterfaces();
  renderStep();
  switchTab('findings');
  document.body.classList.add('walkthrough-ready');
})();
""".strip()


def html_template(data: dict) -> str:
    errors = validate_data(data)
    if errors:
        raise ValueError("\n".join(errors))
    meta = data["meta"]
    data_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: file:; connect-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
  <title>{html.escape(meta["title"])}</title>
  <style>{css()}</style>
</head>
<body>
  <main class="shell">
    <header class="header">
      <div class="header-row">
        <div>
          <div class="eyebrow">Guided pull request review · {html.escape(meta["baseRef"])} ← {html.escape(meta["headRef"])}</div>
          <h1>{html.escape(meta["title"])}</h1>
          <p class="summary">{html.escape(meta["summary"])}</p>
        </div>
        <div class="progress">
          <a href="{html.escape(meta["prUrl"])}" target="_blank" rel="noreferrer">Open pull request</a>
          <div class="progress-text"></div>
          <div class="progress-track"><div class="progress-fill"></div></div>
        </div>
      </div>
    </header>
    <div class="layout">
      <nav class="nav" aria-label="Review steps">
        <div class="nav-title">Review path</div>
        <div class="nav-list"></div>
      </nav>
      <article class="main">
        <div class="tab-bar" role="tablist" aria-label="View">
          <button class="tab-button" role="tab" data-tab="steps" aria-selected="false" aria-controls="panel-steps">Steps</button>
          <button class="tab-button" role="tab" data-tab="findings" aria-selected="true" aria-controls="panel-findings">Findings <span class="tab-badge"></span></button>
          <button class="tab-button" role="tab" data-tab="interfaces" aria-selected="false" aria-controls="panel-interfaces">Interfaces <span class="tab-badge iface-badge"></span></button>
        </div>
        <div class="tab-panel" id="panel-steps" role="tabpanel" data-active="false">
          <div class="step-content"></div>
          <div class="controls">
            <button class="control" type="button" data-action="previous">Previous step</button>
            <button class="control" type="button" data-action="next">Next step</button>
          </div>
        </div>
        <div class="tab-panel" id="panel-findings" role="tabpanel" data-active="true">
          <section class="findings-panel" aria-label="Critical and major findings">
            <div class="findings-content"></div>
          </section>
        </div>
        <div class="tab-panel" id="panel-interfaces" role="tabpanel" data-active="false">
          <section class="interfaces-panel" aria-label="Interface and adjacent-system changes">
            <div class="interfaces-content"></div>
          </section>
        </div>
      </article>
    </div>
  </main>
  <script id="walkthrough-data" type="application/json">{data_json}</script>
  <script>{runtime()}</script>
</body>
</html>"""


def extract_data(html_text: str) -> dict:
    parser = DataExtractor()
    parser.feed(html_text)
    return json.loads("".join(parser.parts))


def static_validate(html_text: str) -> tuple[dict, list[str]]:
    errors: list[str] = []
    parser = DataExtractor()
    parser.feed(html_text)
    if parser.asset_reference:
        errors.append("HTML contains a runtime asset reference")
    if "connect-src 'none'" not in html_text:
        errors.append("CSP does not block runtime network connections")
    for network_api in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon"):
        if network_api in "".join(parser.runtime_parts):
            errors.append(f"HTML uses network API: {network_api}")
    try:
        data = extract_data(html_text)
    except Exception as exc:
        return {}, errors + [f"Cannot extract walkthrough data: {exc}"]
    errors.extend(validate_data(data))
    for label in (
        "Relevant code diff",
        "How this works",
        "What to verify as reviewer",
        "Critical and major findings",
        "Interface & adjacent-system changes",
        "Previous step",
        "Next step",
    ):
        if label not in html_text:
            errors.append(f"Missing UI label: {label}")
    return data, errors


def browser_validate(html_path: Path) -> tuple[bool, str]:
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError as exc:
        return False, f"Playwright is unavailable: {exc}"
    with sync_playwright() as playwright:
        browser = None
        errors: list[str] = []
        for label, options in (
            ("bundled Chromium", {}),
            ("system Chrome", {"channel": "chrome"}),
            ("system Chromium", {"channel": "chromium"}),
        ):
            try:
                browser = playwright.chromium.launch(**options)
                break
            except PlaywrightError as exc:
                errors.append(f"{label}: {exc}")
        if browser is None:
            return False, "Unable to launch browser: " + " | ".join(errors)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
            page.wait_for_selector("body.walkthrough-ready")
            if not page.locator(".findings-panel").is_visible():
                return False, "Review findings are not initially visible"
            page.locator('[data-tab="steps"]').click()
            count = page.locator(".nav-step").count()
            steps = extract_data(html_path.read_text())["steps"]
            if count != len(steps) or count == 0:
                return False, "Step navigation does not match walkthrough data"
            for index, step in enumerate(steps):
                if index:
                    page.locator('[data-action="next"]').click()
                if page_errors:
                    return False, "Browser JavaScript errors: " + " | ".join(page_errors)
                if page.locator(".nav-step").nth(index).get_attribute("aria-current") != "step":
                    return False, f"Step {index + 1} navigation did not advance"
                if page.locator(".diff-card").count() != len(step["diffs"]):
                    return False, f"Step {index + 1} code diffs did not render"
                if page.locator(".example").count() != len(step.get("productionExamples", [])):
                    return False, f"Step {index + 1} examples did not render"
            findings_panel_count = page.locator(".findings-panel").count()
            interfaces_panel_count = page.locator(".interfaces-panel").count()
            tab_count = page.locator('.tab-button[role="tab"]').count()
            navigation_works = page.locator('[data-action="next"]').is_disabled()
        except (PlaywrightError, OSError, ValueError) as exc:
            return False, f"Browser validation failed: {exc}"
        finally:
            browser.close()
    if count < 1 or not navigation_works:
        return False, "Step navigation did not advance"
    if findings_panel_count != 1:
        return False, "Review findings section did not render"
    if interfaces_panel_count != 1:
        return False, "Interfaces panel did not render"
    if tab_count != 3:
        return False, "Tab bar did not render all three tabs"
    return True, f"rendered {count} steps with working navigation, diffs, and examples"


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", action="store_true")
    group.add_argument("--validate", action="store_true")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--require-browser", action="store_true")
    args = parser.parse_args()

    if args.template:
        if args.data is None:
            parser.error("--template requires --data")
        print(html_template(json.loads(args.data.read_text())))
        return 0

    if args.html is None:
        parser.error("--validate requires --html")
    html_text = args.html.read_text()
    data, errors = static_validate(html_text)
    if errors:
        for error in errors:
            print(f"FAIL - {error}")
        return 1
    print(f"Static validation passed: {len(data['steps'])} guided step(s).")
    passed, message = browser_validate(args.html)
    if passed:
        print(f"PASS - browser {message}")
        return 0
    prefix = "FAIL" if args.require_browser else "WARN"
    print(f"{prefix} - {message}")
    return 1 if args.require_browser else 0


if __name__ == "__main__":
    raise SystemExit(main())
