#!/bin/bash
# Canonical locations of Ryan's agent environment, shared by scripts/sync-skills
# and skills/fleet-maintenance/scripts/agent-skill-links-audit.sh.
#
# These two tools must agree: the audit reports drift against whatever the sync
# would create, so a value present in one and stale in the other makes the audit
# report false failures. That happened when the audit moved to the Metisary
# layout and sync-skills kept the old ~/Projects/agent-scripts literals.
#
# Paths stay $HOME-relative on purpose. scripts/test-sync-skills runs the real
# scripts under a synthetic HOME, so deriving these from the script's own
# location would resolve to the real checkout and defeat that isolation.

CANONICAL_CONFIG_ROOT="$HOME/Metisary/Enviroment/config"
CANONICAL_MANAGER_ROOT="$HOME/Metisary/Enviroment/manager"

CANONICAL_AGENT_SKILLS="$CANONICAL_CONFIG_ROOT/skills"
CANONICAL_MANAGER_SKILLS="$CANONICAL_MANAGER_ROOT/skills"
CANONICAL_AGENTS_MD="$CANONICAL_CONFIG_ROOT/AGENTS.MD"
CANONICAL_SYNC_SKILLS="$CANONICAL_CONFIG_ROOT/scripts/sync-skills"

CANONICAL_CODEX_ROOT="$HOME/.codex/skills"
CANONICAL_CLAUDE_ROOT="$HOME/.claude/skills"

# Harness aliases may intentionally select a nested variant of a shared skill.
canonical_skill_link() {
  [ -L "$1" ] && [ -f "$1/SKILL.md" ] || return 1
  local physical
  physical=$(cd "$1" && pwd -P) || return 1
  [ "${physical##*/}" = "${1##*/}" ] || return 1
  case "$physical" in
    "$CANONICAL_AGENT_SKILLS"/*) return 0 ;;
    *) return 1 ;;
  esac
}
