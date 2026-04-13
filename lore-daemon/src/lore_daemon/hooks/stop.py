"""
Stop hook — fires when Claude finishes responding to a prompt.
A session can have multiple prompts, so this appends to task_completions.jsonl.
"""

import json
from datetime import datetime, timezone

from lore_daemon.registry import registry


def handle(payload: dict) -> None:
    session_id = payload.get("session_id", "unknown")
    temp_dir = registry.get(session_id)

    if temp_dir is None:
        print(f"  [stop] session {session_id} not registered — nothing to record")
        return

    record = {**payload, "completed_at": datetime.now(timezone.utc).isoformat()}

    completions_file = temp_dir / "task_completions.jsonl"
    with completions_file.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"  [stop] session {session_id} — task complete")
