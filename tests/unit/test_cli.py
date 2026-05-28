import pytest
import os
import tempfile
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from lore_cli.main import app
from lore_core.models import SessionData, DecisionRecord

runner = CliRunner()


def test_module_help_outputs_commands(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["python -m lore_cli.main", "--help"])

    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("lore_cli.main", run_name="__main__")

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "Usage:" in output
    assert "Commands" in output
    assert "status" in output


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
    assert "Created .lore/" in result.output
    assert "Installed git hook: post-commit" in result.output
    assert "Registered Claude Code hooks" in result.output


def test_init_command_second_run_reports_unchanged(tmp_dir):
    os.chdir(tmp_dir)
    (tmp_dir / ".git").mkdir()

    first_result = runner.invoke(app, ["init"])
    assert first_result.exit_code == 0

    second_result = runner.invoke(app, ["init"])
    assert second_result.exit_code == 0
    assert "Verified .lore/" in second_result.output
    assert "Git hook already installed: post-commit" in second_result.output
    assert "Claude Code hooks already registered" in second_result.output


@patch("subprocess.run")
def test_stop_command(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["pkill", "-f", "lore-daemon"], returncode=0
    )
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0
    assert "Stopping lore-daemon" in result.output
    assert "Stopped lore-daemon" in result.output
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_stop_command_when_daemon_not_running(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["pkill", "-f", "lore-daemon"], returncode=1
    )
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0
    assert "lore-daemon was not running" in result.output


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


def test_status_command_no_lore(tmp_dir):
    os.chdir(tmp_dir)
    with patch("lore_cli.main._check_daemon") as mock_check:
        mock_check.return_value = False
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Daemon: not running" in result.output
    assert "Project: not initialized" in result.output
    assert "Run 'lore init'" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_status_command_empty(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    (lore_dir / "temp").mkdir()
    (lore_dir / "staging").mkdir()
    (lore_dir / "decisions").mkdir()
    mock_find.return_value = lore_dir

    with patch("lore_cli.main._check_daemon") as mock_check:
        mock_check.return_value = True
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Daemon: running" in result.output
    assert "temp/" in result.output
    assert "staging/" in result.output
    assert "decisions/" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_status_command_with_data(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    (lore_dir / "temp/sess-1").mkdir(parents=True)
    (lore_dir / "temp/sess-2").mkdir(parents=True)
    (lore_dir / "staging/main").mkdir(parents=True)
    (lore_dir / "staging/main/commit1.yaml").write_text("content")
    (lore_dir / "staging/feature").mkdir(parents=True)
    (lore_dir / "staging/feature/commit2.yaml").write_text("content")
    (lore_dir / "decisions").mkdir()
    (lore_dir / "decisions/old1.yaml").write_text("content")
    (lore_dir / "decisions/old2.yaml").write_text("content")
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "temp/: 2 sessions" in result.output
    assert "staging/: 2 branches, 2 decisions" in result.output
    assert "decisions/: 2 decisions" in result.output


def test_log_command_no_lore(tmp_dir):
    os.chdir(tmp_dir)
    result = runner.invoke(app, ["log"])
    assert result.exit_code != 0
    assert "Error: .lore directory not found" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_log_command_empty(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    (lore_dir / "decisions").mkdir()
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
    assert "No decision records found" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_log_command_with_data(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    decisions_dir = lore_dir / "decisions"
    decisions_dir.mkdir()

    # Create two YAML decision files
    decision1 = """commit_hash: abc123abc123abc123abc123abc123abc123abc123
summary: Add status command
why: Users need to see what's in the reasoning tiers
files:
  - lore-cli/src/lore_cli/main.py
"""
    (decisions_dir / "abc123abc123abc123abc123abc123abc123abc123.yaml").write_text(
        decision1
    )

    decision2 = """commit_hash: def456def456def456def456def456def456def456
summary: Fix CI pipeline
why: Tests were failing due to missing dependencies
files:
  - .github/workflows/ci.yml
  - pyproject.toml
"""
    (decisions_dir / "def456def456def456def456def456def456def456.yaml").write_text(
        decision2
    )

    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
    assert "abc123a" in result.output
    assert "Add status command" in result.output
    assert "def456d" in result.output
    assert "Fix CI pipeline" in result.output


def test_show_command_no_lore(tmp_dir):
    os.chdir(tmp_dir)
    result = runner.invoke(app, ["show", "abc123"])
    assert result.exit_code != 0
    assert "Error: .lore directory not found" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_show_command_no_hash(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    (lore_dir / "decisions").mkdir()
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["show", "abc123"])
    assert result.exit_code != 0
    assert "No decision record found for hash" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_show_command_with_full_hash(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    decisions_dir = lore_dir / "decisions"
    decisions_dir.mkdir()

    full_hash = "abc123abc123abc123abc123abc123abc123abc123"
    decision = f"""commit_hash: {full_hash}
summary: Add status command
why: Users need to see what's in the reasoning tiers
alternatives_rejected:
  - Using JSON instead of YAML
constraints:
  - Follow Clean Code principles
symbols:
  - status
files:
  - lore-cli/src/lore_cli/main.py
"""
    (decisions_dir / f"{full_hash}.yaml").write_text(decision)
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["show", full_hash])
    assert result.exit_code == 0
    assert "Add status command" in result.output
    assert "Users need to see" in result.output
    assert "Using JSON instead of YAML" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_show_command_with_short_hash(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    decisions_dir = lore_dir / "decisions"
    decisions_dir.mkdir()

    full_hash = "def456def456def456def456def456def456def456"
    decision = f"""commit_hash: {full_hash}
summary: Fix CI pipeline
why: Tests were failing due to missing dependencies
alternatives_rejected: []
constraints: []
symbols: []
files:
  - .github/workflows/ci.yml
"""
    (decisions_dir / f"{full_hash}.yaml").write_text(decision)
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["show", "def456"])
    assert result.exit_code == 0
    assert "Fix CI pipeline" in result.output


def test_query_command_no_lore(tmp_dir):
    os.chdir(tmp_dir)
    result = runner.invoke(app, ["query", "status command"])
    assert result.exit_code != 0
    assert "Error: .lore directory not found" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_query_command_empty(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    (lore_dir / "decisions").mkdir()
    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["query", "anything"])
    assert result.exit_code == 0
    assert "No decision records found" in result.output


@patch("lore_cli.main.find_lore_dir")
def test_query_command_simple(mock_find, tmp_dir):
    os.chdir(tmp_dir)
    lore_dir = tmp_dir / ".lore"
    lore_dir.mkdir()
    decisions_dir = lore_dir / "decisions"
    decisions_dir.mkdir()

    decision1 = """commit_hash: abc123abc123abc123abc123abc123abc123abc123
summary: Add status command
why: Users need to see what's in the reasoning tiers
files:
  - lore-cli/src/lore_cli/main.py
"""
    (decisions_dir / "abc123abc123abc123abc123abc123abc123abc123.yaml").write_text(
        decision1
    )

    decision2 = """commit_hash: def456def456def456def456def456def456def456
summary: Fix CI pipeline
why: Tests were failing due to missing dependencies
files:
  - .github/workflows/ci.yml
"""
    (decisions_dir / "def456def456def456def456def456def456def456.yaml").write_text(
        decision2
    )

    mock_find.return_value = lore_dir

    result = runner.invoke(app, ["query", "status"])
    assert result.exit_code == 0
    assert "abc123a" in result.output
    assert "Add status command" in result.output
    assert "def456d" not in result.output or "Fix CI pipeline" not in result.output
