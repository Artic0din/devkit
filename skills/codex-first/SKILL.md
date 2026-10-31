---
name: codex-first
description: "Claude Code delegation: route substantial implementation, fixes, exploration, and authorised Git operations to Codex when the parent uses a native Claude model. Keep design and verification with the parent."
---

# Codex First

## Routing gate

Use hands-on delegation only when the parent is Claude Code running a native Claude model.
Determine that from the active session's model metadata, not its base URL or a guessed router name.
If the model is non-Claude or cannot be identified, work directly.
Codex and other harnesses also work directly rather than launching a Codex worker to do their own task.

Independent review is separate from hands-on delegation.
For review, load [autoreview](../autoreview/SKILL.md) and follow its target selection, engine choice, isolation, and completion rules.
Codex remains the preferred reviewer in every harness; Claude review is available when requested.
Use the review helper, never the implementation-worker recipe below, for that review.

## Divide the work

Delegate substantial implementation, refactoring, bug fixes, tests, dependency updates, and bounded code exploration.
Delegate authorised rebases, conflict resolution, and landing mechanics when the routing gate applies.
Keep design decisions, ambiguous requirements, tiny obvious edits, session-only tools, credentials, and release/publish operations with the parent.
The parent owns the landing decision and verifies its required gates before dispatching landing mechanics.

Delegation grants no extra authority.
A work order may include commits, pushes, merges, or publication only when the user or governing workflow already authorises those actions.
Preserve unrelated edits and follow the target repository's instructions.

## Prepare the work order

Use a fresh session for a new work order.
Resume an existing session only for a follow-up to that same order.

Give the worker:

- the goal, absolute repository/worktree path, branch, and applicable agent instructions;
- the permitted changes, non-goals, and exact Git/publication authority;
- the known failure or evidence, relevant files, and decisions already made;
- the required checks and expected report: changed files, commands/results, unresolved findings, and blockers;
- a stop condition: finish this order only; if a constraint cannot be met, report the evidence instead of bypassing it.

For concurrent workers, use one isolated worktree and branch per worker.
Give each worker a unique prompt, result, and log path.
Keep landing serial and preserve another worker's lock or unfinished work.

## Launch an implementation worker

Inherit the configured Codex model, provider, authentication, sandbox, and approval policy.
Keep medium reasoning on the default service tier as the worker defaults (L1 in the AGENTS.MD routing ladder); raise to high only after a trigger, and use Fast service only when Ryan asks for speed.
Do not hardcode a model or switch providers to recover from an error.
Apply an explicit user model override with `--model` on every fresh or resumed launch.

Codex here authenticates through ChatGPT OAuth and uses the model's default context window; see [codex-config](../codex-config/SKILL.md) for its settings and restart rules.
Resolve sibling skills from this loaded skill's real directory, following symlinks.
Verify host-specific configuration before using that workflow; do not copy upstream paths, provider settings, or credentials into this environment.

Check `command -v codex` and the installed `codex exec --help` before the first launch.
Use the installed CLI; report a missing installation instead of installing or rewriting launchers as part of delegation.

In Claude Code, run each worker as its own harness-tracked background task (`run_in_background: true`).
Include setup inside that tracked task and retain its completion/exit status.
Do not detach it with `&`.

Set `repo` to the verified absolute worktree path.
Write a complete work order into the quoted heredoc before launching:

```bash
task_dir=$(mktemp -d "${TMPDIR:-/tmp}/codex-worker.XXXXXX")
cat >"$task_dir/prompt.md" <<'EOF'
<Complete work order with scope, authority, checks, and stop condition.>
EOF
if command codex exec -C "$repo" \
  -c 'model_reasoning_effort="medium"' \
  -o "$task_dir/result.md" - <"$task_dir/prompt.md" \
  >"$task_dir/worker.log" 2>&1; then
  cat "$task_dir/result.md"
else
  worker_exit=$?
  printf 'Worker failed (%s); inspect %s\n' "$worker_exit" "$task_dir/worker.log" >&2
  exit "$worker_exit"
fi
```

Medium effort on the default tier is the L1 worker setting from the routing ladder in AGENTS.MD; escalate to L2 with `-c 'model_reasoning_effort="high"'` only after a trigger, and add `--enable fast_mode -c 'service_tier="fast"'` only when Ryan asks for speed.
Keep logs local and inspect only relevant, redacted errors.
Read the result file after completion; the file alone does not prove the command succeeded.
Remove the task's temporary directory only after collecting the result and any needed failure evidence.
An execution-policy denial is a blocker to diagnose, not permission to add unrestricted execution flags.

## Follow-up and recovery

Save the explicit session ID from the worker's launch output before resuming.
Use a new result/log file for each attempt so stale output cannot look like a successful retry.
Check the installed `codex exec resume --help`; run from the repository directory because resume does not accept `-C`.

A follow-up uses the same provider and authorised execution policy.
If the recorded session settings conflict with the intended settings, start a fresh scoped worker.
Repeat the reasoning/service settings and any explicit user model override.
For example, after writing the follow-up prompt and setting the saved `session_id`:

```bash
(cd "$repo" && command codex exec resume "$session_id" \
  -c 'model_reasoning_effort="medium"' \
  -o "$task_dir/followup-result.md" - <"$task_dir/followup-prompt.md" \
  >"$task_dir/followup.log" 2>&1)
```

Preserve and check that command's exit status before reading its result.
If resume cannot restore the session, launch a fresh worker with a self-contained handoff.
For authentication, model, provider, or policy failures, inspect the exact redacted error and fix the confirmed cause before retrying.
Keep credential handling in the approved credential workflow; never put credentials in prompts, command arguments, logs, or copied authentication files.

While work is running, use the tracked task's status and relevant log tail to assess progress.
Five minutes without log output is a reason to inspect, not proof of a hang.
Interrupt only a task-owned worker when there is evidence it is stalled, out of scope, or no longer needed.
Wait for it to stop before editing its files or starting a replacement.
Follow the governing repository's failed-attempt limit; report the blocker instead of repeatedly relaunching unchanged work.

## Verify and close out

Read the actual diff and Git status, check that every changed file belongs to the order, and verify the requested behaviour with focused proof.
Treat the worker's report as evidence to check, not completion by itself.
For CI work, confirm a run exists for the exact head SHA before waiting and handle every terminal state.
Run the required [autoreview](../autoreview/SKILL.md) closeout and address accepted findings.
Confirm task-owned workers have stopped before editing, committing, or handing off their files.
After authorised landing, verify the merged result and checkout state under the repository's normal workflow.
