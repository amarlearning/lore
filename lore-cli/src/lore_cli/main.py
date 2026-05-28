import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
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
    load_agents_constraints,
)

DEFAULT_DAEMON_HOST = "127.0.0.1"
DEFAULT_DAEMON_PORT = 7340
BUILD_INFO_FILENAME = "lore-build-info.json"
BUILD_INFO_HOME_PATH = Path.home() / ".local" / "share" / "lore" / BUILD_INFO_FILENAME

app = typer.Typer(
    help="lore — reasoning memory for AI-driven codebases",
    no_args_is_help=True,
)


def _daemon_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _read_build_info_file(path: Path) -> tuple[str, str] | None:
    """Read build metadata file and return short sha/date if valid."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    short_sha = data.get("short_sha")
    commit_date = data.get("date")
    if isinstance(short_sha, str) and isinstance(commit_date, str):
        return short_sha, commit_date
    return None


def _get_installed_lore_build_info() -> tuple[str, str]:
    """
    Resolve installed lore short commit sha and date from metadata files.
    """
    # Prefer install.sh metadata written next to the binary in ~/.local/bin.
    argv_path = Path(sys.argv[0]).expanduser()
    candidate_paths = [
        argv_path.parent / BUILD_INFO_FILENAME,
        BUILD_INFO_HOME_PATH,
    ]

    for path in candidate_paths:
        build_info = _read_build_info_file(path)
        if build_info is not None:
            return build_info

    return "unknown", "unknown-date"


def _check_daemon(
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    timeout: float = 0.5,
) -> bool:
    """Return whether lore-daemon responds to its health endpoint."""
    try:
        with urllib.request.urlopen(
            f"{_daemon_url(host, port)}/health",
            timeout=timeout,
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


@app.command()
def start(
    port: int = typer.Option(DEFAULT_DAEMON_PORT, help="Port to listen on"),
    host: str = typer.Option(DEFAULT_DAEMON_HOST, help="Host to bind to"),
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
    result = subprocess.run(
        ["pkill", "-f", "lore-daemon"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo("Stopped lore-daemon.")
        return

    if result.returncode == 1:
        typer.echo("lore-daemon was not running.")
        return

    error = result.stderr.strip() or result.stdout.strip() or "unknown error"
    typer.echo(f"Error stopping lore-daemon: {error}")
    sys.exit(result.returncode)


@app.command()
def version():
    """Show installed lore short commit sha and date."""
    short_sha, commit_date = _get_installed_lore_build_info()
    typer.echo(f"lore {short_sha} {commit_date}")


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
                typer.echo(f"Git hook already installed: {hook_name}")
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
        "UserPromptSubmit": [
            {"hooks": [{"type": "http", "url": f"{base_url}/prompt"}]}
        ],
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
    changed = False

    for event, configs_any in lore_hooks.items():
        configs = cast(List[Dict[str, Any]], configs_any)
        if event not in hooks_settings:
            hooks_settings[event] = configs
            changed = True
        else:
            # Avoid duplicate registrations
            existing_urls = []
            for config_item in cast(
                List[Dict[str, Any]], hooks_settings.get(event, [])
            ):
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
                    changed = True

    if changed or not settings_path.exists():
        settings_path.write_text(json.dumps(settings, indent=2))
        typer.echo("Registered Claude Code hooks in .claude/settings.json")
    else:
        typer.echo("Claude Code hooks already registered in .claude/settings.json")


@app.command()
def init():
    """Set up .lore/ in the current repo and install git + Claude Code hooks."""
    cwd = Path.cwd()
    lore_dir_path = cwd / ".lore"
    was_initialized = lore_dir_path.is_dir()
    lore_dir = init_lore_dir(str(cwd))
    if was_initialized:
        typer.echo(f"Initialized: Verified .lore/ at {lore_dir}")
    else:
        typer.echo(f"Initialized: Created .lore/ at {lore_dir}")

    _install_git_hooks(cwd)
    _install_claude_hooks(cwd)

    typer.echo("\nLore is ready.")
    typer.echo("Next: run 'lore start' in a separate terminal.")


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
    constraints = load_agents_constraints(str(cwd))

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

    # Merge constraints from AGENTS.md with distilled constraints
    if constraints:
        decision.constraints = list(set(decision.constraints + constraints))

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
        typer.echo(
            f"Successfully promoted {count} decision records to permanent store."
        )
        # Cleanup the empty branch staging directory
        staging_dir.rmdir()
    else:
        typer.echo("No decisions were ready for promotion.")


@app.command()
def status(
    port: int = typer.Option(DEFAULT_DAEMON_PORT, help="Daemon port to check"),
    host: str = typer.Option(DEFAULT_DAEMON_HOST, help="Daemon host to check"),
):
    """Show daemon health and what's in temp/, staging/, and decisions/."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))

    daemon_running = _check_daemon(host=host, port=port)

    typer.echo("Lore Status:")
    typer.echo("-----------")
    if daemon_running:
        typer.echo(f"Daemon: running at {_daemon_url(host, port)}")
    else:
        typer.echo(f"Daemon: not running at {_daemon_url(host, port)}")
        typer.echo("        Start it with 'lore start'.")

    if not lore_dir:
        typer.echo("Project: not initialized (.lore directory not found)")
        typer.echo("         Run 'lore init' from your repository root.")
        return

    temp_dir = lore_dir / "temp"
    staging_dir = lore_dir / "staging"
    decisions_dir = lore_dir / "decisions"

    temp_sessions = list(temp_dir.iterdir()) if temp_dir.exists() else []
    temp_count = len([d for d in temp_sessions if d.is_dir()])

    staging_branches = list(staging_dir.iterdir()) if staging_dir.exists() else []
    staging_branch_count = len([d for d in staging_branches if d.is_dir()])
    staging_decision_count = 0
    for branch_dir in staging_branches:
        if branch_dir.is_dir():
            staging_decision_count += len(list(branch_dir.glob("*.yaml")))

    decision_files = (
        list(decisions_dir.glob("*.yaml")) if decisions_dir.exists() else []
    )
    decision_count = len(decision_files)

    typer.echo(f"Project: initialized at {lore_dir}")
    typer.echo(f"temp/: {temp_count} session{'s' if temp_count != 1 else ''}")
    typer.echo(
        f"staging/: {staging_branch_count} branch{'es' if staging_branch_count != 1 else ''}, {staging_decision_count} decision{'s' if staging_decision_count != 1 else ''}"
    )
    typer.echo(
        f"decisions/: {decision_count} decision{'s' if decision_count != 1 else ''}"
    )


@app.command()
def log():
    """Show history of decision records in decisions/."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))
    if not lore_dir:
        typer.echo("Error: .lore directory not found. Run 'lore init' first.")
        sys.exit(1)

    decisions_dir = lore_dir / "decisions"
    if not decisions_dir.exists():
        typer.echo("No decision records found.")
        return

    decision_files = sorted(decisions_dir.glob("*.yaml"), reverse=True)

    if not decision_files:
        typer.echo("No decision records found.")
        return

    for yaml_file in decision_files:
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)

            commit_hash = data.get("commit_hash", "")
            summary = data.get("summary", "No summary")
            files = data.get("files", [])

            short_hash = commit_hash[:7] if commit_hash else "--------"
            file_list = ", ".join(files[:2])
            if len(files) > 2:
                file_list += f", +{len(files) - 2} more"

            typer.echo(f"{short_hash} — {summary}")
            if file_list:
                typer.echo(f"  {file_list}")
        except Exception:
            pass


@app.command()
def show(commit_hash: str):
    """Show a specific decision record by commit hash (supports short hashes)."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))
    if not lore_dir:
        typer.echo("Error: .lore directory not found. Run 'lore init' first.")
        sys.exit(1)

    decisions_dir = lore_dir / "decisions"
    if not decisions_dir.exists():
        typer.echo(f"No decision record found for hash '{commit_hash}'.")
        sys.exit(1)

    matching_files = []
    for file_path in decisions_dir.glob("*.yaml"):
        if file_path.stem.startswith(commit_hash):
            matching_files.append(file_path)

    if len(matching_files) == 0:
        typer.echo(f"No decision record found for hash '{commit_hash}'.")
        sys.exit(1)
    elif len(matching_files) > 1:
        typer.echo(f"Multiple decision records found matching '{commit_hash}':")
        for match_file in matching_files:
            typer.echo(f"  - {match_file.stem}")
        sys.exit(1)

    decision_file = matching_files[0]
    with open(str(decision_file), "r") as fp:
        data = yaml.safe_load(fp)

    typer.echo(f"Commit: {data.get('commit_hash', 'N/A')}")
    typer.echo(f"Summary: {data.get('summary', 'N/A')}")
    typer.echo()
    typer.echo("Why:")
    typer.echo(f"  {data.get('why', 'N/A')}")
    typer.echo()

    alternatives = data.get("alternatives_rejected", [])
    if alternatives:
        typer.echo("Alternatives Rejected:")
        for alt in alternatives:
            typer.echo(f"  - {alt}")
        typer.echo()

    constraints = data.get("constraints", [])
    if constraints:
        typer.echo("Constraints:")
        for constraint in constraints:
            typer.echo(f"  - {constraint}")
        typer.echo()

    symbols = data.get("symbols", [])
    if symbols:
        typer.echo("Symbols:")
        for symbol in symbols:
            typer.echo(f"  - {symbol}")
        typer.echo()

    files = data.get("files", [])
    if files:
        typer.echo("Files:")
        for file in files:
            typer.echo(f"  - {file}")


@app.command()
def query(q: str):
    """Search decision records by keywords (future: semantic search)."""
    cwd = Path.cwd()
    lore_dir = find_lore_dir(str(cwd))
    if not lore_dir:
        typer.echo("Error: .lore directory not found. Run 'lore init' first.")
        sys.exit(1)

    decisions_dir = lore_dir / "decisions"
    if not decisions_dir.exists():
        typer.echo("No decision records found.")
        return

    decision_files = list(decisions_dir.glob("*.yaml"))
    if not decision_files:
        typer.echo("No decision records found.")
        return

    query_lower = q.lower()
    matches = []

    for file_path in decision_files:
        try:
            with open(str(file_path), "r") as f:
                data = yaml.safe_load(f)

            summary = data.get("summary", "").lower()
            why = data.get("why", "").lower()
            files_list = " ".join(data.get("files", [])).lower()
            symbols_list = " ".join(data.get("symbols", [])).lower()

            if (
                query_lower in summary
                or query_lower in why
                or query_lower in files_list
                or query_lower in symbols_list
            ):
                matches.append((file_path, data))
        except Exception:
            pass

    if not matches:
        typer.echo(f"No decision records found matching '{q}'.")
        return

    typer.echo(
        f"Found {len(matches)} matching decision record{'' if len(matches) == 1 else 's'}:"
    )
    typer.echo()

    for file_path, data in matches:
        commit_hash = data.get("commit_hash", "")
        summary = data.get("summary", "No summary")
        files_list = data.get("files", [])

        short_hash = commit_hash[:7] if commit_hash else "--------"
        file_list = ", ".join(files_list[:2])
        if len(files_list) > 2:
            file_list += f", +{len(files_list) - 2} more"

        typer.echo(f"{short_hash} — {summary}")
        if file_list:
            typer.echo(f"  {file_list}")
        typer.echo()


@app.command()
def constraints():
    """Show architectural constraints from AGENTS.md."""
    cwd = Path.cwd()
    constraints = load_agents_constraints(str(cwd))

    if not constraints:
        typer.echo(
            "No AGENTS.md file found with Key Architectural Constraints section."
        )
        return

    typer.echo("Lore Architectural Constraints:")
    typer.echo("-------------------------------")
    for constraint in constraints:
        typer.echo(f"  {constraint}")


if __name__ == "__main__":
    app()
