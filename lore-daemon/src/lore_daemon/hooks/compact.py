"""
PreCompact hook — fires before Claude Code compacts the context window.
This is the most important hook: captures full session state before reasoning is discarded.
"""

import json

from lore_daemon.registry import registry


def handle(payload: dict) -> None:
    session_id = payload.get("session_id", "unknown")
    temp_dir = registry.get(session_id)

    if temp_dir is None:
        print(f"  [compact] session {session_id} not registered — dropping event")
        return

    compact_file = temp_dir / "compact_events.jsonl"
    with compact_file.open("a") as f:
        f.write(json.dumps(payload) + "\n")

    print(f"  [compact] {session_id} — session state captured before compaction")
