#!/usr/bin/env python3
"""PreToolUse guard for the model routing ladder in AGENTS.MD (Parallel Agents).

Reads one Claude Code or Codex hook payload from stdin and denies delegations
that break the ladder: a T3 `delegate_task` without an explicit model, any
delegation above L2 without an `[escalate:L3]` or `[escalate:L4]` tag and a
named trigger, and Cursor children with fast mode or a large context.
A deny is a PreToolUse `hookSpecificOutput` decision on stdout with exit 0.
Other tools and allowed calls produce no output.
The guard fails closed: a payload it cannot read is denied with a generic reason.
"""
import json
import os
import re
import sys

HIGH_EFFORT = {"xhigh", "max", "ultra", "ultracode", "ultrathink"}
L4_FAMILIES = ("fable", "mythos")
L3_FAMILIES = ("astra",)
EFFORT_KEYS = ("effort", "reasoningEffort", "reasoning_effort", "reasoning")
LARGE_CONTEXTS = {"500k", "1m"}
NATIVE_AGENT_TOOLS = {"agent", "task"}
FRONTMATTER_FIELD = re.compile(r"^(name|model|effort):[ \t]*(.*?)[ \t]*$")
LADDER = "the routing ladder in AGENTS.MD (Parallel Agents)"
TRIGGER_MARKER = re.compile(r"\btrigger:\s*\S", re.IGNORECASE)


def decision(reason):
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    })


def option_map(options):
    if isinstance(options, dict):
        return {str(key): value for key, value in options.items()}
    if isinstance(options, list):
        return {
            str(entry.get("id")): entry.get("value")
            for entry in options
            if isinstance(entry, dict)
        }
    return {}


def escalation_level(*texts):
    joined = " ".join(str(text or "") for text in texts).lower()
    if "[escalate:l4]" in joined:
        return 4
    if "[escalate:l3]" in joined:
        return 3
    return 0


def effort_of(options):
    for key in EFFORT_KEYS:
        if options.get(key) is not None:
            return str(options[key]).lower()
    return ""


def names_trigger(text):
    return bool(TRIGGER_MARKER.search(str(text or "")))


CONTEXT_SUFFIX = re.compile(r"\[([^\]]+)\]\s*$")


def context_suffix(model):
    """Context window requested inside the model id, such as the 1m in claude-sonnet-5-5[1m]."""
    match = CONTEXT_SUFFIX.search(str(model or "").strip().lower())
    return match.group(1).strip() if match else ""


def model_family(model):
    """Vendor-neutral family of a model id: strips provider prefixes, regions, versions and context suffixes."""
    text = str(model or "").strip().lower()
    text = text.split("[", 1)[0]  # claude-fable-5-1[1m]
    text = text.split("/")[-1]  # bedrock/eu/anthropic.claude-fable-5-1, publishers/anthropic/models/...
    text = text.split("@", 1)[0]  # vertex claude-opus-4-5@20251101
    text = re.sub(r":\d+$", "", text)  # bedrock ...-v1:0
    text = re.sub(r"-v\d+$", "", text)
    text = re.sub(r"^(?:[a-z]{2,6}\.)*anthropic\.", "", text)  # us.anthropic. / anthropic.
    stripped = True
    while stripped:
        stripped = False
        for marker in ("anthropic.", "claude-", "gpt-"):
            if text.startswith(marker):
                text = text[len(marker):]
                stripped = True
    return text


def is_l4_model(model):
    family = model_family(model)
    return any(family == name or family.startswith(name + "-") for name in L4_FAMILIES)


def is_l3_model(model):
    family = model_family(model)
    return any(family.startswith(name) for name in L3_FAMILIES) or family.startswith("6-astra")


def truthy(value):
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def check_delegate_task(tool_input):
    target = tool_input.get("target") or {}
    if not isinstance(target, dict):
        target = {}
    model = str(target.get("model") or "").strip()
    title = str(tool_input.get("title") or "")
    task = str(tool_input.get("task") or "")
    level = escalation_level(title, task)
    if not model:
        return (
            "delegate_task has no target.model, so the child would inherit the "
            f"parent's model and effort. Set target per {LADDER}."
        )
    if level and not names_trigger(task):
        return "An [escalate:Lx] tag needs a 'Trigger: <reason>' marker in the task text."
    if is_l4_model(model) and level < 4:
        return f"{model} is L4 and needs Ryan's approval: add [escalate:L4] to the title and name the trigger."
    if is_l3_model(model) and level < 3:
        return f"{model} is L3 or above: add [escalate:L3] to the title and name the trigger."
    options = option_map(target.get("options"))
    effort = effort_of(options)
    if effort in HIGH_EFFORT and level < 3:
        return f"effort {effort} is L3 or above: add [escalate:L3] to the title and name the trigger, or use high."
    if level < 3:
        if truthy(options.get("fastMode")):
            return "fast mode costs 2x to 6x the standard rate on every provider; children run with fastMode false."
        if str(options.get("contextWindow") or "").lower() in LARGE_CONTEXTS or context_suffix(model) in LARGE_CONTEXTS:
            return "Large contexts double the rate; children use the smaller option (256k Grok, 300k Claude) and no [1m] suffix."
    return None


def parse_frontmatter(head):
    """name, model and effort from a definition's front matter; values must sit on their own line."""
    if not head.startswith("---"):
        return None
    fields = {}
    for line in head[3:].split("\n---", 1)[0].splitlines():
        match = FRONTMATTER_FIELD.match(line)
        if match:
            fields[match.group(1)] = match.group(2).split(" #", 1)[0].strip().strip("'\"")
    return fields


def agent_roots(cwd):
    """Project `.claude/agents` directories from cwd up to the repository root, nearest first, then the user's."""
    roots = []
    current = os.path.abspath(str(cwd or os.getcwd()))
    while True:
        roots.append(os.path.join(current, ".claude", "agents"))
        parent = os.path.dirname(current)
        if os.path.isdir(os.path.join(current, ".git")) or os.path.isfile(os.path.join(current, ".git")) or parent == current:
            break
        current = parent
    roots.append(os.path.join(os.path.expanduser("~"), ".claude", "agents"))
    return roots


def definition_settings(subagent_type, cwd):
    """(model, effort) declared by the agent definition whose front matter `name` matches, or None.

    Mirrors Claude Code discovery: project definitions, searched recursively from
    cwd up to the repository root, win over user ones. Plugin-namespaced types
    such as ``pstack:deep`` are never resolved: their definitions live in plugin
    caches, so the call must name its model.
    """
    name = str(subagent_type or "").strip()
    if not name or ":" in name or "/" in name or name.startswith("."):
        return None
    for root in agent_roots(cwd):
        if not os.path.isdir(root):
            continue
        for directory, _subdirs, files in sorted(os.walk(root)):
            for entry in sorted(files):
                if not entry.endswith(".md"):
                    continue
                try:
                    with open(os.path.join(directory, entry), encoding="utf-8") as handle:
                        fields = parse_frontmatter(handle.read(4096))
                except OSError:
                    continue
                if fields and fields.get("name") == name:
                    return (fields.get("model", "").lower(), fields.get("effort", "").lower())
    return None


def check_native_agent(tool_input, cwd):
    model = str(tool_input.get("model") or "").strip().lower()
    effort = str(tool_input.get("effort") or "").strip().lower()
    subagent_type = str(tool_input.get("subagent_type") or "").strip()
    prompt = str(tool_input.get("prompt") or "")
    level = escalation_level(tool_input.get("description"), prompt)
    if level and not names_trigger(prompt):
        return "An [escalate:Lx] tag needs a 'Trigger: <reason>' marker in the prompt."
    if subagent_type == "fork":
        return None  # fork continues the parent's context and model by design
    settings = definition_settings(subagent_type, cwd) or ("", "")
    definition_model, definition_effort = settings
    env_model = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "").strip().lower()
    if truthy(os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "")):
        if not env_model or env_model == "inherit":
            return "CLAUDE_CODE_SUBAGENT_MODEL_FORCE is set without a concrete CLAUDE_CODE_SUBAGENT_MODEL, so every subagent inherits an unknown model; unset it or name the model."
        model = env_model
    elif not model:
        if definition_model == "inherit":
            return f"'{subagent_type}' declares model: inherit, so it would run on the parent's model. Pass model (haiku, sonnet, opus) explicitly; only fork inherits by design."
        model = definition_model  # CLAUDE_CODE_SUBAGENT_MODEL is not a safe fallback: built-in types ignore it
        if not model:
            return (
                f"Agent call names no model and '{subagent_type or 'general-purpose'}' has no resolvable model in "
                "its definition, so it would inherit the parent. Set model (haiku, sonnet, opus) and effort; "
                "plugin agents always need an explicit model; only fork inherits by design."
            )
    if is_l4_model(model) and level < 4:
        return "Agent model fable is L4 and needs Ryan's approval: add [escalate:L4] and name the trigger."
    effort = effort or definition_effort
    env_effort = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL", "").strip().lower()
    if env_effort:
        effort = env_effort
    if context_suffix(model) in LARGE_CONTEXTS and level < 3:
        return "Large contexts double the rate; drop the [1m] suffix from the Agent model below L3."
    if not effort:
        return "Agent call resolves no effort from the call, the agent definition or CLAUDE_CODE_EFFORT_LEVEL, so it would inherit the session's effort. Set effort (medium or high)."
    if effort in HIGH_EFFORT and level < 3:
        return f"Agent effort {effort} is L3: add [escalate:L3] to the description and name the trigger, or use high."
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        tool_name = str(payload.get("tool_name") or "")
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        lowered = tool_name.lower()
        if "delegate_task" in lowered:
            reason = check_delegate_task(tool_input)
        elif lowered in NATIVE_AGENT_TOOLS:
            reason = check_native_agent(tool_input, payload.get("cwd"))
        else:
            return 0
    except Exception as error:  # fail closed without echoing the payload
        reason = (
            f"delegate guard could not read the hook payload ({type(error).__name__}); "
            "fix the hook before delegating."
        )
    if reason:
        print(decision(reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
