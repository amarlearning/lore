import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import typer
from lore_core.store import init_lore_dir

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
    settings = {}
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

    for event, configs in lore_hooks.items():
        if event not in settings["hooks"]:
            settings["hooks"][event] = configs
        else:
            # Avoid duplicate registrations
            existing_urls = [
                h.get("url")
                for c in settings["hooks"][event]
                for h in c.get("hooks", [])
            ]
            for config in configs:
                new_hooks = [
                    h for h in config["hooks"] if h.get("url") not in existing_urls
                ]
                if new_hooks:
                    config["hooks"] = new_hooks
                    settings["hooks"][event].append(config)

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
    typer.echo("lore commit — not yet implemented")


@app.command()
def merge():
    """Promote staging/ reasoning into permanent decisions/ (.yaml)."""
    typer.echo("lore merge — not yet implemented")


@app.command()
def status():
    """Show what's in temp/, staging/, and decisions/."""
    typer.echo("lore status — not yet implemented")
