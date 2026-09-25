#!/usr/bin/env python3
"""Validate a session-triage preview before presentation or mutation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

OUTCOMES = {"verified_complete", "partial", "blocked", "active", "unclear"}
TASK_STATUSES = {"new", "duplicate", "completed", "blocked"}
KNOWLEDGE_STATUSES = {"verified", "rejected"}
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MARKER_PATTERN = re.compile(r"^<!-- session-triage:[A-Za-z0-9-]+:[A-Za-z0-9._-]+ -->$")


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_timestamp(value: Any) -> bool:
    if not _has_text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_task(
    task: Any,
    thread_id: str,
    mapping_status: str,
    project_repository: str | None,
    path: str,
    errors: list[str],
) -> None:
    _require(isinstance(task, dict), f"{path} must be an object", errors)
    if not isinstance(task, dict):
        return

    status = task.get("status")
    evidence = task.get("evidence")
    dedupe = task.get("dedupe")
    marker = task.get("marker")
    _require(_has_text(task.get("title")), f"{path}.title is required", errors)
    _require(isinstance(status, str) and status in TASK_STATUSES, f"{path}.status is invalid", errors)
    _require(
        isinstance(evidence, list)
        and bool(evidence)
        and all(_has_text(item) for item in evidence),
        f"{path}.evidence must contain source evidence",
        errors,
    )
    _require(isinstance(dedupe, dict), f"{path}.dedupe must be an object", errors)
    if isinstance(dedupe, dict):
        _require(
            dedupe.get("checked") is True,
            f"{path}.dedupe.checked must be true",
            errors,
        )
        _require(
            _has_text(dedupe.get("reason")),
            f"{path}.dedupe.reason is required",
            errors,
        )
        if isinstance(status, str) and status in {"duplicate", "completed"}:
            _require(
                _has_text(dedupe.get("existing_url")),
                f"{path}.dedupe.existing_url is required for {status}",
                errors,
            )

    if status == "new":
        repository = task.get("repo")
        body = task.get("body")
        _require(_has_text(body), f"{path}.body is required", errors)
        if isinstance(body, str):
            for heading in ("Context", "Goal", "Acceptance criteria", "Technical notes"):
                _require(
                    bool(re.search(rf"(?m)^## {heading}\s*$", body)),
                    f"{path}.body requires a {heading} section", errors,
                )
            _require(isinstance(marker, str) and marker in body, f"{path}.body must include its marker", errors)
        _require(
            mapping_status == "mapped",
            f"{path} cannot be new for an unmapped project",
            errors,
        )
        _require(
            isinstance(repository, str)
            and bool(REPOSITORY_PATTERN.fullmatch(repository)),
            f"{path}.repo is invalid",
            errors,
        )
        _require(
            isinstance(repository, str) and isinstance(project_repository, str)
            and repository.casefold() == project_repository.casefold(),
            f"{path}.repo must match the mapped project",
            errors,
        )
        _require(
            isinstance(marker, str) and bool(MARKER_PATTERN.fullmatch(marker)),
            f"{path}.marker is invalid",
            errors,
        )
        if isinstance(marker, str):
            _require(
                f":{thread_id}:" in marker,
                f"{path}.marker must contain the source thread ID",
                errors,
            )


def _validate_knowledge(candidate: Any, path: str, errors: list[str]) -> None:
    _require(isinstance(candidate, dict), f"{path} must be an object", errors)
    if not isinstance(candidate, dict):
        return

    status = candidate.get("status")
    sources = candidate.get("primary_sources")
    _require(
        isinstance(status, str) and status in KNOWLEDGE_STATUSES,
        f"{path}.status is invalid",
        errors,
    )
    _require(
        _has_text(candidate.get("reason")),
        f"{path}.reason is required",
        errors,
    )
    _require(
        isinstance(sources, list),
        f"{path}.primary_sources must be a list",
        errors,
    )
    if status == "verified":
        _require(
            _has_text(candidate.get("target_note")),
            f"{path}.target_note is required",
            errors,
        )
        _require(
            _has_text(candidate.get("proposed_content")),
            f"{path}.proposed_content is required",
            errors,
        )
        _require(
            isinstance(sources, list)
            and bool(sources)
            and all(_has_text(item) for item in sources),
            f"{path}.primary_sources must contain current primary evidence",
            errors,
        )
    elif status == "rejected":
        _require(
            candidate.get("target_note") is None,
            f"{path}.target_note must be null when rejected",
            errors,
        )


def validate_preview(preview: Any) -> list[str]:
    """Return all validation failures without mutating the preview."""
    errors: list[str] = []
    _require(isinstance(preview, dict), "preview must be a JSON object", errors)
    if not isinstance(preview, dict):
        return errors

    _require(
        type(preview.get("schema_version")) is int and preview["schema_version"] == 1,
        "schema_version must be 1",
        errors,
    )
    _require(preview.get("mode") == "preview", "mode must be preview", errors)
    _require(
        type(preview.get("window_days")) is int and preview["window_days"] > 0,
        "window_days must be a positive integer",
        errors,
    )
    _require(
        _valid_timestamp(preview.get("generated_at")),
        "generated_at must be timezone-aware ISO 8601",
        errors,
    )
    _require(
        _valid_timestamp(preview.get("cutoff")),
        "cutoff must be timezone-aware ISO 8601",
        errors,
    )
    if (
        type(preview.get("window_days")) is int and preview["window_days"] > 0
        and _valid_timestamp(preview.get("generated_at"))
        and _valid_timestamp(preview.get("cutoff"))
    ):
        timezone = ZoneInfo("Australia/Melbourne")
        try:
            generated = datetime.fromisoformat(preview["generated_at"].replace("Z", "+00:00")).astimezone(timezone)
            cutoff = datetime.fromisoformat(preview["cutoff"].replace("Z", "+00:00"))
            first_date = generated.date() - timedelta(days=preview["window_days"] - 1)
            expected_cutoff = datetime.combine(first_date, time.min, tzinfo=timezone)
            _require(cutoff == expected_cutoff, "cutoff must match the declared Melbourne calendar-day window", errors)
        except OverflowError:
            errors.append("preview timestamps or window_days are outside the supported date range")

    coverage = preview.get("coverage")
    validation = preview.get("validation")
    threads = preview.get("threads")
    _require(isinstance(coverage, dict), "coverage must be an object", errors)
    _require(
        isinstance(validation, dict),
        "validation must be an object",
        errors,
    )
    _require(isinstance(threads, list), "threads must be a list", errors)
    if not isinstance(threads, list):
        return errors

    if isinstance(validation, dict):
        _require(
            isinstance(validation.get("status"), str) and validation["status"] in {"pending", "validated"},
            "validation.status is invalid",
            errors,
        )
        for field in (
            "eligible_roster_complete",
            "dedupe_checks_complete",
            "primary_source_checks_complete",
        ):
            _require(
                validation.get(field) is True,
                f"validation.{field} must be true",
                errors,
            )

    seen_ids: set[str] = set()
    seen_markers: set[str] = set()
    audited_count = 0
    unreadable_count = 0
    archive_count = 0
    new_task_count = 0
    verified_knowledge_count = 0

    for index, thread in enumerate(threads):
        path = f"threads[{index}]"
        _require(isinstance(thread, dict), f"{path} must be an object", errors)
        if not isinstance(thread, dict):
            continue

        thread_id = thread.get("id")
        _require(_has_text(thread_id), f"{path}.id is required", errors)
        _require(_has_text(thread.get("host_id")), f"{path}.host_id is required", errors)
        if isinstance(thread_id, str):
            _require(
                thread_id not in seen_ids,
                f"duplicate thread ID: {thread_id}",
                errors,
            )
            seen_ids.add(thread_id)

        _require(thread.get("kind") == "codex", f"{path}.kind must be codex", errors)
        _require(_has_text(thread.get("status")), f"{path}.status is required", errors)
        _require(
            _valid_timestamp(thread.get("updated_at")),
            f"{path}.updated_at is invalid",
            errors,
        )
        _require(
            _valid_timestamp(thread.get("observed_updated_at")),
            f"{path}.observed_updated_at must be timezone-aware ISO 8601",
            errors,
        )
        if _valid_timestamp(thread.get("updated_at")):
            updated = datetime.fromisoformat(thread["updated_at"].replace("Z", "+00:00"))
            if _valid_timestamp(preview.get("cutoff")):
                cutoff = datetime.fromisoformat(preview["cutoff"].replace("Z", "+00:00"))
                _require(updated >= cutoff, f"{path} is outside the approved window", errors)
            if _valid_timestamp(thread.get("observed_updated_at")):
                observed = datetime.fromisoformat(thread["observed_updated_at"].replace("Z", "+00:00"))
                _require(observed == updated, f"{path} has mismatched update timestamps", errors)
        _require(
            _has_text(thread.get("current_title")),
            f"{path}.current_title is required",
            errors,
        )
        _require(
            _has_text(thread.get("proposed_title")),
            f"{path}.proposed_title is required",
            errors,
        )
        _require(
            isinstance(thread.get("outcome"), str) and thread["outcome"] in OUTCOMES,
            f"{path}.outcome is invalid",
            errors,
        )
        _require(
            isinstance(thread.get("evidence"), list) and bool(thread["evidence"])
            and all(_has_text(item) for item in thread["evidence"]),
            f"{path}.evidence must contain non-empty source references",
            errors,
        )

        project = thread.get("project")
        _require(
            isinstance(project, dict),
            f"{path}.project must be an object",
            errors,
        )
        mapping_status = "unmapped"
        if isinstance(project, dict):
            mapping_status = project.get("mapping_status")
            _require(
                isinstance(mapping_status, str) and mapping_status in {"mapped", "unmapped"},
                f"{path}.project.mapping_status is invalid",
                errors,
            )
            _require(
                isinstance(project.get("apply_support"), str) and project["apply_support"] in {"supported", "unsupported"},
                f"{path}.project.apply_support is invalid",
                errors,
            )
            if mapping_status == "mapped":
                _require(
                    _has_text(project.get("name")),
                    f"{path}.project.name is required",
                    errors,
                )
                _require(
                    _has_text(project.get("cwd")),
                    f"{path}.project.cwd is required",
                    errors,
                )
                repository = project.get("repo")
                _require(
                    isinstance(repository, str)
                    and bool(REPOSITORY_PATTERN.fullmatch(repository)),
                    f"{path}.project.repo is invalid",
                    errors,
                )
            elif mapping_status == "unmapped":
                for field in ("name", "cwd", "repo"):
                    value = project.get(field)
                    valid_value = value is None or (
                        _has_text(value)
                        and (field != "repo" or bool(REPOSITORY_PATTERN.fullmatch(value)))
                    )
                    _require(
                        field in project and valid_value,
                        f"{path}.project.{field} must be present and null or valid text",
                        errors,
                    )

        _require(type(thread.get("unreadable")) is bool, f"{path}.unreadable must be a boolean", errors)
        _require(type(thread.get("archive_candidate")) is bool, f"{path}.archive_candidate must be a boolean", errors)
        unreadable = thread.get("unreadable") is True
        if unreadable:
            unreadable_count += 1
            _require(
                _has_text(thread.get("blocker")),
                f"{path}.blocker is required when unreadable",
                errors,
            )
        else:
            audited_count += 1
            _require(
                thread.get("blocker") is None,
                f"{path}.blocker must be null when readable",
                errors,
            )

        unresolved = thread.get("unresolved_outcomes")
        tasks = thread.get("task_candidates")
        knowledge = thread.get("knowledge_candidates")
        _require(
            isinstance(unresolved, list),
            f"{path}.unresolved_outcomes must be a list",
            errors,
        )
        _require(
            isinstance(tasks, list),
            f"{path}.task_candidates must be a list",
            errors,
        )
        _require(
            isinstance(knowledge, list),
            f"{path}.knowledge_candidates must be a list",
            errors,
        )

        if isinstance(tasks, list):
            for task_index, task in enumerate(tasks):
                _validate_task(
                    task,
                    str(thread_id),
                    mapping_status,
                    project.get("repo") if isinstance(project, dict) else None,
                    f"{path}.task_candidates[{task_index}]",
                    errors,
                )
                if isinstance(task, dict) and task.get("status") == "new":
                    new_task_count += 1
                    marker = task.get("marker")
                    if isinstance(marker, str):
                        _require(marker not in seen_markers, f"duplicate task marker: {marker}", errors)
                        seen_markers.add(marker)
                    _require(not unreadable, f"{path} unreadable thread cannot propose new tasks", errors)

        if isinstance(knowledge, list):
            for candidate_index, candidate in enumerate(knowledge):
                _validate_knowledge(
                    candidate,
                    f"{path}.knowledge_candidates[{candidate_index}]",
                    errors,
                )
                if (
                    isinstance(candidate, dict)
                    and candidate.get("status") == "verified"
                ):
                    verified_knowledge_count += 1
                    _require(not unreadable, f"{path} unreadable thread cannot propose verified knowledge", errors)

        if thread.get("archive_candidate") is True:
            archive_count += 1
            _require(
                thread.get("unreadable") is False,
                f"{path} archive candidate must be explicitly readable",
                errors,
            )
            _require(
                thread.get("status") == "idle",
                f"{path} archive candidate must have a confirmed idle status",
                errors,
            )
            _require(
                thread.get("outcome") == "verified_complete",
                f"{path} archive outcome must be verified_complete",
                errors,
            )
            _require(
                isinstance(unresolved, list) and not unresolved,
                f"{path} archive candidate has unresolved outcomes",
                errors,
            )
            has_outstanding_tasks = isinstance(tasks, list) and any(
                isinstance(task, dict) and isinstance(task.get("status"), str) and task["status"] in {"new", "blocked"}
                for task in tasks
            )
            _require(
                not has_outstanding_tasks,
                f"{path} archive candidate has outstanding tasks",
                errors,
            )

    if isinstance(coverage, dict):
        expected_counts = {
            "eligible_threads": len(threads),
            "audited_threads": audited_count,
            "unreadable_threads": unreadable_count,
            "archive_candidates": archive_count,
            "new_task_candidates": new_task_count,
            "verified_knowledge_candidates": verified_knowledge_count,
        }
        for field, expected in expected_counts.items():
            _require(
                type(coverage.get(field)) is int and coverage[field] == expected,
                f"coverage.{field} must equal {expected}",
                errors,
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preview", type=Path)
    args = parser.parse_args()
    try:
        preview = json.loads(args.preview.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    errors = validate_preview(preview)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1

    print(
        "VALID: "
        f"{preview['coverage']['eligible_threads']} eligible threads, "
        f"{preview['coverage']['new_task_candidates']} new tasks, "
        f"{preview['coverage']['archive_candidates']} archive candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
