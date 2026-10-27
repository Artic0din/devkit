---
name: github-author-context
description: "GitHub contributor context: identity, activity, trust, company/team signal."
---

# GitHub Author Context

Build a compact profile of a PR author or GitHub user before reviewing their work.

Most useful on repositories Ryan does not own. His own repositories are authored by
himself and by bots, so the profile pass rarely earns its cost there.

## When to skip

- `Artic0din` is Ryan. Skip unless he explicitly asks.
- Bot authors carry no trust signal. `gh` reports them as `app/<name>`, and
  `.author.is_bot` is `true`; `app/copilot-swe-agent` and `app/dependabot` are the two
  seen here. Record the bot name and review the diff on its merits instead.

```bash
gh pr view <n> --json author -q '{login:.author.login,bot:.author.is_bot}'
```

## Inputs

Prefer a GitHub login. From a PR:

```bash
gh pr view <n> --json author,url,headRepository,baseRepository \
  -q '{author:.author.login,url:.url,repo:.baseRepository.nameWithOwner}'
```

## Source order

1. Live GitHub public profile:

```bash
gh api "users/<login>" \
  --jq '{login,name,company,location,bio,blog,twitter_username,created_at,followers,following,public_repos}'
```

2. Target-repo activity. Which command works depends on repository visibility, and
   picking the wrong one returns a confidently empty answer:

**Public repositories** — search works:

```bash
gh search prs --repo <owner/repo> --author <login> --merged --limit 20 --json number,title,url
gh search prs --repo <owner/repo> --author <login> --state open --limit 20 --json number,title,url
gh search issues --repo <owner/repo> --author <login> --state open --limit 20 --json number,title,url
```

`--state merged` is not valid here; merged state is the separate `--merged` flag.

**Private repositories** — search is not available, and `gh pr list --author` silently
returns `[]` instead of failing. Verified on `Artic0din/Pulse`: `--author Artic0din`
returned nothing while that author had 40 merged pull requests. List first, then filter
client-side:

```bash
gh pr list --repo <owner/repo> --state merged --limit 100 \
  --json number,title,mergedAt,author -q '[.[] | select(.author.login=="<login>")]'
```

Never read an empty result as "no history" without confirming the query could have
returned anything. Check visibility when unsure:

```bash
gh repo view <owner/repo> --json isPrivate -q .isPrivate
```

Collaborator permission, on either kind of repo:

```bash
gh api "repos/<owner>/<repo>/collaborators/<login>/permission" --jq '{permission,user:.user.login}' 2>/dev/null || true
```

The permission endpoint needs push access on the repository being queried. With it, a
non-collaborator returns `permission: none`. Without it — the normal case on a repo Ryan
does not own — it returns HTTP 403 `Must have push access to view collaborator
permission`, which is why the call ends in `|| true`. Neither result is an error to
report, and neither says anything about the author.

3. Local git evidence, when the repo is checked out:

```bash
git log --all --author="<login>" --since="90 days ago" --oneline --decorate --no-merges | head -40
git shortlog -sne --all | rg -i "<login>|<name>|<email>"
```

## Output

Keep it short. Add this block near the top of a PR review:

```text
Author context: @login
- Who: <name/company/location/role, confidence>
- Activity: <merged/open PRs, issues, reviews/commits if known>
- Standing: <maintainer/collaborator/repeat contributor/drive-by/bot/unknown>
- Risk: <review-load, broad PRs, low history, company-governance, none obvious>
```

State confidence. A public profile is self-reported: an empty `company` field is
absence of evidence, not evidence of independence. Separate someone's employer from
work their employer directed; almost everyone has an employer.

Never quote private phone, email, or contact details unless Ryan asks. Do not compile a
profile beyond what the review needs.
