import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, cast

import typer
import yaml
from lore_core.distill import distill_sessions_to_decision, extract_symbols_from_diff
from lore_core.models import DistillContext
from lore_core.store import (
    find_lore_dir,
    get_changed_files,
    get_commit_info,
    get_git_repo,
    init_lore_dir,
    load_sessions,
)

app = typer.Typer(help="lore — reasoning memory for AI-driven codebases")


@app.command()
def start(
    port: int = typer.Option(7340, help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
):
    """Start the lore-daemon background process."""
    typer.echo(f"Starting lore-daemon on {host}:{port}...")
    try:
        # Try to run lore-daemon from the same environment
        subprocess.run(["lore-daemon", "--port", str(port), "--host", host])
    except FileNotFoundError:
        typer.echo(
            "Error: 'lore-daemon' command not found. Ensure it is installed and in your PATH."
        )
        sys.exit(1)


@app.command()
def stop():
    """Stop the lore-daemon background process."""
    typer.echo("Stopping lore-daemon...")
    # This is a placeholder for now, as the daemon doesn't have a formal stop mechanism yet
    # beyond killing the process.
    subprocess.run(["pkill", "-f", "lore-daemon"])


def _install_git_hooks(cwd: Path):
    """Install post-commit and post-merge git hooks."""
    git_dir = cwd / ".git"
    if not git_dir.is_dir():
        typer.echo("Warning: .git directory not found. Skipping git hooks.")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hooks = {
        "post-commit": "#!/bin/bash\nlore commit\n",
        "post-merge": "#!/bin/bash\nlore merge\n",
    }

    for hook_name, hook_content in hooks.items():
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            content = hook_path.read_text()
            if "lore" in content:
                continue
            hook_content = content + "\n" + hook_content

        hook_path.write_text(hook_content)
        # Make executable
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
        typer.echo(f"Installed git hook: {hook_name}")


def _install_claude_hooks(cwd: Path):
    """Register Claude Code hooks in .claude/settings.json."""
    claude_dir = cwd / ".claude"
    claude_dir.mkdir(exist_ok=True)

    settings_path = claude_dir / "settings.json"
    settings: Dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            pass

    # Basic hook registration as defined in architecture.md
    base_url = "http://localhost:7340/hooks"
    lore_hooks = {
        "UserPromptSubmit": [{"hooks": [{"type": "http", "url": f"{base_url}/prompt"}]}],
        "PostToolUse": [
            {
                "matcher": ".*",
                "hooks": [{"type": "http", "url": f"{base_url}/tool"}],
            }
        ],
        "PreCompact": [{"hooks": [{"type": "http", "url": f"{base_url}/compact"}]}],
        "Stop": [{"hooks": [{"type": "http", "url": f"{base_url}/stop"}]}],
        "PreToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit|Read",
                "hooks": [{"type": "http", "url": f"{base_url}/pre-tool"}],
            }
        ],
    }

    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks_settings = cast(Dict[str, Any], settings["hooks"])

    for event, configs_any in lore_hooks.items():
        configs = cast(List[Dict[str, Any]], configs_any)
        if event not in hooks_settings:
            hooks_settings[event] = configs
        else:
            # Avoid duplicate registrations
            existing_urls = []
            for config_item in cast(List[Dict[str, Any]], hooks_settings.get(event, [])):
                hooks_list = config_item.get("hooks", [])
                if isinstance(hooks_list, list):
                    for hook_item in hooks_list:
                        if isinstance(hook_item, dict):
                            existing_urls.append(hook_item.get("url"))

            for config in configs:
                config_hooks = cast(List[Dict[str, Any]], config.get("hooks", []))
                new_hooks = [
                    h for h in config_hooks if h.get("url") not in existing_urls
                ]
                if new_hooks:
                    config["hooks"] = new_hooks
                    hooks_settings[event].append(config)

    settings_path.write_text(json.dumps(settings, indent=2))
    typer.echo("Registered Claude Code hooks in .claude/settings.json")


@app.command()
def init():
    """Set up .lore/ in the current repo and install git + Claude Code hooks."""
    cwd = Path.cwd()
    lore_dir = init_lore_dir(str(cwd))
    typer.echo(f"Initialized {lore_dir}")

    _install_git_hooks(cwd)
    _install_claude_hooks(cwd)

    typer.echo("\nLore is ready! Make sure 'lore start' is running.")


@app.command()
def commit():
    """Distill temp/ reasoning into staging/ decision records (.yaml)."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))
    if not lore_dir:
        typer.echo("Error: .lore directory not found. Run 'lore init' first.")
        sys.exit(1)

    repo = get_git_repo(str(cwd))
    if not repo:
        typer.echo("Error: Git repository not found.")
        sys.exit(1)

    try:
        commit_hash, diff = get_commit_info(repo)
    except Exception as e:
        typer.echo(f"Error getting commit info: {e}")
        sys.exit(1)

    symbols = extract_symbols_from_diff(diff)
    files = get_changed_files(diff)
    
    if not files:
        typer.echo("No files changed in the latest commit.")
        return

    sessions = load_sessions(lore_dir, files)
    if not sessions:
        typer.echo("No relevant session data found in temp/ for this commit.")
        return

    # In a real implementation, we would pass a real LLM client
    context = DistillContext(
        commit_hash=commit_hash,
        diff=diff,
        symbols=symbols,
        files=files,
        sessions=sessions,
    )

    typer.echo(f"Distilling reasoning for commit {commit_hash[:7]}...")
    decision = distill_sessions_to_decision(context, llm_client=None)

    # Save to staging/
    branch_name = repo.active_branch.name
    staging_dir = lore_dir / "staging" / branch_name
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = staging_dir / f"{commit_hash}.yaml"
    with open(output_path, "w") as f:
        yaml.dump(decision.model_dump(), f)

    typer.echo(f"Distilled decision record saved to: {output_path}")
    
    # Cleanup temp/ (for V1, we clear all matched sessions)
    # Actually, we should only clear the sessions that were distilled.
    for session in sessions:
        session_path = lore_dir / "temp" / session.session_id
        # We can either delete or move it. Let's delete it for now.
        # But for safety, we might want to keep it until merge.
        # For V1, the rule is "temp/ is cleared per commit".
        import shutil
        shutil.rmtree(session_path)
        typer.echo(f"Cleared temp session: {session.session_id}")


@app.command()
def merge():
    """Promote staging/ reasoning into permanent decisions/ (.yaml)."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))
    if not lore_dir:
        typer.echo("Error: .lore directory not found. Run 'lore init' first.")
        sys.exit(1)

    repo = get_git_repo(str(cwd))
    if not repo:
        typer.echo("Error: Git repository not found.")
        sys.exit(1)

    # For V1, we promote from the active branch's staging area
    # In V2, we might want to be more specific about the source branch
    branch_name = repo.active_branch.name
    staging_dir = lore_dir / "staging" / branch_name
    if not staging_dir.is_dir():
        typer.echo(f"No staged decisions found for branch {branch_name}.")
        return

    decisions_dir = lore_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for yaml_file in staging_dir.glob("*.yaml"):
        target_path = decisions_dir / yaml_file.name
        # Move the file
        shutil.move(str(yaml_file), str(target_path))
        typer.echo(f"Promoted: {yaml_file.name}")
        count += 1

    if count > 0:
        typer.echo(f"Successfully promoted {count} decision records to permanent store.")
        # Cleanup the empty branch staging directory
        staging_dir.rmdir()
    else:
        typer.echo("No decisions were ready for promotion.")


@app.command()
def status():
    """Show what's in temp/, staging/, and decisions/."""
    typer.echo("lore status — not yet implemented")
