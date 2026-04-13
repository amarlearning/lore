import click
import uvicorn


@click.command()
@click.option("--port", default=7340, show_default=True, help="Port to listen on")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
def main(port: int, host: str):
    """lore-daemon — captures Claude Code agent sessions (launched via 'lore start')."""
    click.echo(f"lore-daemon starting on {host}:{port}")
    click.echo("Waiting for Claude Code hook events...\n")
    uvicorn.run(
        "lore_daemon.server:app",
        host=host,
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
