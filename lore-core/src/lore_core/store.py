"""
Utilities for finding and writing to the .lore/ directory.
The .lore/ dir is found by walking up from a given path — same mechanism git uses for .git/.
"""

from pathlib import Path


def find_lore_dir(cwd: str) -> Path | None:
    """Walk up from cwd until a .lore/ directory is found. Returns None if not found."""
    path = Path(cwd).resolve()
    while True:
        candidate = path / ".lore"
        if candidate.is_dir():
            return candidate
        parent = path.parent
        if parent == path:
            return None
        path = parent


def init_lore_dir(cwd: str) -> Path:
    """Create the .lore directory structure in the current directory."""
    lore_dir = Path(cwd).resolve() / ".lore"
    for sub in ["temp", "staging", "decisions"]:
        (lore_dir / sub).mkdir(parents=True, exist_ok=True)
    return lore_dir


def session_temp_dir(lore_dir: Path, session_id: str) -> Path:
    """Return (and create) the temp directory for a session."""
    temp = lore_dir / "temp" / session_id
    temp.mkdir(parents=True, exist_ok=True)
    return temp


def find_decisions_for_file(lore_dir: Path, file_path: str) -> list[str]:
    """
    Return the contents of any decision records in decisions/ that mention file_path.
    Matches on the full path or just the filename.
    Returns an empty list if decisions/ doesn't exist or nothing matches.
    """
    decisions_dir = lore_dir / "decisions"
    if not decisions_dir.exists():
        return []

    file_name = Path(file_path).name
    matches = []
    for yaml_file in sorted(decisions_dir.glob("*.yaml")):
        content = yaml_file.read_text(encoding="utf-8")
        if file_path in content or file_name in content:
            matches.append(content)

    return matches
