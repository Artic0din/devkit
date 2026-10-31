import json
import os
from pathlib import Path
import subprocess
import tempfile

GUARD = Path(__file__).with_name("delegate-guard.py")


def run_guard(payload, home=None, extra_env=None) -> str:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    env = {key: value for key, value in os.environ.items() if not key.startswith("CLAUDE_CODE_")}
    env.update({"HOME": home or os.environ.get("HOME", ""), **(extra_env or {})})
    result = subprocess.run(
        ["python3", str(GUARD)], input=raw, text=True, capture_output=True, timeout=5, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    return result.stdout


def denied(payload, home=None, extra_env=None) -> str:
    output = run_guard(payload, home, extra_env)
    assert output, "expected a deny decision"
    decision = json.loads(output)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    return decision["permissionDecisionReason"]


def allowed(payload, home=None, extra_env=None) -> None:
    assert run_guard(payload, home, extra_env) == "", "expected silence for an allowed call"


def delegate(target, title="child", task="Do the thing.", tool_name="mcp__t3-code__delegate_task"):
    tool_input = {"task": task, "title": title}
    if target is not None:
        tool_input["target"] = target
    return {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}


def test_other_tools_pass_through() -> None:
    allowed({"tool_name": "Bash", "tool_input": {"command": "ls"}})
    allowed({"tool_name": "Read", "tool_input": {}})


def test_delegate_requires_explicit_model() -> None:
    assert "inherit" in denied(delegate(None))
    assert "inherit" in denied(delegate({"providerInstanceId": "claudeAgent"}))
    allowed(delegate({"providerInstanceId": "claudeAgent", "model": "claude-sonnet-5-5", "options": {"effort": "high"}}))
    allowed(delegate({"providerInstanceId": "codex", "model": "gpt-6.1-sol",
                      "options": [{"id": "reasoningEffort", "value": "medium"}, {"id": "serviceTier", "value": "default"}]}))


def test_high_effort_needs_l3_tag_and_trigger() -> None:
    sol_xhigh = {"providerInstanceId": "codex", "model": "gpt-6.1-sol", "options": {"reasoningEffort": "xhigh"}}
    assert "L3" in denied(delegate(sol_xhigh))
    assert "trigger" in denied(delegate(sol_xhigh, title="[escalate:L3] retry")).lower()
    allowed(delegate(sol_xhigh, title="[escalate:L3] retry", task="Trigger: L2 failed verification. Fix the parser."))
    for effort in ("max", "ultra", "ultracode", "ultrathink"):
        assert "L3" in denied(delegate({"providerInstanceId": "claudeAgent", "model": "claude-opus-5-5", "options": {"effort": effort}}))
    allowed(delegate({"providerInstanceId": "claudeAgent", "model": "claude-opus-5-5", "options": {"effort": "high"}}))


def test_astra_and_fable_levels() -> None:
    astra = {"providerInstanceId": "codex", "model": "gpt-6-astra", "options": {"reasoningEffort": "low"}}
    assert "L3" in denied(delegate(astra))
    allowed(delegate(astra, title="[escalate:L3] hard bug", task="Trigger: two levels failed."))
    fable = {"providerInstanceId": "claudeAgent", "model": "claude-fable-5-1", "options": {"effort": "high"}}
    assert "L4" in denied(delegate(fable))
    assert "L4" in denied(delegate(fable, title="[escalate:L3] x", task="Trigger: y"))
    allowed(delegate(fable, title="[escalate:L4] approved", task="Trigger: Ryan approved L4."))


def test_cursor_children_run_cheap() -> None:
    assert "fast mode" in denied(delegate({"providerInstanceId": "cursor", "model": "composer-2.5", "options": {"fastMode": True}}))
    assert "fast mode" in denied(delegate({"providerInstanceId": "cursor-work", "driverKind": "cursor", "model": "composer-2.5", "options": {"fastMode": True}}))
    assert "fast mode" in denied(delegate({"providerInstanceId": "claudeAgent", "model": "claude-opus-5-5", "options": {"effort": "high", "fastMode": True}}))
    assert "fast mode" in denied(delegate({"providerInstanceId": "cursor", "model": "composer-2.5", "options": [{"id": "fastMode", "value": "true"}]}))
    allowed(delegate({"providerInstanceId": "cursor", "model": "composer-2.5", "options": {"fastMode": False}}))
    assert "context" in denied(delegate({"providerInstanceId": "cursor", "model": "grok-4.7", "options": {"contextWindow": "500k", "fastMode": False}}))
    assert "context" in denied(delegate({"providerInstanceId": "cursor", "model": "claude-opus-5-5", "options": {"effort": "high", "contextWindow": "1m", "fastMode": False}}))
    allowed(delegate({"providerInstanceId": "cursor", "model": "claude-opus-5-5", "options": {"effort": "high", "contextWindow": "300k", "fastMode": False}}))
    allowed(delegate({"providerInstanceId": "cursor", "model": "grok-4.7", "options": {"contextWindow": "256k", "fastMode": False, "reasoning_effort": "high"}}))
    allowed(delegate({"providerInstanceId": "cursor", "model": "grok-4.7", "options": {"contextWindow": "500k", "fastMode": True}},
                     title="[escalate:L3] big repo", task="Trigger: 400k token context needed after L2 failed."))


def test_trigger_marker_must_carry_a_reason() -> None:
    astra = {"providerInstanceId": "codex", "model": "gpt-6-astra", "options": {"reasoningEffort": "low"}}
    assert "trigger" in denied(delegate(astra, title="[escalate:L3] investigate", task="Fix event trigger ordering.")).lower()
    assert "trigger" in denied(delegate(astra, title="[escalate:L3] investigate", task="Trigger:   ")).lower()
    allowed(delegate(astra, title="[escalate:L3] investigate", task="trigger: L2 failed verification twice."))
    assert "trigger" in denied({"tool_name": "Agent", "tool_input": {"description": "[escalate:L3] deep", "prompt": "Handle the trigger carefully.", "model": "opus", "effort": "xhigh"}}).lower()


def test_model_spellings_normalise() -> None:
    for spelling in ("claude-fable-5-1[1m]", "anthropic.claude-fable-5-1", "bedrock/eu/anthropic.claude-fable-5", "claude-mythos-5-1", "FABLE",
                     "claude-fable-5-1-20260901", "us.anthropic.claude-fable-5-1-v1:0", "apac.anthropic.claude-mythos-5-1-v1:0",
                     "claude-fable-5-1@20260901", "publishers/anthropic/models/claude-fable-5-1"):
        assert "L4" in denied(delegate({"providerInstanceId": "claudeAgent", "model": spelling, "options": {"effort": "high"}})), spelling
    for spelling in ("gpt-6-astra", "openai/gpt-6-astra", "gpt-6-astra-2026-09-03"):
        assert "L3" in denied(delegate({"providerInstanceId": "codex", "model": spelling, "options": {"reasoningEffort": "low"}})), spelling
    for spelling in ("claude-sonnet-5-5", "claude-opus-5-5", "us.anthropic.claude-sonnet-5-5-v1:0", "gpt-6.1-sol", "composer-2.5"):
        allowed(delegate({"providerInstanceId": "claudeAgent", "model": spelling, "options": {"effort": "high"}}))
    assert "context" in denied(delegate({"providerInstanceId": "claudeAgent", "model": "claude-sonnet-5-5[1m]", "options": {"effort": "high"}}))
    allowed(delegate({"providerInstanceId": "claudeAgent", "model": "claude-sonnet-5-5[1m]", "options": {"effort": "high"}},
                     title="[escalate:L3] whole repo", task="Trigger: L2 failed on a 600k token repo."))
    with tempfile.TemporaryDirectory() as home:
        assert "context" in denied({"tool_name": "Agent", "cwd": home, "tool_input": {"description": "big", "prompt": "Read all.", "model": "sonnet[1m]", "effort": "high"}}, home)
    with tempfile.TemporaryDirectory() as home:
        force = {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1", "CLAUDE_CODE_SUBAGENT_MODEL": "claude-fable-5-1[1m]"}
        assert "L4" in denied({"tool_name": "Agent", "cwd": home, "tool_input": {"description": "fix", "prompt": "Fix it.", "model": "sonnet", "effort": "high"}}, home, force)


def test_codex_style_tool_name_matches() -> None:
    assert "inherit" in denied(delegate(None, tool_name="t3-code/delegate_task"))


def test_native_agent_rules() -> None:
    with tempfile.TemporaryDirectory() as home:
        agents = Path(home) / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "Explore.md").write_text("---\nname: Explore\nmodel: haiku\neffort: medium\n---\nbody\n")
        (agents / "deep.md").write_text("---\nname: deep\nmodel: fable\neffort: high\n---\nbody\n")
        (agents / "inheriting.md").write_text("---\nname: inheriting\nmodel: inherit\n---\nbody\n")
        agent = lambda **tool_input: {"tool_name": "Agent", "cwd": home, "tool_input": tool_input}
        allowed(agent(description="explore", prompt="Find callers.", subagent_type="Explore"), home)
        allowed(agent(description="fix", prompt="Fix it.", model="sonnet", effort="high"), home)
        allowed(agent(description="fork", prompt="Continue.", subagent_type="fork"), home)
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="general-purpose"), home)
        assert "inherit" in denied(agent(description="plan", prompt="Plan it."), home)
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="inheriting"), home)
        assert "L4" in denied(agent(description="deep", prompt="Think.", subagent_type="deep"), home)
        assert "explicit model" in denied(agent(description="deep", prompt="Think.", subagent_type="pstack:deep"), home)
        allowed(agent(description="deep", prompt="Think.", subagent_type="pstack:deep", model="sonnet", effort="high"), home)
        (agents / "hot.md").write_text("---\nname: hot\nmodel: opus\neffort: max\n---\nbody\n")
        assert "L3" in denied(agent(description="hot", prompt="Go.", subagent_type="hot"), home)
        assert "L3" in denied(agent(description="hot", prompt="Go.", subagent_type="hot", model="sonnet"), home)
        allowed(agent(description="hot", prompt="Go.", subagent_type="hot", effort="high"), home)
        allowed(agent(description="[escalate:L3] hot", prompt="Trigger: L2 failed. Go.", subagent_type="hot"), home)
        assert "L3" in denied(agent(description="fix", prompt="Fix it.", model="sonnet"), home, {"CLAUDE_CODE_EFFORT_LEVEL": "max"})
        force = {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1", "CLAUDE_CODE_SUBAGENT_MODEL": "fable"}
        assert "L4" in denied(agent(description="fix", prompt="Fix it.", model="sonnet", effort="high"), home, force)
        assert "L4" in denied(agent(description="explore", prompt="Find callers.", subagent_type="Explore"), home, force)
        assert "unknown" in denied(agent(description="fix", prompt="Fix it.", model="sonnet"), home, {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "true"})
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="general-purpose"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku", "CLAUDE_CODE_EFFORT_LEVEL": "medium"})
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="Plan"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku", "CLAUDE_CODE_EFFORT_LEVEL": "medium"})
        assert "effort" in denied(agent(description="plan", prompt="Plan it.", subagent_type="general-purpose"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"})
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="inheriting"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku", "CLAUDE_CODE_EFFORT_LEVEL": "medium"})
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="general-purpose"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "inherit", "CLAUDE_CODE_EFFORT_LEVEL": "medium"})
        assert "effort" in denied(agent(description="fix", prompt="Fix it.", model="sonnet"), home)
        (agents / "warm.md").write_text("---\nname: warm\nmodel: opus\neffort: high\n---\nbody\n")
        allowed(agent(description="warm", prompt="Go.", subagent_type="warm", model="sonnet"), home)
        assert "inherit" in denied(agent(description="plan", prompt="Plan it.", subagent_type="general-purpose"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "fable"})
        (agents / "alias.md").write_text("---\nname: researcher\nmodel: haiku\neffort: medium\n---\nbody\n")
        (agents / "researcher.md").write_text("---\nname: other\nmodel: fable\neffort: high\n---\nbody\n")
        allowed(agent(description="r", prompt="Read docs.", subagent_type="researcher"), home)
        assert "L4" in denied(agent(description="o", prompt="Think.", subagent_type="other"), home)
        (agents / "blank.md").write_text("---\nname: blank\nmodel:\neffort: high\n---\nbody\n")
        assert "inherit" in denied(agent(description="b", prompt="Go.", subagent_type="blank"), home)
        (agents / "noeffort.md").write_text("---\nname: noeffort\nmodel: sonnet\neffort:\ncolor: blue\n---\nbody\n")
        assert "effort" in denied(agent(description="n", prompt="Go.", subagent_type="noeffort"), home)
        allowed(agent(description="fix", prompt="Fix it.", model="sonnet", effort="high"), home, {"CLAUDE_CODE_SUBAGENT_MODEL": "fable"})
        allowed(agent(description="fix", prompt="Fix it.", model="sonnet"), home, {"CLAUDE_CODE_EFFORT_LEVEL": "high"})
        assert "L4" in denied(agent(description="deep", prompt="Think.", model="fable", effort="high"), home)
        assert "L3" in denied({"tool_name": "Task", "cwd": home, "tool_input": {"description": "deep", "prompt": "Think.", "model": "opus", "effort": "max"}}, home)
        allowed(agent(description="[escalate:L4] deep", prompt="Trigger: Ryan approved. Think.", model="fable", effort="high"), home)
        allowed(agent(description="[escalate:L4] deep", prompt="Trigger: Ryan approved. Think.", subagent_type="deep"), home)
        assert "trigger" in denied(agent(description="[escalate:L3] deep", prompt="Think.", model="opus", effort="xhigh"), home).lower()
        project = Path(home) / "proj" / ".claude" / "agents"
        project.mkdir(parents=True)
        (Path(home) / "proj" / ".git").mkdir()
        (project / "worker.md").write_text("---\nname: worker\nmodel: opus\neffort: medium\n---\nbody\n")
        allowed({"tool_name": "Agent", "cwd": str(Path(home) / "proj"), "tool_input": {"description": "w", "prompt": "Work.", "subagent_type": "worker"}}, home)
        (agents / "nested-user.md").write_text("---\nname: nested\nmodel: haiku\neffort: medium\n---\nbody\n")
        (project / "review").mkdir()
        (project / "review" / "nested.md").write_text("---\nname: nested\nmodel: fable\neffort: high\n---\nbody\n")
        sub = Path(home) / "proj" / "src" / "deep"
        sub.mkdir(parents=True)
        assert "L4" in denied({"tool_name": "Agent", "cwd": str(sub), "tool_input": {"description": "n", "prompt": "Go.", "subagent_type": "nested"}}, home)
        allowed({"tool_name": "Agent", "cwd": home, "tool_input": {"description": "n", "prompt": "Go.", "subagent_type": "nested"}}, home)


def test_malformed_payload_fails_closed() -> None:
    reason = denied("{not json")
    assert "could not read" in reason
    assert "not json" not in reason
    reason = denied({"tool_name": "mcp__t3-code__delegate_task", "tool_input": "oops"})
    assert "inherit" in reason


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
    print("PASS: pass-through, explicit targets, escalation tags, Cursor limits, native Agent, fail closed")
