import pytest
import os
import json
import tempfile
from pathlib import Path
from lore_core.store import (
    find_lore_dir,
    init_lore_dir,
    session_temp_dir,
    get_git_repo,
    get_commit_info,
    get_changed_files,
    load_sessions,
)
from git import Repo


@pytest.fixture(autouse=True)
def ensure_valid_cwd(tmp_path_factory):
    """Ensure the process always has a valid CWD before each test."""
    try:
        old_cwd = os.getcwd()
    except FileNotFoundError:
        old_cwd = str(Path.home())

    tmp_dir = tmp_path_factory.mktemp("cwd_fix")
    os.chdir(tmp_dir)
    yield
    try:
        os.chdir(old_cwd)
    except FileNotFoundError:
        pass


@pytest.fixture
def tmp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        yield tmp_path


def test_get_git_repo(tmp_repo):
    Repo.init(tmp_repo)
    assert get_git_repo(str(tmp_repo)) is not None
    assert get_git_repo("/non/existent/path") is None


def test_get_commit_info(tmp_repo, monkeypatch):
    repo = Repo.init(tmp_repo)
    monkeypatch.chdir(tmp_repo)

    file1 = tmp_repo / "file1.txt"
    file1.write_text("content")
    repo.index.add(["file1.txt"])
    commit1 = repo.index.commit("Initial commit")

    hash1, diff1 = get_commit_info(repo)
    assert hash1 == commit1.hexsha
    assert "file1.txt" in diff1

    # Second commit
    file2 = tmp_repo / "file2.txt"
    file2.write_text("content2")
    repo.index.add(["file2.txt"])
    commit2 = repo.index.commit("Second commit")

    hash2, diff2 = get_commit_info(repo)
    assert hash2 == commit2.hexsha
    assert "file2.txt" in diff2
    assert "file1.txt" not in diff2


def test_find_lore_dir(tmp_repo):
    # Test upward search
    project_dir = tmp_repo / "project"
    sub_dir = project_dir / "src" / "module"
    sub_dir.mkdir(parents=True)

    lore_dir = project_dir / ".lore"
    lore_dir.mkdir()

    assert find_lore_dir(str(sub_dir)) == lore_dir
    assert find_lore_dir(str(tmp_repo)) is None


def test_init_lore_dir(tmp_repo):
    lore_dir = init_lore_dir(str(tmp_repo))
    assert lore_dir.is_dir()
    assert (lore_dir / "temp").is_dir()
    assert (lore_dir / "staging").is_dir()
    assert (lore_dir / "decisions").is_dir()


def test_session_temp_dir(tmp_repo):
    lore_dir = tmp_repo / ".lore"
    session_id = "test-session"
    s_dir = session_temp_dir(lore_dir, session_id)
    assert s_dir == lore_dir / "temp" / session_id
    assert s_dir.is_dir()


def test_get_changed_files():
    diff = """--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,2 @@
+new line
--- a/dir/file2.py
+++ b/dir/file2.py
"""
    # Note: our current implementation looks for +++ b/
    diff = """diff --git a/file1.py b/file1.py
index 123..456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,2 @@
+new line
diff --git a/dir/file2.py b/dir/file2.py
--- a/dir/file2.py
+++ b/dir/file2.py
"""
    files = get_changed_files(diff)
    assert "file1.py" in files
    assert "dir/file2.py" in files


def test_load_sessions(tmp_repo):
    lore_dir = tmp_repo / ".lore"
    lore_dir.mkdir()
    temp_dir = lore_dir / "temp"
    temp_dir.mkdir()

    session_id = "session-1"
    s_dir = temp_dir / session_id
    s_dir.mkdir()

    # Create tool events
    events_file = s_dir / "tool_events.jsonl"
    event = {"type": "PostToolUse", "timestamp": 100.0, "data": {"file": "app.py"}}
    with open(events_file, "w") as f:
        f.write(json.dumps(event) + "\n")

    # Create prompt
    prompt_file = s_dir / "prompt.json"
    prompt_file.write_text(json.dumps({"prompt": "hello"}))

    # Load sessions
    sessions = load_sessions(lore_dir, ["app.py"])
    assert len(sessions) == 1
    assert sessions[0].session_id == session_id
    assert sessions[0].prompt == "hello"
    assert len(sessions[0].events) == 1

    # Test filtering
    sessions = load_sessions(lore_dir, ["other.py"])
    assert len(sessions) == 0
