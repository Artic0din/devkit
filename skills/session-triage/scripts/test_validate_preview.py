"""Run directly to check preview scope and archive safeguards with synthetic data."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from validate_preview import validate_preview


def preview() -> dict:
    return {
        "schema_version": 1, "mode": "preview", "window_days": 7,
        "generated_at": "2026-09-25T10:00:00+10:00",
        "cutoff": "2026-09-19T00:00:00+10:00",
        "coverage": {
            "eligible_threads": 1, "audited_threads": 1, "unreadable_threads": 0,
            "archive_candidates": 1, "new_task_candidates": 0,
            "verified_knowledge_candidates": 0,
        },
        "validation": {
            "status": "pending", "eligible_roster_complete": True,
            "dedupe_checks_complete": True, "primary_source_checks_complete": True,
        },
        "threads": [{
            "id": "synthetic", "host_id": "local", "kind": "codex", "status": "idle",
            "updated_at": "2026-09-24T10:00:00+10:00",
            "observed_updated_at": "2026-09-24T10:00:00+10:00",
            "current_title": "Example", "proposed_title": "Example done",
            "outcome": "verified_complete", "evidence": ["Synthetic check passed"],
            "project": {
                "name": None, "cwd": None, "repo": None,
                "mapping_status": "unmapped", "apply_support": "unsupported",
            },
            "unreadable": False, "blocker": None, "archive_candidate": True,
            "unresolved_outcomes": [], "task_candidates": [], "knowledge_candidates": [],
        }],
    }


def test_host_identity() -> None:
    for value in (None, "", " ", 1, [], {}):
        invalid = preview()
        invalid["threads"][0]["host_id"] = value
        assert "threads[0].host_id is required" in validate_preview(invalid), value
    invalid = preview()
    del invalid["threads"][0]["host_id"]
    assert "threads[0].host_id is required" in validate_preview(invalid)


def test_project_metadata() -> None:
    for mapping in ("mapped", "unmapped"):
        valid = preview()
        valid["threads"][0]["project"].update(
            mapping_status=mapping, name="Example", cwd="/tmp/example", repo="owner/example",
        )
        assert not validate_preview(valid), validate_preview(valid)
        for field in ("name", "cwd", "repo"):
            invalid = deepcopy(valid)
            del invalid["threads"][0]["project"][field]
            assert any(f"project.{field}" in error for error in validate_preview(invalid)), (mapping, field)
            for value in (None, "", " ", 1, [], {}):
                invalid = deepcopy(valid)
                invalid["threads"][0]["project"][field] = value
                errors = validate_preview(invalid)
                if mapping == "unmapped" and value is None:
                    assert not errors, errors
                else:
                    assert any(f"project.{field}" in error for error in errors), (mapping, field, value)
        invalid = deepcopy(valid)
        invalid["threads"][0]["project"]["repo"] = "not-a-repository"
        assert any("project.repo" in error for error in validate_preview(invalid)), mapping


def test_invalid_utf8_cli() -> None:
    with TemporaryDirectory() as directory:
        source = Path(directory) / "preview.json"
        source.write_bytes(b'\xff')
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("validate_preview.py")), str(source)],
            capture_output=True, text=True, check=False,
        )
    assert result.returncode == 1, result
    assert result.stderr.startswith("INVALID:"), result.stderr
    assert "Traceback" not in result.stderr, result.stderr


def task_preview() -> dict:
    value = preview()
    thread = value["threads"][0]
    thread["archive_candidate"] = False
    thread["project"].update(mapping_status="mapped", name="Example", cwd="/tmp/example", repo="owner/project")
    thread["task_candidates"] = [{
        "status": "new", "title": "Example", "repo": "owner/project",
        "body": "## Context\nEvidence\n## Goal\nOutcome\n## Acceptance criteria\n- [ ] Verified\n## Technical notes\nConstraints\n<!-- session-triage:synthetic:example -->",
        "evidence": ["Synthetic evidence"], "marker": "<!-- session-triage:synthetic:example -->",
        "dedupe": {"checked": True, "existing_url": None, "reason": "No matching issue"},
    }]
    value["coverage"].update(archive_candidates=0, new_task_candidates=1)
    return value


def test_task_repository() -> None:
    value = task_preview()
    assert not validate_preview(value), validate_preview(value)
    value["threads"][0]["task_candidates"][0]["repo"] = "OWNER/Project"
    assert not validate_preview(value), validate_preview(value)
    value["threads"][0]["task_candidates"][0]["repo"] = "other/project"
    assert any("must match the mapped project" in error for error in validate_preview(value))


def test_unreadable_mutations() -> None:
    for candidate_type in ("task", "knowledge"):
        value = task_preview()
        thread = value["threads"][0]
        thread.update(unreadable=True, blocker="Cannot read source", outcome="blocked")
        thread["proposed_title"] = thread["current_title"]
        value["coverage"].update(audited_threads=0, unreadable_threads=1)
        expected = "threads[0] unreadable thread cannot propose new tasks"
        if candidate_type == "knowledge":
            thread["task_candidates"] = []
            thread["knowledge_candidates"] = [{
                "status": "verified", "target_note": "Example", "proposed_content": "Example fact",
                "primary_sources": ["Synthetic source"], "reason": "Verified fixture",
                "edit_operation": "append",
            }]
            value["coverage"].update(new_task_candidates=0, verified_knowledge_candidates=1)
            expected = "threads[0] unreadable thread cannot propose verified knowledge"
        assert validate_preview(value) == [expected], (candidate_type, validate_preview(value))


def test_task_publication_payload() -> None:
    for body in (None, "", "Unstructured issue"):
        value = task_preview()
        value["threads"][0]["task_candidates"][0]["body"] = body
        assert any("body" in error for error in validate_preview(value)), body
    value = task_preview()
    candidate = value["threads"][0]["task_candidates"][0]
    value["threads"][0]["task_candidates"].append(deepcopy(candidate))
    value["coverage"]["new_task_candidates"] = 2
    assert any("duplicate task marker" in error for error in validate_preview(value))
    value["threads"][0]["task_candidates"][1]["marker"] = "<!-- session-triage:synthetic:second -->"
    value["threads"][0]["task_candidates"][1]["body"] = candidate["body"].replace(":example -->", ":second -->")
    assert not validate_preview(value), validate_preview(value)


def test_unreadable_title_unchanged() -> None:
    value = preview()
    thread = value["threads"][0]
    thread.update(unreadable=True, blocker="Cannot read source", outcome="unclear", archive_candidate=False)
    value["coverage"].update(audited_threads=0, unreadable_threads=1, archive_candidates=0)
    assert "threads[0] unreadable thread must keep its current title" in validate_preview(value)
    thread["proposed_title"] = thread["current_title"]
    assert not validate_preview(value), validate_preview(value)


def test_empty_issue_sections() -> None:
    marker = "<!-- session-triage:synthetic:example -->"
    for body in (
        "## Context\n## Goal\n## Acceptance criteria\n## Technical notes\n" + marker,
        "## Context\nEvidence\n## Goal\nOutcome\n## Acceptance criteria\nNone\n## Technical notes\nConstraints\n" + marker,
        "## Context\nEvidence\n## Goal\nOutcome\n## Acceptance criteria\n- [ ] Verified\n## Technical notes\n" + marker,
        "## Context\nEvidence\n## Goal\nOutcome\n## Acceptance criteria\n- [ ]\n## Technical notes\nConstraints\n" + marker,
    ):
        value = task_preview()
        value["threads"][0]["task_candidates"][0]["body"] = body
        assert any("section must not be empty" in error or "at least one criterion" in error
                   for error in validate_preview(value)), body
    value = task_preview()
    candidate = value["threads"][0]["task_candidates"][0]
    candidate["body"] = candidate["body"].replace("\n", "\r\n")
    assert not validate_preview(value), validate_preview(value)


def test_existing_url() -> None:
    for status in ("duplicate", "completed"):
        for url in ("not a URL", "github.com/owner/project/issues/1", "http://github.com/owner/project/issues/1", "https://",
                    "https://[abc", "https://@", "https://user@", "https://:443"):
            value = task_preview()
            value["threads"][0]["task_candidates"][0].update(status=status)
            value["threads"][0]["task_candidates"][0]["dedupe"]["existing_url"] = url
            value["coverage"]["new_task_candidates"] = 0
            assert any("existing_url" in error for error in validate_preview(value)), (status, url)
        value["threads"][0]["task_candidates"][0]["dedupe"]["existing_url"] = "https://github.com/owner/project/issues/1"
        assert not validate_preview(value), validate_preview(value)


def test_knowledge_edit_operation() -> None:
    value = preview()
    value["threads"][0]["knowledge_candidates"] = [{
        "status": "verified", "target_note": "Example", "proposed_content": "Example fact",
        "primary_sources": ["Synthetic source"], "reason": "Verified fixture",
    }]
    value["coverage"]["verified_knowledge_candidates"] = 1
    candidate = value["threads"][0]["knowledge_candidates"][0]
    for operation in (None, "", "edit", []):
        candidate["edit_operation"] = operation
        assert any("edit_operation" in error for error in validate_preview(value)), operation
    candidate["edit_operation"] = "replace_section"
    assert any("target_section" in error for error in validate_preview(value))
    candidate["target_section"] = "Facts"
    assert not validate_preview(value), validate_preview(value)
    for operation in ("create", "append"):
        candidate["edit_operation"] = operation
        assert not validate_preview(value), validate_preview(value)


if __name__ == "__main__":
    test_host_identity()
    test_project_metadata()
    test_invalid_utf8_cli()
    test_task_repository()
    test_unreadable_mutations()
    test_task_publication_payload()
    test_unreadable_title_unchanged()
    test_empty_issue_sections()
    test_existing_url()
    test_knowledge_edit_operation()
    valid = preview()
    assert not validate_preview(valid)
    invalid = deepcopy(valid)
    invalid["generated_at"] = "0001-01-01T00:00:00+14:00"
    assert validate_preview(invalid), "Timezone overflow must be a validation error"
    custom = deepcopy(valid)
    custom["window_days"] = 14
    custom["cutoff"] = "2026-09-12T00:00:00+10:00"
    assert not validate_preview(custom), validate_preview(custom)
    for window in (0, -1, True, "7"):
        invalid = deepcopy(valid)
        invalid["window_days"] = window
        assert validate_preview(invalid), window
    for state in (None, "active", "inProgress", "unknown"):
        invalid = deepcopy(valid)
        invalid["threads"][0]["status"] = state
        assert validate_preview(invalid), state
    invalid = deepcopy(valid)
    del invalid["threads"][0]["status"]
    assert validate_preview(invalid)
    invalid = deepcopy(valid)
    invalid["threads"][0]["updated_at"] = "2026-09-01T10:00:00+10:00"
    invalid["threads"][0]["observed_updated_at"] = invalid["threads"][0]["updated_at"]
    assert validate_preview(invalid), "Out-of-window session was accepted"
    for observed in (1, "invalid", "2026-09-23T10:00:00+10:00"):
        invalid = deepcopy(valid)
        invalid["threads"][0]["observed_updated_at"] = observed
        assert validate_preview(invalid), observed
    invalid = deepcopy(valid)
    invalid["threads"][0].update(unreadable=True, blocker="Cannot read session")
    invalid["threads"][0]["proposed_title"] = invalid["threads"][0]["current_title"]
    invalid["coverage"].update(audited_threads=0, unreadable_threads=1)
    assert validate_preview(invalid) == ["threads[0] archive candidate must be explicitly readable"], validate_preview(invalid)
    for field in ("outcome",):
        invalid = deepcopy(valid)
        invalid["threads"][0][field] = []
        assert validate_preview(invalid)
    for field in ("mapping_status", "apply_support"):
        invalid = deepcopy(valid)
        invalid["threads"][0]["project"][field] = {}
        assert validate_preview(invalid)
    invalid = deepcopy(valid)
    invalid["validation"]["status"] = []
    assert validate_preview(invalid)
    invalid = deepcopy(valid)
    invalid["cutoff"] = "2026-09-01T00:00:00+10:00"
    assert validate_preview(invalid), "Declared window and cutoff disagree"
    for field in ("task_candidates", "knowledge_candidates"):
        invalid = deepcopy(valid)
        invalid["threads"][0][field] = [{"status": []}]
        assert validate_preview(invalid)
    for evidence in ([None], [""], [{}]):
        invalid = deepcopy(valid)
        invalid["threads"][0]["evidence"] = evidence
        assert validate_preview(invalid), evidence
    for unreadable in (None, "true"):
        invalid = deepcopy(valid)
        invalid["threads"][0].update(unreadable=unreadable, archive_candidate=False)
        invalid["coverage"]["archive_candidates"] = 0
        assert validate_preview(invalid), unreadable
    print("PASS: window, archive, metadata, and invalid UTF-8 safeguards")
