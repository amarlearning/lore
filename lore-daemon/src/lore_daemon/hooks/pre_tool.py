"""
PreToolUse hook — fires before Claude writes/edits a file.
Looks up decisions/ for anything relevant to the file being touched
and returns it as additionalContext so Claude sees constraints before writing.
"""

from lore_core.store import find_decisions_for_file
from lore_daemon.registry import registry


def handle(payload: dict) -> dict:
    session_id = payload.get("session_id", "unknown")
    file_path = payload.get("tool_input", {}).get("file_path", "")

    print(f"  [pre-tool] {session_id} about to touch {file_path!r}")

    if not file_path:
        return {}

    temp_dir = registry.get(session_id)
    if temp_dir is None:
        return {}

    # temp_dir is .lore/temp/<session_id>/ — walk up two levels to get .lore/
    lore_dir = temp_dir.parent.parent

    decisions = find_decisions_for_file(lore_dir, file_path)
    if not decisions:
        return {}

    combined = "\n\n---\n\n".join(decisions)
    context = f"Lore has recorded prior decisions for {file_path}:\n\n{combined}"

    print(f"  [pre-tool] injecting {len(decisions)} decision(s) for {file_path!r}")
    return {"additionalContext": context}
