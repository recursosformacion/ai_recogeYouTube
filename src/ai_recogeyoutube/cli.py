"""Command-line entry points."""

import typer
from rich import print

from .config import get_settings
from .db import initialize

app = typer.Typer(no_args_is_help=True, help="Descubrimiento de audios de YouTube para OSAP.")


@app.command()
def doctor() -> None:
    """Show local configuration without revealing secret values."""
    settings = get_settings()
    print("[bold]ai_recogeYouTube[/bold] · diagnóstico")
    print(f"YouTube API key configured: {'yes' if settings.youtube_api_key else 'no'}")
    print(f"Database path: {settings.db_path}")
    print(f"Max results per query: {settings.max_results}")
    print("Audio analysis extra: install with [cyan]pip install -e '.[audio]'[/cyan]")


@app.command("init-db")
def init_db() -> None:
    """Create the local pilot database."""
    settings = get_settings()
    initialize(settings.db_path)
    print(f"[green]Local database initialized:[/green] {settings.db_path}")


if __name__ == "__main__":
    app()
