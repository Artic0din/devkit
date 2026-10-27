---
name: create-verification-skill
description: "Generate a project-local verification skill that drives your app the way a user does, for any language, framework, or platform, when explicitly asked to create a verification skill."
disable-model-invocation: true
---

# Create a verification skill

## Host support

Use the project's existing registered skill location when there is one.
Otherwise use `.agents/skills` for Codex, `.claude/skills` for Claude Code, or `.cursor/skills` for Cursor.
In the instructions below, `<project-skill-root>` means that chosen location.
Keep one source for each generated skill; use the project's established links if other agents need access.
Use tools actually available in the current session and follow their documentation.
Browser and native-app actions must use the permitted computer-use tools; do not assume Cursor tools, raw browser-control access, or a particular model.
The bundled Notes feature map is a format example, not an installed application or verified command set.
In Codex, invoke `$create-verification-skill` or `$maintain-verification-skill` explicitly.
In Claude Code and Cursor, use `/create-verification-skill` or `/maintain-verification-skill`.


Every serious project needs a scripted way to drive the real app and prove behavior: launch it, exercise a feature the way a user would, and capture evidence.
This skill generates that as a project-local skill (`<project-skill-root>/verify-<app>/`) tailored to the repo.
You write the generator's output for the next agent, not for a human: it will be read cold, mid-task, by an agent that has never seen the app.

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch?
  A web UI, a CLI/TUI, a desktop app, an API, a mobile app, a library?
  A repo can have several; pick the primary one and note the rest.
- **Run:** how does the app start locally?
  Prefer the repo's own documented dev command (package scripts, Makefile, README quickstart).
  Note ports, env vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically?
  Existing harnesses first — Playwright/Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port.
  Only then pick a generic recipe: browser/CDP for web and Electron, a tmux/PTY harness for CLI/TUI, plain HTTP for services.
- **Observe:** what evidence can be captured?
  Screenshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)?
  If not, say so in the generated skill: refusing to double-drive a shared instance beats corrupting the user's session.
  Can the app run against disposable local state (a scratch database, data directory, or profile, or a copy of fixture data)?
  Create, update, and delete checks must use that state; if the only runnable setup uses the user's persistent data, the generated skill marks those paths blocked instead of mutating it.

If the checkout doesn't build or start as-is, report the blocker before generating; repair product code only when the user has already authorized that work; a skill written against a broken base teaches wrong steps.
When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, clearly marked as verification scaffolding, and remove it in cleanup.

## 2. Generate the skill

Derive `<app>` from the display name as a short lowercase slug containing only letters, digits, and single hyphens between words.
Validate that the complete `verify-<app>` name matches `^[a-z0-9]+(?:-[a-z0-9]+)*$` and is at most 64 characters, including the `verify-` prefix.
Use that exact name for the directory and YAML `name`; do not substitute an unnormalized display name or overwrite an existing skill.

Write `<project-skill-root>/verify-<app>/SKILL.md` with YAML frontmatter (`name: verify-<app>` and a `description` that names the app, the surface, and when to reach for it) and these sections, each grounded in what the interview actually found (no placeholders left):

- **Launch:** the exact command that starts the app for verification, and how to tell it's ready (a log line, a port answering, a prompt).
  Include teardown.
  For a short-lived CLI or TUI there is no server to keep alive: launch means build the binary (or install deps) once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" — process up, right version/build, port owned by us, auth valid.
  An agent runs this first whenever anything looks off.
- **Drive:** the harness recipe with real selectors/commands from this repo, not examples.
  Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes.
  Use a unique run directory outside the worktree, or a directory confirmed ignored by Git before capture.
  Keep raw screenshots, response bodies, logs, and transcripts out of commits; inspect and redact evidence before any authorized sharing, including visual inspection of images.
  Before committing skill changes, inspect the staged file list for evidence and run the repository's secret scan.
  State the proof standards: exercise the real user path, not internal setters or test-only endpoints; capture the action and the resulting state, not just the final screen; verify side effects (files written, rows inserted, messages sent) alongside what's visible; mocks only where a production boundary already isolates the external system.
  Before any externally visible mutation, confirm that the current authorization covers that specific action and target.
  Use isolated external test accounts, recipients, payment environments, or resources; a disposable local instance alone does not isolate its downstream effects.
  If a safe authorized target is unavailable, mark the path blocked rather than sending, charging, publishing, or issuing a real control command to obtain proof.
  When the safe path is a dry-run or test mode, verify what it actually skips by observing (files, network, git refs) rather than trusting its name: some dry-runs still touch the network or open a browser.
- **Cleanup:** how to tear down instances the run created.
  Never kill by process name; kill what you started.
  Cleanup removes instances and scratch state, never the evidence: proof artifacts survive the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill body.
  A helper the reader has to reverse-engineer is not a helper.

## 3. Seed the feature map

Create `<project-skill-root>/verify-<app>/features/README.md` plus one file per user-facing feature identified from routes, commands, menus, or docs during the interview, including secondary surfaces.
Follow the shape in [`references/feature-map-example/`](references/feature-map-example/), with a README index and one file per feature.
Each file answers, from the user's point of view: what the feature is, how to reach it, how to drive it with the harness, and what observable end state proves it works.
Record known prerequisites or coverage blockers explicitly; do not silently omit identified features.
The four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`.
The map is the repo's maintained verification source; a proof that drives one convenient entry point is incomplete when the map lists others.

## 4. Prove the generated skill before handing it over

Run its own instructions end to end: launch, doctor, exercise every mapped user path and behavior, capture evidence, clean up.
Record each recipe's verification status; explicitly label any unexercised recipe as unverified with its blocker, and never describe a partly tested map as fully proven.
Check the project's required manifest, catalogue, or host links, update the relevant registration for the generated skill, and verify that the intended host discovers it before claiming activation.
If host discovery cannot be checked in the current session, distinguish written source from unverified activation in the handoff.
After cleanup, confirm the evidence still exists at the named location — a cleanup that eats the proof fails this step.
Fix what fails, and run the generated cleanup after every failed iteration too, so broken attempts don't strand processes and ports.
A generated skill that was never executed is a draft, not a deliverable.

## 5. Offer the maintenance loop

Point the user at `$maintain-verification-skill` in Codex, or `/maintain-verification-skill` in Claude Code and Cursor, for keeping the map honest as the app changes.
Suggest a cadence only if they ask.
