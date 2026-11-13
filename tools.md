# Tools Reference

CLI tools installed on Ryan's Macs that agents reach for directly. Skills own the workflows; this
file is only the map of what exists and where the workflow lives.

## gh
GitHub CLI for PRs, issues, CI, releases. Authenticated as `Artic0din`.

**Usage**: `gh help`

When someone shares a GitHub URL, read it with `gh`, not a browser:
```bash
gh issue view <url> --comments
gh pr view <url> --comments --files
gh run list / gh run view <id>
```

Workflows: `$github-deep-review`, `$github-project-triage`, `$github-author-context`.

---

## codexbar
Usage and remaining limits for Codex, Claude, Cursor and other AI providers, backed by the CodexBar app. On PATH via Homebrew.

**Usage**: `codexbar usage --provider codex --json`

---

## mcporter
Calls any MCP server configured for Claude, Codex or Cursor from the shell, for example `mcporter call ha-mcp.ha_eval_template ...` for Home Assistant. On PATH via Homebrew.

**Usage**: `mcporter --help`

Preferred relay for Chrome work; see the routing in `AGENTS.MD`.

---

## xcodes
Xcode version manager, installed on every fleet Mac. Full Xcode is not always present; check before assuming Instruments,
`xctrace`, or `simctl` exist.

```bash
xcodes installed
xcrun --find xctrace || echo "not installed; run: xcodes install --latest"
```

Workflows: `$xcode-sync`, `$instruments-profiling`, `$native-app-performance`.

---

## yt-dlp
Video, audio, subtitle, and transcript downloads.

Workflows: `$video-transcript-downloader` for raw downloads, `$video-analysis` for a visual brief of one video.

---

## imsg
iMessage CLI, installed from Homebrew. No skill currently routes to it.

---

## Sonos
There is no `sonos` CLI installed. Sonos is reached through the Sonos connector configured in
Claude; `$sonos` documents the workflow.

---

## Computer use
Screenshot, screen inspection, and click automation.

Use the available browser or computer-use tools and their applicable skills, following the
routing in `docs/agent-operations.md`.

## Obscura

Default MCP browser for agent page reading, extraction and DOM interaction on the fleet Macs.
The `obscura` entry in Claude, Codex and Cursor starts `~/.local/bin/obscura mcp` on demand.
The launcher in `scripts/obscura` uses version 0.2.6 from `~/.local/share/obscura/0.2.6/` and the profile in `config/obscura.sb`, installed as `~/.local/share/obscura/browser.sb`.
Keep both release executables together and verify the release archive's SHA-256 before installation.
Run `python3 scripts/test-obscura.py` to check the profile.

From this repository's root, on an Apple Silicon Mac with `curl` and `sandbox-exec`:

```sh
set -eu
test "$(uname -s)" = Darwin && test "$(uname -m)" = arm64
mkdir -p "$HOME/Metisary/Enviroment/scratch/codex"
stage=$(mktemp -d "$HOME/Metisary/Enviroment/scratch/codex/obscura-install.XXXXXX")
curl --fail --location --proto '=https' -o "$stage/release.tar.gz" https://github.com/h4ckf0r0day/obscura/releases/download/v0.2.6/obscura-aarch64-macos.tar.gz
printf '%s  %s\n' 19faa248ac762f466ddb822dbb03ed4f097312d10d1a4d5b2143e6040a9bebd0 "$stage/release.tar.gz" | shasum -a 256 -c -
tar -xzf "$stage/release.tar.gz" -C "$stage" obscura obscura-worker
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/obscura/0.2.6"
install -m 700 "$stage/obscura" "$stage/obscura-worker" "$HOME/.local/share/obscura/0.2.6/"
install -m 600 config/obscura.sb "$HOME/.local/share/obscura/browser.sb"
install -m 700 scripts/obscura "$HOME/.local/bin/obscura"
"$HOME/.local/bin/obscura" fetch https://example.com --quiet --eval document.title
```

Back up each client's existing MCP configuration before merging the `obscura` entry from `config/mcp.json` or `config/codex.config.template.toml`; do not replace the whole configuration.
For Codex, retain the template's explicit routine-browser tool list and disable existing `chrome-devtools` and `playwright` entries with `enabled = false`.
For Claude, switch off its Chrome-by-default setting if enabled.
The fleet paths in `config/mcp.json` target the existing account; adjust those paths for other accounts.

The profile denies access to home directories, external volumes and macOS temporary directories, denies writes to the browser installation, and prevents launching other executables.
This is a filesystem and executable boundary, not Chrome-equivalent site isolation or a complete network sandbox.
The native MCP browser runs in-process; subprocess-based CLI modes are outside this launcher's supported scope.
Sessions have no imported Chrome cookies or profiles.
Private-network navigation remains blocked by Obscura's default; use a real browser for local apps, existing logins, downloads into personal folders, extensions, visual acceptance and Chrome-specific debugging.
Codex's `chrome-devtools` server is disabled by default but retained for an explicit fallback session.
Launch that fallback with `codex -c 'mcp_servers.chrome-devtools.enabled=true'` when needed.
Use the active host's browser tools when that workflow requires them; T3's browser and bundled Chrome are managed by T3 and are not replaced by this integration.
Existing sessions keep their loaded tools until restarted after their work finishes.
