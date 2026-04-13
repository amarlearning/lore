"""
UserPromptSubmit hook — fires at the start of every agent session.
This is where we learn the session's working directory and register it.
"""

import json

from lore_core.store import find_lore_dir, session_temp_dir
from lore_daemon.registry import registry


_REASONING_CONTEXT = (
    "When making any significant implementation decision — choosing an algorithm, "
    "picking a library, structuring a component, or selecting an approach over an alternative — "
    "briefly state why in your response. One sentence is enough: what you chose and what you "
    "rejected. This is the only way the reasoning behind this codebase gets preserved."
)


def handle(payload: dict) -> dict:
    session_id = payload.get("session_id", "unknown")
    cwd = payload.get("cwd", "")

    lore_dir = find_lore_dir(cwd) if cwd else None

    if lore_dir is None:
        print(f"  [prompt] no .lore/ found for cwd={cwd!r} — session {session_id} not tracked")
        return {}

    temp_dir = session_temp_dir(lore_dir, session_id)
    registry.register(session_id, temp_dir)

    prompts_file = temp_dir / "prompts.jsonl"
    with prompts_file.open("a") as f:
        f.write(json.dumps(payload) + "\n")

    print(f"  [prompt] session {session_id} → {temp_dir}")
    return {"additionalContext": _REASONING_CONTEXT}
