"""
In-memory map of session_id → .lore/temp/<session_id>/ path.
Populated on UserPromptSubmit. Looked up by every other hook.
"""

from pathlib import Path


class SessionRegistry:
    def __init__(self) -> None:
        self._map: dict[str, Path] = {}

    def register(self, session_id: str, temp_dir: Path) -> None:
        self._map[session_id] = temp_dir

    def get(self, session_id: str) -> Path | None:
        return self._map.get(session_id)

    def remove(self, session_id: str) -> None:
        self._map.pop(session_id, None)

    def all_sessions(self) -> dict[str, Path]:
        return dict(self._map)


# Single shared instance used across all hook handlers
registry = SessionRegistry()
