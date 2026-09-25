"""Run directly to check preview scope and archive safeguards with synthetic data."""

from copy import deepcopy

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
            "id": "synthetic", "kind": "codex", "status": "idle",
            "updated_at": "2026-09-24T10:00:00+10:00",
            "observed_updated_at": "2026-09-24T10:00:00+10:00",
            "current_title": "Example", "proposed_title": "Example done",
            "outcome": "verified_complete", "evidence": ["Synthetic check passed"],
            "project": {"mapping_status": "unmapped", "apply_support": "unsupported"},
            "unreadable": False, "blocker": None, "archive_candidate": True,
            "unresolved_outcomes": [], "task_candidates": [], "knowledge_candidates": [],
        }],
    }


if __name__ == "__main__":
    valid = preview()
    assert not validate_preview(valid)
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
    invalid["coverage"].update(audited_threads=0, unreadable_threads=1)
    assert validate_preview(invalid), "Unreadable session was accepted for archive"
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
    print("PASS: default/custom window and known-idle archive safeguards")
