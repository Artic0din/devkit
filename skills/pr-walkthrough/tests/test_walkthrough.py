"""Synthetic checks; never read a real pull request or launch a saved profile."""

import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("walkthrough", SKILL / "scripts/linear_walkthrough.py")
walkthrough = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(walkthrough)


def example() -> dict:
    source = re.search(r"```json\n(.*?)\n```", (SKILL / "SKILL.md").read_text(), re.S)
    return json.loads(source.group(1))


def test_rendered_data_roundtrips_and_escapes_markup():
    data = example()
    data["meta"]["summary"] = "</script><img src=x onerror=alert(1)>"
    rendered = walkthrough.html_template(data)
    assert walkthrough.extract_data(rendered) == data
    assert "<img src=x" not in rendered


def test_code_examples_do_not_count_as_runtime_network_calls():
    data = example()
    data["steps"][0]["diffs"][0]["lines"][0]["content"] = 'fetch("https://example.invalid")'
    assert walkthrough.static_validate(walkthrough.html_template(data))[1] == []


def test_script_urls_are_rejected():
    data = example()
    data["meta"]["prUrl"] = "javascript:alert(1)"
    assert walkthrough.validate_data(data)


def test_findings_are_initially_selected():
    rendered = walkthrough.html_template(example())
    assert 'data-tab="findings" aria-selected="true"' in rendered
    assert 'id="panel-findings" role="tabpanel" data-active="true"' in rendered


def test_single_step_browser_validation(tmp_path):
    pytest.importorskip("playwright")
    path = tmp_path / "index.html"
    path.write_text(walkthrough.html_template(example()))
    passed, message = walkthrough.browser_validate(path)
    assert passed, message


def test_same_title_steps_still_navigate(tmp_path):
    pytest.importorskip("playwright")
    data = example()
    second = deepcopy(data["steps"][0])
    second["id"] += "-second"
    data["steps"].append(second)
    path = tmp_path / "index.html"
    path.write_text(walkthrough.html_template(data))
    passed, message = walkthrough.browser_validate(path)
    assert passed, message


def test_broken_third_step_fails_browser_validation(tmp_path):
    pytest.importorskip("playwright")
    data = example()
    for suffix in ("-second", "-third"):
        step = deepcopy(data["steps"][0])
        step["id"] += suffix
        data["steps"].append(step)
    rendered = walkthrough.html_template(data)
    data["steps"][2]["explanation"] = None
    path = tmp_path / "index.html"
    path.write_text(rendered.replace(json.dumps(walkthrough.extract_data(rendered)), json.dumps(data)))
    passed, message = walkthrough.browser_validate(path)
    assert not passed, message


@pytest.mark.parametrize("field", ["diffs", "explanation", "reviewChecks", "productionExamples"])
@pytest.mark.parametrize("value", [None, "invalid", {"invalid": True}])
def test_step_collections_reject_non_arrays(field, value):
    data = example()
    data["steps"][0][field] = value
    assert walkthrough.validate_data(data)


@pytest.mark.parametrize("field", ["diffs", "productionExamples"])
def test_step_collections_reject_non_objects(field):
    data = example()
    data["steps"][0][field] = [None]
    assert walkthrough.validate_data(data)


def test_diff_lines_reject_non_objects():
    data = example()
    data["steps"][0]["diffs"][0]["lines"] = [None]
    assert walkthrough.validate_data(data)


def test_missing_browser_page_returns_failure(tmp_path):
    pytest.importorskip("playwright")
    passed, message = walkthrough.browser_validate(tmp_path / "missing.html")
    assert not passed
    assert "ERR_FILE_NOT_FOUND" in message


def test_required_review_content():
    data = example()
    del data["interfaces"]
    assert walkthrough.validate_data(data)
    data = example()
    for line in data["steps"][0]["diffs"][0]["lines"]:
        line["type"] = "context"
    assert walkthrough.validate_data(data)
    data = example()
    data["steps"][0]["productionExamples"] = [{}]
    assert walkthrough.validate_data(data)


@pytest.mark.parametrize("value", [None, [], "invalid", 1])
def test_json_root_must_be_object(value):
    assert walkthrough.validate_data(value) == ["Walkthrough data must be an object"]


@pytest.mark.parametrize("url", ["https://:443", "https://@", "https://user@/x", "https://[abc"])
def test_hostless_or_malformed_links_are_rejected(url):
    data = example()
    data["meta"]["prUrl"] = url
    assert walkthrough.validate_data(data)


def test_plaintext_http_links_are_rejected():
    data = example()
    data["meta"]["prUrl"] = "http://github.com/example/project/pull/123"
    assert walkthrough.validate_data(data)
    data = example()
    data["steps"][0]["diffs"][0]["url"] = "http://github.com/example/project/pull/123/files"
    assert walkthrough.validate_data(data)


@pytest.mark.parametrize("field", ["title", "body", "file", "evidence", "remediation"])
@pytest.mark.parametrize("value", [1, {"reason": "x"}, ["x"], "   "])
def test_finding_text_fields_must_be_nonblank_strings(field, value):
    data = example()
    data["findings"][0][field] = value
    assert walkthrough.validate_data(data)


@pytest.mark.parametrize("field", ["explanation", "reviewChecks"])
@pytest.mark.parametrize("value", [[], [""], ["  "], [1], [None]])
def test_step_guidance_needs_nonblank_strings(field, value):
    data = example()
    data["steps"][0][field] = value
    assert walkthrough.validate_data(data)


@pytest.mark.parametrize(
    "line",
    [
        {"type": "add"},
        {"type": "add", "content": "x"},
        {"type": "add", "content": 1, "newLine": 11},
        {"type": "add", "content": "x", "newLine": "11"},
        {"type": "add", "content": "x", "newLine": True},
        {"type": "remove", "content": "x", "newLine": 11},
    ],
)
def test_changed_lines_need_content_and_line_number(line):
    data = example()
    data["steps"][0]["diffs"][0]["lines"] = [line]
    assert walkthrough.validate_data(data)


def test_valid_changed_lines_pass():
    data = example()
    data["steps"][0]["diffs"][0]["lines"] = [
        {"type": "add", "oldLine": None, "newLine": 11, "content": ""},
        {"type": "remove", "oldLine": 10, "newLine": None, "content": "x"},
    ]
    assert walkthrough.validate_data(data) == []


def run_cli(*args: str) -> int:
    import sys
    from unittest import mock

    with mock.patch.object(sys, "argv", ["linear_walkthrough.py", *map(str, args)]):
        try:
            return walkthrough.main()
        except SystemExit as exc:
            return exc.code


def test_validate_requires_context_data(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(walkthrough.html_template(example()))
    assert run_cli("--validate", "--html", html_path) != 0


def test_validate_rejects_stale_context(tmp_path, capsys):
    html_path = tmp_path / "index.html"
    html_path.write_text(walkthrough.html_template(example()))
    edited = example()
    edited["meta"]["summary"] = "Edited after rendering"
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(edited))
    assert run_cli("--validate", "--html", html_path, "--data", context_path) == 1
    assert "context.json does not match" in capsys.readouterr().out


def test_validate_accepts_matching_context(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(walkthrough.html_template(example()))
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(example()))
    assert run_cli("--validate", "--html", html_path, "--data", context_path) == 0


@pytest.mark.parametrize("field", ["title", "orientation"])
@pytest.mark.parametrize("value", [None, "", "  ", 1])
def test_step_heading_fields_need_nonblank_strings(field, value):
    data = example()
    data["steps"][0][field] = value
    assert walkthrough.validate_data(data)


def test_csp_check_reads_the_policy_not_review_text():
    data = example()
    data["steps"][0]["diffs"][0]["lines"][0]["content"] = "connect-src 'none'"
    rendered = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', "", walkthrough.html_template(data))
    assert "CSP does not block runtime network connections" in walkthrough.static_validate(rendered)[1]


def test_modified_shortcuts_keep_the_current_step(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    data = example()
    second = deepcopy(data["steps"][0])
    second["id"] += "-second"
    data["steps"].append(second)
    path = tmp_path / "index.html"
    path.write_text(walkthrough.html_template(data))
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(path.as_uri())
            page.wait_for_selector("body.walkthrough-ready")
            page.locator('[data-tab="steps"]').click()
            first = page.locator(".nav-step").nth(0)
            for shortcut in ("Shift+ArrowRight", "Control+ArrowRight", "Alt+n", "Meta+n"):
                page.keyboard.press(shortcut)
                assert first.get_attribute("aria-current") == "step", shortcut
            page.keyboard.press("ArrowRight")
            assert page.locator(".nav-step").nth(1).get_attribute("aria-current") == "step"
        finally:
            browser.close()


@pytest.mark.parametrize(
    "change",
    [
        {"file": ""},
        {"description": "  "},
        {"file": None},
        {"addedLines": [{}]},
        {"removedLines": [1]},
    ],
)
def test_interface_fields_need_nonblank_strings(change):
    data = example()
    data["interfaces"] = [
        {"category": "grpc", "file": "api/service.proto", "description": "Adds a field.", "addedLines": ["int32 id = 1;"]}
    ]
    assert walkthrough.validate_data(data) == []
    data["interfaces"][0].update(change)
    assert walkthrough.validate_data(data)
