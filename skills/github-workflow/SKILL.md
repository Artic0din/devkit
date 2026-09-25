---
name: github-workflow
description: Manage repository work through GitHub Issues, feature branches, pull requests, reviews, and CI.
---

# GitHub Workflow

Use GitHub Issues for planned work, pull requests and CI for implementation truth, and Basic Memory for reusable verified knowledge only.
The user-level `Development` Project is closed and must not be used.

## Route the request

- Small fix completed in one focused pull request: work directly without creating an issue.
- Planned, multi-session, backlog, or independently deliverable work: create or refine an issue.
- Multi-phase initiative: create the fewest independently deliverable issues, present the breakdown, and wait for explicit approval before implementation.
- Existing issue or URL: start or continue that issue.

## Create or refine an issue

1. Read the canonical and nearest repository `AGENTS.md` files.
2. Inspect the real repository and search existing open and closed issues before creating anything.
3. Use an actionable title and this minimal body:

```markdown
## Context
[Current evidence and why this matters]

## Goal
[Observable outcome]

## Acceptance criteria
- [ ] [Testable behaviour]
- [ ] [Required validation or error behaviour]

## Technical notes
[Verified constraints, pointers, dependencies, or exclusions]
```

4. Add only labels that improve retrieval; do not invent milestones, dates, estimates, or custom fields.

## Implement work

1. For both direct fixes and issue-backed work, create or reuse a feature branch before editing; never commit directly to main.
   Include the issue number only when linked to an actual issue, such as `fix/123-short-description`; otherwise use a conventional direct-fix name such as `fix/short-description`.
2. For issue-backed work, confirm the issue belongs to the repository and agrees with current code and instructions.
3. Implement and validate the approved outcome or issue acceptance criteria under repository rules.
4. When an issue exists, update its checkboxes only after verification; never treat them as a merge gate.

## Send work to review

1. Complete required validation and run `gitleaks git --staged --redact` before committing.
   Immediately before each push, run `gitleaks git --redact --log-opts='<remote-base>..HEAD'` over the exact outgoing range; findings block publication.
2. Open or update one focused pull request with a conventional title.
3. Include what changed, why, the test plan, and the required release note in the pull request body.
   Add `Fixes #123` only for an actual linked issue; direct-fix pull requests do not need an issue footer.
4. Keep issue state aligned with the pull request; pull request review state is authoritative.

## Complete work

- Let the merged pull request close the issue through `Fixes #123`.
- Confirm required checks passed, the pull request merged, and its linked issue closed.
- If a pull request closes without merge, keep or reopen the issue and return it to the appropriate active or backlog state.
- Store only reusable verified knowledge in Basic Memory; never mirror task status there.

## Safety

- Read before writing and avoid duplicate issues.
- Never create an issue merely to satisfy process for a small direct fix.
- Never infer completion from a comment, unchecked evidence, or an open pull request.
- Treat Slack and agent automations as triggers and notification surfaces; GitHub remains canonical.
