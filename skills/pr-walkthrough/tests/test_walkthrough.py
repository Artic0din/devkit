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
