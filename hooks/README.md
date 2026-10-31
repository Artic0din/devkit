# Staged-secret checks

`hooks/check-staged-secrets.sh` runs one Gitleaks scan of the caller's Git index.
It requires Bash, Git and Gitleaks, writes no files and makes no network requests.

Run it from the repository being checked.
Outside a repository it does nothing; missing Git, unreadable metadata and damaged `.git` directories block the check.
It returns exit code 2 with a generic message on a finding, scanner error or missing Gitleaks, and 0 with no output on a clean scan.
It does not print staged lines, even when a secret is detected.

The repository's `hooks/pre-commit` runs the scanner after Git has staged all commit content, including `git commit -a`, before its existing skill validation.
This enforcement covers `git commit` in opted-in checkouts, not every command that can create commits.
In particular, cherry-pick does not invoke `pre-commit`, and merge can use `pre-merge-commit` instead.
Opt in as documented in the main README with `git config core.hooksPath hooks`.
The Git hook fails closed if scanning is unavailable.
It never replaces the mandatory explicit staged scan before commits and exact outgoing-commit-range scan before pushes.
Git's explicit hook bypasses remain possible; this is not a server-side enforcement boundary.

Run `python3 hooks/test-staged-secrets.py` to exercise the scanner and the Git hook against isolated Git repositories and the installed Gitleaks executable.

# Delegate guard

`hooks/delegate-guard.py` is a synchronous `PreToolUse` hook for T3 Code `delegate_task` calls and Claude Code's native `Agent` tool.
It needs Python 3, writes no files and makes no network requests.
Allowed calls and unrelated tools produce no output.
It enforces the model routing ladder in `AGENTS.MD` (Parallel Agents).
A `delegate_task` without `target.model` is denied because the child would inherit the parent's model and effort.
An effort of `xhigh` or above, or GPT-6 Astra, needs `[escalate:L3]` in the title and a `Trigger: <reason>` marker with a non-empty reason in the task; the bare word trigger does not count.
Fable or Mythos needs `[escalate:L4]`; model ids are normalised first, so provider prefixes, dated ids and `[1m]` context suffixes classify the same way.
Below L3, fast mode and the 500k or 1m context options are denied on every provider, including a `[1m]` suffix on the model id, so a renamed Cursor instance or Claude's own fast mode cannot slip through.
Native `Agent` calls follow the same tag rules for `fable` and effort above `high`.
A call without `model` is allowed only when `subagent_type` is `fork`, which inherits by design, or when a definition whose front matter `name` matches the type names a model on the `model:` line; project `.claude/agents` trees are searched recursively from the call's cwd up to the repository root before `~/.claude/agents`, and the resolved model is then checked, so a definition on `fable` needs the L4 tag too.
The effective effort is the call's `effort`, else the definition's `effort`, with `CLAUDE_CODE_EFFORT_LEVEL` overriding both, so a definition at `max` needs the L3 tag unless the call lowers it.
With `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `CLAUDE_CODE_SUBAGENT_MODEL` overrides every call and is what the guard checks; force without a concrete model is denied because the effective model is unknown.
Without force, `CLAUDE_CODE_SUBAGENT_MODEL` is ignored as a fallback, because built-in types such as Plan and Explore ignore it too, so an unspecified model is still denied.
A definition that declares `model: inherit` is denied for the same reason, whatever the environment fallback says.
A non-fork call must also resolve an effort from the call, the definition or `CLAUDE_CODE_EFFORT_LEVEL`; otherwise it would inherit the session's effort and is denied.
Built-in types such as `general-purpose` without a model, and plugin-namespaced types such as `pstack:deep` whose definitions live in plugin caches, are denied unless the call names its model.
A deny is printed as a PreToolUse `hookSpecificOutput` decision with exit code 0, which both Claude Code and Codex read; an unreadable payload is denied with a generic reason and never echoed.
The guard only sees agent tool calls: the T3 picker and humans choose models freely.
Known limit: a native `Agent` alias such as `opus` resolves to the parent's exact model when the families match, so a parent that Ryan started on a `[1m]` context passes that context to same-family children; the hook cannot see the parent's model and does not try to guess it, because denying every alias would block the ladder's own values.

Wire it in Claude Code's `~/.claude/settings.json`:

```json
{"hooks": {"PreToolUse": [{"matcher": "mcp__t3-code__delegate_task|Agent", "hooks": [{"type": "command", "command": "python3 /Users/ryanfoyle/Metisary/Enviroment/config/hooks/delegate-guard.py", "timeout": 5}]}]}}
```

And in Codex's `~/.codex/hooks.json` as a `PreToolUse` entry beside the existing `PostToolUse` one:

```json
{"matcher": "delegate_task", "hooks": [{"type": "command", "command": "python3 '/Users/ryanfoyle/Metisary/Enviroment/config/hooks/delegate-guard.py'", "timeout": 5}]}
```

Codex passes MCP tools to hooks under their canonical tool name with resolved JSON arguments, so the matcher is a substring; this was checked against the Codex hook schema, not a captured payload.

Run `python3 hooks/test-delegate-guard.py` for the offline contract tests.
