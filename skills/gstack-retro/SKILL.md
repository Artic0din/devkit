---
name: gstack-retro
description: "Review weekly engineering activity with Gstack. Use explicitly for shipping history, work patterns, and team metrics."
disable-model-invocation: true
---

# Gstack weekly retrospective

This command is separate from Matt Pocock's `retro`, which reviews a coding session.

Locate the installed Gstack source before selecting the active agent's instructions.
Check `../gstack` relative to this skill's resolved directory, then the active host's skill roots (`~/.codex/skills/gstack`, `~/.claude/skills/gstack`, or `~/.cursor/skills/gstack`).
Follow directory links and select a candidate containing the appropriate file below; this repository does not bundle the Gstack runtime.
Resolve the following paths inside that discovered Gstack directory:

- Codex: `.agents/skills/gstack-retro/SKILL.md`.
- Claude Code: `.harness/claude/retro/SKILL.md`, or `retro/SKILL.md` when no generated Claude variant exists.
- Other agents: use their installed Gstack variant; report a missing variant rather than inventing tool support.

Follow that file for the requested weekly review, preserving the user's scope and the current session's tool and permission rules.
If the selected file is missing, report that Gstack must be installed before this command can run.
Keep this registered name as `gstack-retro`; do not rename Matt's `retro` or edit generated Gstack files.
