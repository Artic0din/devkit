---
name: codex-config
description: "Codex configuration: model and reasoning settings, ChatGPT login, app-server restarts after config changes, and fleet rollout."
---

# Codex Config

Use this skill when configuring, repairing, or auditing Codex on Ryan's Macs.

Codex authenticates through ChatGPT OAuth, not an OpenAI API key:

```bash
codex login status   # Logged in using ChatGPT
```

`~/.codex/auth.json` holds `auth_mode = "chatgpt"` and OAuth tokens, with `OPENAI_API_KEY` null.
Never print, copy, or move that file between Macs; each host logs in from its own local session.

## Current settings

The root of `~/.codex/config.toml` carries:

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "medium"
model_reasoning_summary = "concise"
model_verbosity = "medium"
service_tier = "default"
personality = "pragmatic"
approval_policy = "never"
approvals_reviewer = "user"
sandbox_mode = "danger-full-access"
```

`approval_policy = "never"` with `sandbox_mode = "danger-full-access"` means Codex runs commands
without asking. Treat any change to either as a deliberate decision Ryan makes, not a repair step.

Preserve the selected model when changing anything else. `-m gpt-6.1-sol` selects a model, not a
provider, and changing reasoning effort or verbosity does not require touching the model.

## Do not add direct-API context overrides

There is no `model_provider`, `model_catalog_json`, or custom model catalogue here, and there should
not be. A 922,000-token context window and a 700,000-token compaction threshold belong only to a
direct OpenAI API provider with its own API key and billing.

Attaching those numbers to the ChatGPT-backed route produces a thread that grows past the real
provider limit, receives `context_length_exceeded`, and then cannot compact because the compaction
request itself no longer fits. The session is unrecoverable at that point. If a config writer or a
synced file introduces `model_context_window`, `model_auto_compact_token_limit`, or
`model_catalog_json`, remove them rather than tuning them.

Codex's own defaults for the selected model are authoritative. The server decides real limits and
billing; a client-side override cannot expand entitlement.

## Config changes need an app-server restart

Codex TUI sessions can share an app server through
`~/.codex/app-server-control/app-server-control.sock`. A running server keeps the configuration it
loaded at startup, so editing `config.toml` does not reach sessions already attached to it. When that
socket directory exists, a shared server is running and keeps its loaded settings.

After changing configuration:

1. let active turns finish;
2. restart the Codex desktop app and any shared CLI app server;
3. start a fresh session for proof;
4. resume an old session only when keeping its recorded model is intentional.

A fresh session reads the root config; session metadata then records what it used, and resuming
preserves that record. A same-value CLI override such as `codex -c 'model_verbosity="medium"'`
forces an embedded per-invocation server, which is useful for diagnosis without changing anything
permanently.

## Verification

```bash
codex --version
codex login status
codex exec --skip-git-repo-check 'Reply with exactly: codex-config-ok' </dev/null
```

Expect the installed version, `Logged in using ChatGPT`, and the exact probe response. For TUI
proof, send the prompt text and Enter as separate terminal actions, and do not read echoed input as
the model's reply.

## Direct-API preflight

`scripts/preflight.rb` validates a direct OpenAI API setup: the `openai_api_direct` provider block,
the safe-input and compaction values, all four catalogue entries, and that the Keychain auth helper
returns a non-empty credential without printing it. `--private-home` additionally re-runs the helper
under fresh HOME and XDG directories as a delivery diagnostic.

It is retained for the direct-API route described above as something not to add casually. None of
that is configured here, so running it against the current setup fails at the provider check — that
is the correct result, not a fault. Use it only if Ryan deliberately moves inference to a direct API
provider, and treat a failure as a reason to stop rather than to lower a threshold.

```bash
ruby skills/codex-config/scripts/preflight.rb
```

`scripts/preflight.test.rb` is synthetic and offline, runs in CI, and passes independently of the
host's Codex configuration.

## Fleet rollout

Use `$fleet-maintenance` first for its host list, reachability rules, and remote PATH handling.
Audit every reachable host before mutation; mutate one host at a time. Verify each host's identity
before changing any remote file, and keep a per-host result with:

- a config backup taken before the change;
- the resulting root settings;
- `codex login status`, without showing any credential;
- whether an app-server restart is still pending.

Never interrupt an active Codex turn to reload configuration; report it as pending instead.

## Failure policy

- Context overflow: preserve the session file and inspect the last token-accounting events. Do not
  respond by adding a context or compaction override; see the section above.
- A setting appears not to apply: check the running app-server version and the configuration it
  loaded. An old server keeps the previous values even after the file changes.
- `codex login status` reports API-key login when connectors are needed: run `codex logout` then
  `codex login` from that host's local graphical session.
- A synced config introduces a direct provider table or custom catalogue: inspect before changing,
  and never append a duplicate TOML table.
