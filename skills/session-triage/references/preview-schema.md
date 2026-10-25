# Preview schema

The preview is JSON.
All timestamps are timezone-aware ISO 8601 values.
Normalize native app timestamps from seconds or milliseconds before writing the preview.
`observed_updated_at` records the same instant as `updated_at` for the pre-mutation freshness check.
Every thread's update time must be on or after `cutoff`.
The window includes today's Melbourne calendar date: cutoff is Melbourne midnight `window_days - 1` dates before `generated_at`.

Required top-level fields:

- schema_version: 1
- mode: preview
- generated_at
- cutoff
- window_days: positive integer, default 7 unless the user requests a different window
- coverage
- validation
- threads

Coverage contains:

- eligible_threads
- audited_threads
- unreadable_threads
- archive_candidates
- new_task_candidates
- verified_knowledge_candidates

Validation contains status (pending or validated) and true values for:

- eligible_roster_complete
- dedupe_checks_complete
- primary_source_checks_complete

Each thread contains:

- id, host_id, kind, updated_at, observed_updated_at, status
- current_title and proposed_title
- project with name, cwd, repo, mapping_status, and apply_support
- outcome and non-empty evidence
- unreadable and blocker
- archive_candidate
- unresolved_outcomes
- task_candidates
- knowledge_candidates

Project mapping_status is mapped or unmapped.
Project apply_support is supported or unsupported.
Every thread's host_id is a non-empty string identifying the source host, including `local` for the local host.
Project name, cwd, and repo must always be present.
For a mapped project, name and cwd are non-empty strings and repo uses `owner/repository` form.
For an unmapped project, unknown values are explicitly null; known name and cwd values are non-empty strings, and a known repo still uses `owner/repository` form.
Thread status is the non-empty status returned by the app.
Only a confirmed `idle` status permits an archive candidate; active, missing, or unfamiliar statuses do not establish inactivity.

Task status is new, duplicate, completed, or blocked.
Every task includes title, repo, evidence, dedupe, and marker.
Dedupe contains checked, existing_url, and reason.
Duplicate and completed tasks include an `https` URL to the existing work.
New tasks require a mapped owner/repository and a marker containing the source thread ID.
Every new task also includes the exact proposed issue body, with Context, Goal, Acceptance criteria, and Technical notes sections and its stable marker.
Each section has non-empty content apart from the marker, and Acceptance criteria lists at least one `-` or `*` item.
Task markers must be unique across all new candidates in the preview.
The task repository must match the mapped project's repository, ignoring letter case.
Unreadable threads cannot contain new task candidates or verified knowledge candidates.
An unreadable thread's proposed_title equals its current_title, so it is never renamed.

Knowledge status is verified or rejected.
Verified candidates include target_note, proposed_content, edit_operation, non-empty primary_sources, and reason.
edit_operation is `create`, `append`, or `replace_section`.
`create` writes proposed_content as a new note and requires that target_note does not exist yet.
`append` adds proposed_content to the end of the existing target_note.
`replace_section` also names target_section, the exact existing heading whose content proposed_content replaces.
Rejected candidates use a null target_note and precise rejection reason.
