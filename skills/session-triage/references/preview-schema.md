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
Thread status is the non-empty status returned by the app.
Only a confirmed `idle` status permits an archive candidate; active, missing, or unfamiliar statuses do not establish inactivity.

Task status is new, duplicate, completed, or blocked.
Every task includes title, repo, evidence, dedupe, and marker.
Dedupe contains checked, existing_url, and reason.
Duplicate and completed tasks include an existing URL.
New tasks require a mapped owner/repository and a marker containing the source thread ID.

Knowledge status is verified or rejected.
Verified candidates include target_note, proposed_content, non-empty primary_sources, and reason.
Rejected candidates use a null target_note and precise rejection reason.
