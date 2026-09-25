---
name: build-kickoff
description: Emit a standardized greenfield/multi-phase build kickoff brief for Ryan's projects. Use when starting a new build that should run phase-by-phase with branch-per-PR, conventional commits, tests-in-PR, and a chosen execution mode. Triggers - "start an autonomous build", "kick off the build", "run this spec end to end", "build X phase by phase", pasting a build/autonomy preamble, or any new-project kickoff that needs the standing gates and rules wired up.
metadata:
  short-description: Standardized greenfield build kickoff brief (autonomous or human-gated)
---

# Build Kickoff

## Overview

Greenfield and multi-phase builds in this environment always open with the same standing
block: read the engineering constitution, branch-per-PR, conventional commits, tests in the
same PR, a secret scan before every push, no scope creep, and a chosen *execution mode*. This
skill assembles that brief from the canonical templates below so it is identical every time
and never hand-retyped or partially remembered.

This is a template/standards skill: it produces a kickoff brief, it does not itself run the
build. After emitting the brief, hand off to the normal execution path (`worker`/`architect`,
`superpowers:executing-plans`, or `loop` for autonomous runs).

## When to use

- A new repo/project is starting and needs the standing rules + gates stated up front.
- A spec exists and the user wants it executed phase by phase, PR per phase.
- The user pastes a partial autonomy/build preamble (fill the gaps from here instead).

Do NOT use for: one-off edits to an existing repo, code review (`code-review`/`linus-code-reviewer`),
or handoffs to another agent (`agent-handoff`).

## Step 1 - Choose the execution mode

Exactly one. This is the only real decision; everything else is fixed.

- **Autonomous** - continue authorized implementation and validation without routine pauses.
  Merge only when the user's instructions and repository policy authorize it.
  Use when the user says "run autonomously / end to end / do not pause".
- **Human-gated** - same rules, but every phase/PR stops at a `<HARD-GATE>` user review gate;
  the human presses merge. Default to this when the mode is not stated.

If the user has not stated the mode, use human-gated review.

## Step 2 - Gather the project-specific fill-ins

Only these vary per build. Get them from the spec/prompt; do not invent - if a value is
unknown, leave a `[TODO]` and flag it rather than guessing.

- `PROJECT` name and one-line goal
- `PHASES` - ordered phase list (Phase 0 spine first, then one slice end-to-end at a time)
- `STACK` specifics and any domain rules (e.g. Decimal money never float; Australia/Melbourne
  DST-correct bucketing; license-gating)
- `DECISIONS_DOC` path (default `docs/decisions.md`)

## Step 3 - Emit the brief

Fill the template for the chosen mode. Keep the wording verbatim except the fill-ins - these
rules are the standing contract and must not drift.

### Common rules (both modes)

```
- Read ~/Metisary/Enviroment/config/docs/engineering-constitution.md FIRST and treat it as binding.
- Phases, each its own branch + PR: [PHASES]. Phase 0 = spine (repo, CI/CD, backend skeleton,
  frontend shell, settings store, health-check framework), then one slice end-to-end at a time
  in priority order.
- Conventional commits ({type}({scope}): {description}). One logical change per PR. Tests in the
  same PR. CHANGELOG under [Unreleased] every PR. Never commit to main; never force-push or
  rewrite shared history.
- Secret hygiene: run `gitleaks git --staged --redact` before every commit and
  `gitleaks git --redact --log-opts='<remote-base>..HEAD'` over the exact outgoing
  range before every push. Scanner findings block publication.
  No secrets in git, memory files, or logs. .env.example with names only.
- No scope creep. Where the spec leaves a decision open, pick the lowest-risk option, record it
  and the reasoning in [DECISIONS_DOC], and keep going.
- Open source is license-gated: no GPL/AGPL copy-paste; prefer pinned maintained libs; attribute
  in docs/third-party.md.
- AI review: use the canonical autoreview skill and repository-required reviews. Self-fix loop on any failing gate:
  hypothesize 3-4 root causes, confirm with evidence, fix, re-run. Max 3 attempts per failure;
  on the 3rd, stop, report the last known-good commit hash, and wait for confirmation
  before resetting or trying a different approach.
```

### Mode A - Autonomous (append to common rules)

```
Autonomous implementation within the approved scope.
Existing user approvals persist; repository safeguards and merge authorization still apply.

## Autonomous execution
- Prepare each PR after its tests, lint/type/build, secret scans and required reviews pass.
- Merge only when authorized by the user and permitted by repository policy; otherwise report it ready for review.
```

### Mode B - Human-gated (append to common rules)

```
Phased build. Standard human-in-the-loop applies: the human presses merge on every PR.

## User review gate
- At the end of each phase/PR, STOP at a <HARD-GATE> and summarize: what shipped, gate status
  (CI/tests/lint/secret-scan/@codex review), and what is next. Do not start the next phase or
  merge until the human approves.
```

## Step 4 - Hand off

State the chosen mode and the filled phase list back to the user, then proceed via the normal
execution path. For autonomous runs, `loop` can drive the phase sequence; for gated runs, stop
after each phase as specified.

## Notes

- Execution mode never overrides repository safeguards or grants merge/reset authority.
- This brief is the standing contract pasted at the start of builds across PriceHawk, Monarr,
  Helmarr, and similar greenfield projects; keep it in sync with AGENTS.md and the constitution.
