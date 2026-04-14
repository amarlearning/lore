import pytest
import json
from unittest.mock import patch
from lore_daemon.hooks import prompt, tool, pre_tool, compact, stop
from lore_daemon.registry import registry


@pytest.fixture
def lore_env(tmp_path):
    lore_dir = tmp_path / ".lore"
    lore_dir.mkdir()
    (lore_dir / "temp").mkdir()
    (lore_dir / "decisions").mkdir()
    yield tmp_path, lore_dir


def test_prompt_handle(lore_env):
    root, lore_dir = lore_env
    session_id = "test-session-123"
    payload = {"session_id": session_id, "cwd": str(root)}

    with patch("lore_daemon.hooks.prompt.find_lore_dir", return_value=lore_dir):
        context = prompt.handle(payload)

        # Verify context injection
        assert "additionalContext" in context

        # Verify registry registration
        assert registry.get(session_id) is not None

        # Verify file creation
        temp_dir = lore_dir / "temp" / session_id
        assert (temp_dir / "prompts.jsonl").exists()


def test_tool_handle(lore_env):
    root, lore_dir = lore_env
    session_id = "test-session-456"
    temp_dir = lore_dir / "temp" / session_id
    temp_dir.mkdir(parents=True)
    registry.register(session_id, temp_dir)

    payload = {
        "session_id": session_id,
        "type": "PostToolUse",
        "data": {"tool": "Write", "file": "app.py"},
    }

    tool.handle(payload)

    # Verify tool event was logged
    assert (temp_dir / "tool_events.jsonl").exists()
    with open(temp_dir / "tool_events.jsonl", "r") as f:
        line = f.readline()
        assert json.loads(line) == payload


def test_compact_handle(lore_env):
    root, lore_dir = lore_env
    session_id = "test-session-789"
    temp_dir = lore_dir / "temp" / session_id
    temp_dir.mkdir(parents=True)
    registry.register(session_id, temp_dir)

    payload = {"session_id": session_id, "reasoning": "compacted reasoning"}

    compact.handle(payload)

    # Verify compact event was logged
    assert (temp_dir / "compact_events.jsonl").exists()


def test_stop_handle(lore_env):
    root, lore_dir = lore_env
    session_id = "test-session-abc"
    temp_dir = lore_dir / "temp" / session_id
    temp_dir.mkdir(parents=True)
    registry.register(session_id, temp_dir)

    payload = {"session_id": session_id, "status": "finished"}

    stop.handle(payload)

    # Verify stop event was logged
    assert (temp_dir / "task_completions.jsonl").exists()


def test_pre_tool_handle(lore_env):
    root, lore_dir = lore_env
    session_id = "test-session-pretool"
    temp_dir = lore_dir / "temp" / session_id
    temp_dir.mkdir(parents=True)
    registry.register(session_id, temp_dir)

    # Create a decision in decisions/
    decisions_dir = lore_dir / "decisions"
    decision_file = decisions_dir / "abc123.yaml"
    decision_file.write_text("file: app.py\nreasoning: test reasoning")

    payload = {
        "session_id": session_id,
        "tool_input": {"file_path": "app.py"},
    }

    # Mock find_decisions_for_file to return a match
    with patch(
        "lore_daemon.hooks.pre_tool.find_decisions_for_file",
        return_value=["test reasoning"],
    ):
        context = pre_tool.handle(payload)
        assert "additionalContext" in context
        assert "test reasoning" in context["additionalContext"]
