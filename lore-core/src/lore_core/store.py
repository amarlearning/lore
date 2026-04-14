"""
Utilities for finding and writing to the .lore/ directory.
The .lore/ dir is found by walking up from a given path — same mechanism git uses for .git/.
"""

import json
from pathlib import Path
from typing import List, Optional
from git import Repo
from .models import SessionData, SessionEvent


def find_lore_dir(cwd: str) -> Optional[Path]:
    """Search upwards from cwd to find a .lore directory."""
    current = Path(cwd).resolve()
    for parent in [current] + list(current.parents):
        lore_dir = parent / ".lore"
        if lore_dir.is_dir():
            return lore_dir
    return None


def init_lore_dir(cwd: str) -> Path:
    """Create the .lore directory structure in the current directory."""
    lore_dir = Path(cwd).resolve() / ".lore"
    for sub in ["temp", "staging", "decisions"]:
        (lore_dir / sub).mkdir(parents=True, exist_ok=True)
    return lore_dir


def session_temp_dir(lore_dir: Path, session_id: str) -> Path:
    """Get the path to a session's temp directory."""
    temp_dir = lore_dir / "temp" / session_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_git_repo(cwd: str) -> Optional[Repo]:
    """Find and return the git repo for the given directory."""
    try:
        return Repo(cwd, search_parent_directories=True)
    except Exception:
        return None


def get_commit_info(repo: Repo):
    """Return the current commit hash and the diff between HEAD and HEAD~1."""
    commit = repo.head.commit
    if len(commit.parents) == 0:
        # First commit
        diff = repo.git.diff("4b825dc642cb6eb9a060e54bf8d69288fbee4904", commit.hexsha)
    else:
        diff = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)

    return commit.hexsha, diff


def get_changed_files(diff: str) -> List[str]:
    """Extract list of changed files from a git diff."""
    # A pragmatic regex approach to extract filenames from git diff output
    # git diff format usually includes lines like '--- a/path/to/file' and '+++ b/path/to/file'
    files = set()
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.add(line[6:])
    return list(files)


def load_sessions(lore_dir: Path, changed_files: List[str]) -> List[SessionData]:
    """Load session data from temp directory for sessions that touched changed_files."""
    sessions: List[SessionData] = []
    temp_dir = lore_dir / "temp"
    if not temp_dir.is_dir():
        return sessions

    for session_path in temp_dir.iterdir():
        if not session_path.is_dir():
            continue

        events_file = session_path / "tool_events.jsonl"
        if not events_file.exists():
            continue

        # Check if this session touched any of the changed_files
        touched = False
        events = []
        with open(events_file, "r") as f:
            for line in f:
                try:
                    event_data = json.loads(line)
                    # For V1, we assume 'PostToolUse' events have a 'file' or similar field
                    # Or we just check all files in the session if it's simpler
                    # Let's check for any mention of the changed_files in the event data
                    event_str = json.dumps(event_data)
                    for f_name in changed_files:
                        if f_name in event_str:
                            touched = True

                    events.append(
                        SessionEvent(
                            type=event_data.get("type", "unknown"),
                            timestamp=event_data.get("timestamp", 0.0),
                            data=event_data,
                        )
                    )
                except json.JSONDecodeError:
                    continue

        if touched:
            prompt_file = session_path / "prompt.json"
            prompt = None
            if prompt_file.exists():
                try:
                    prompt_data = json.loads(prompt_file.read_text())
                    prompt = prompt_data.get("prompt")
                except json.JSONDecodeError:
                    pass

            compact_file = session_path / "compact.json"
            compact_reasoning = None
            if compact_file.exists():
                try:
                    compact_data = json.loads(compact_file.read_text())
                    compact_reasoning = compact_data.get("reasoning")
                except json.JSONDecodeError:
                    pass

            sessions.append(
                SessionData(
                    session_id=session_path.name,
                    prompt=prompt,
                    events=events,
                    compact_reasoning=compact_reasoning,
                )
            )

    return sessions


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
