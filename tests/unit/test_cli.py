import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from lore_cli.main import app
from lore_core.models import SessionData, DecisionRecord

runner = CliRunner()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir).resolve()


def test_init_command(tmp_dir):
    os.chdir(tmp_dir)
    # Create a fake .git dir
    (tmp_dir / ".git").mkdir()

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initialized" in result.output
    assert (tmp_dir / ".lore").is_dir()
    assert (tmp_dir / ".git/hooks/post-commit").exists()
    assert (tmp_dir / ".claude/settings.json").exists()


@patch("subprocess.run")
def test_stop_command(mock_run):
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0
    assert "Stopping lore-daemon" in result.output
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_start_command(mock_run):
    result = runner.invoke(app, ["start", "--port", "8000"])
    assert result.exit_code == 0
    assert "Starting lore-daemon on 127.0.0.1:8000" in result.output
    mock_run.assert_called_once()


def test_init_command_no_git(tmp_dir):
    os.chdir(tmp_dir)
    # No .git dir
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Warning: .git directory not found" in result.output


def test_commit_command_no_lore(tmp_dir):
    os.chdir(tmp_dir)
    # No .lore dir
    result = runner.invoke(app, ["commit"])
    assert result.exit_code != 0
    assert "Error: .lore directory not found" in result.output


@patch("lore_cli.main.find_lore_dir")
@patch("lore_cli.main.get_git_repo")
@patch("lore_cli.main.get_commit_info")
@patch("lore_cli.main.get_changed_files")
@patch("lore_cli.main.load_sessions")
@patch("lore_cli.main.distill_sessions_to_decision")
def test_commit_command(
    mock_distill, mock_load, mock_changed, mock_info, mock_repo, mock_find, tmp_dir
):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    mock_find.return_value = lore_dir

    mock_repo_obj = MagicMock()
    mock_repo_obj.active_branch.name = "main"
    mock_repo.return_value = mock_repo_obj

    mock_info.return_value = ("abc123hash", "fake diff")
    mock_changed.return_value = ["app.py"]

    # Use real SessionData instead of MagicMock to satisfy Pydantic
    mock_load.return_value = [SessionData(session_id="sess-1")]

    # Use real DecisionRecord
    mock_distill.return_value = DecisionRecord(
        commit_hash="abc123hash",
        summary="summary",
        why="why",
        alternatives_rejected=[],
        constraints=[],
        symbols=[],
        files=["app.py"],
    )

    with patch("shutil.rmtree") as mock_rm:
        result = runner.invoke(app, ["commit"])
        assert result.exit_code == 0
        assert "Distilling reasoning" in result.output
        assert (lore_dir / "staging/main/abc123hash.yaml").exists()
        mock_rm.assert_called_once()


@patch("lore_cli.main.find_lore_dir")
@patch("lore_cli.main.get_git_repo")
def test_merge_command(mock_repo, mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    mock_find.return_value = lore_dir

    staging_dir = lore_dir / "staging/main"
    staging_dir.mkdir(parents=True)
    (staging_dir / "abc123hash.yaml").write_text("content")

    mock_repo_obj = MagicMock()
    mock_repo_obj.active_branch.name = "main"
    mock_repo.return_value = mock_repo_obj

    result = runner.invoke(app, ["merge"])
    assert result.exit_code == 0
    assert "Promoted: abc123hash.yaml" in result.output
    assert (lore_dir / "decisions/abc123hash.yaml").exists()
    assert not staging_dir.exists()
