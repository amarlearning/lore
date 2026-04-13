import os
import shutil
import tempfile
from pathlib import Path
from git import Repo
import json
import yaml
from typer.testing import CliRunner
from lore_cli.main import app

def test_full_commit_distillation_flow():
    runner = CliRunner()
    
    # Create a temporary directory for the test repo
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        os.chdir(tmp_path)
        
        # 1. Initialize git repo
        repo = Repo.init(tmp_path)
        
        # 2. Initialize lore
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        lore_dir = tmp_path / ".lore"
        assert lore_dir.is_dir()
        
        # 3. Create a fake session in temp/
        session_id = "test-session-123"
        session_path = lore_dir / "temp" / session_id
        session_path.mkdir(parents=True)
        print(f"DEBUG: TEST CREATED session_path={session_path}, exists={session_path.is_dir()}")
        
        # Create a tool event touching app.py
        events_file = session_path / "tool_events.jsonl"
        event = {
            "type": "PostToolUse",
            "timestamp": 123456789.0,
            "data": {
                "tool": "Write",
                "file": "app.py",
                "content": "def main():\n    pass"
            }
        }
        with open(events_file, "w") as f:
            f.write(json.dumps(event) + "\n")
            
        # 4. Make a commit in the repo
        app_file = tmp_path / "app.py"
        app_file.write_text("def main():\n    pass")
        repo.index.add(["app.py"])
        
        # Ensure 'lore' is in PATH for the git hook
        old_path = os.environ.get("PATH", "")
        venv_bin = str(Path(__file__).parent.parent.parent / ".venv" / "bin")
        os.environ["PATH"] = venv_bin + os.pathsep + old_path
        
        try:
            commit = repo.index.commit("Initial commit")
            commit_hash = commit.hexsha
        finally:
            os.environ["PATH"] = old_path
    
        # 5. Verify decision record in staging/ (it should be there because of the git hook)
        # Check active branch
        branch_name = repo.active_branch.name
        staging_dir = lore_dir / "staging" / branch_name
        decision_file = staging_dir / f"{commit_hash}.yaml"
        
        assert decision_file.exists()
        
        # Read and verify YAML content
        with open(decision_file, "r") as f:
            decision = yaml.safe_load(f)
            assert decision["commit_hash"] == commit_hash
            assert "main" in decision["symbols"]
            assert "app.py" in decision["files"]
            
        # 6. Verify temp/ is cleared
        assert not session_path.exists()
        
        # 7. Run lore merge
        result = runner.invoke(app, ["merge"])
        assert result.exit_code == 0
        assert f"Promoted: {commit_hash}.yaml" in result.output
        
        # 8. Verify decision record in decisions/
        decisions_dir = lore_dir / "decisions"
        permanent_file = decisions_dir / f"{commit_hash}.yaml"
        assert permanent_file.exists()
        
        # 9. Verify staging/branch/ is cleared
        assert not staging_dir.exists()
