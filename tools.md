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

## repobar
Repository activity, issue and PR counts, and local checkout state across `Artic0din` and
`Plaintext-Lab`. On PATH via Homebrew, backed by the RepoBar app.

**Usage**: `repobar --help`

Workflow: `$github-project-triage` (broad queue discovery).

---

## mcporter
MCP server launcher for browser automation and web scraping. On PATH via Homebrew.

**Usage**: `mcporter --help`

Preferred relay for Chrome work; see the routing in `AGENTS.MD`.

---

## gitleaks
Secret scanner. Required before every commit and push; see the Git rules in `AGENTS.MD`.

```bash
gitleaks git --staged --redact
gitleaks git --redact --log-opts="origin/<branch>..HEAD"
```

---

## xcodes
Xcode version manager. Full Xcode is not always present; check before assuming Instruments,
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
