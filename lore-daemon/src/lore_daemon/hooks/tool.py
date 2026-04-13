"""
PostToolUse hook — fires after every tool execution.
Appends one JSON line to tool_events.jsonl in the session's temp dir.
"""

import json

from lore_daemon.registry import registry


def handle(payload: dict) -> None:
    session_id = payload.get("session_id", "unknown")
    temp_dir = registry.get(session_id)

    if temp_dir is None:
        print(f"  [tool] session {session_id} not registered — dropping event")
        return

    tool_name = payload.get("tool_name", "?")
    file_path = payload.get("tool_input", {}).get("file_path", "")

    events_file = temp_dir / "tool_events.jsonl"
    with events_file.open("a") as f:
        f.write(json.dumps(payload) + "\n")

    print(f"  [tool] {session_id} | {tool_name} {file_path}")
