"""Command-line entry points."""

from pathlib import Path

import typer
from rich import print

from .catalog import import_catalog_csv
from .config import get_settings
from .db import initialize
from .discovery import discover_work, load_work
from .export import export_candidates
from .models import Voice
from .youtube import YouTubeAPIError, YouTubeClient

app = typer.Typer(no_args_is_help=True, help="Descubrimiento de audios de YouTube para OSAP.")


@app.command()
def doctor() -> None:
    """Show local configuration without revealing secret values."""
    settings = get_settings()
    print("[bold]ai_recogeYouTube[/bold] · diagnóstico")
    print(f"YouTube API key configured: {'yes' if settings.youtube_api_key else 'no'}")
    print(f"Database path: {settings.db_path}")
    print(f"Max results per query: {settings.max_results}")
    print("Audio analysis extra: install with [cyan]python -m pip install -e '.[audio]'[/cyan]")


@app.command("init-db")
def init_db() -> None:
    """Create the local pilot database."""
    settings = get_settings()
    initialize(settings.db_path)
    print(f"[green]Local database initialized:[/green] {settings.db_path}")


@app.command("import-catalog")
def import_catalog(csv_file: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Import a CSV export of OSAP works into the local database."""
    settings = get_settings()
    initialize(settings.db_path)
    try:
        count = import_catalog_csv(csv_file, settings.db_path)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    print(f"[green]Imported/updated {count} works locally.[/green]")


@app.command("discover-work")
def discover_one(
    work_id: str = typer.Argument(..., help="Exact work_id from the imported OSAP catalog."),
    voice: list[Voice] = typer.Option(
        [Voice.SOPRANO, Voice.ALTO, Voice.TENOR, Voice.BASS],
        "--voice",
        help="Repeat to select voices; defaults to all four SATB voices.",
    ),
    queries_per_voice: int = typer.Option(2, min=1, max=10),
) -> None:
    """Search YouTube for one work; intentionally bounded to control quota."""
    settings = get_settings()
    if not settings.youtube_api_key:
        raise typer.BadParameter("Set YOUTUBE_API_KEY in .env before discovery.")
    initialize(settings.db_path)
    try:
        work = load_work(settings.db_path, work_id)
        stats = discover_work(
            work, voice, YouTubeClient(settings.youtube_api_key), settings.db_path,
            max_results=settings.max_results, max_queries_per_voice=queries_per_voice,
        )
    except (ValueError, YouTubeAPIError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    print(f"[green]Discovery finished for {work.title}[/green]")
    print(stats)
    print("[yellow]Results are candidates only; review before treating a voice as verified.[/yellow]")


@app.command("export-candidates")
def export_candidates_command(
    output: Path = typer.Option(
        Path("data/candidates.csv"), "--output", "-o",
        help="Destination CSV file (Excel-compatible UTF-8).",
    ),
    work_id: str | None = typer.Option(
        None, "--work-id", help="Optional exact work ID to export only one work."
    ),
) -> None:
    """Export discovered videos to a CSV for human review."""
    settings = get_settings()
    try:
        count = export_candidates(settings.db_path, output, work_id)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    print(f"[green]Exported {count} candidates to:[/green] {output}")
    print("[yellow]Voice guesses are search clues, not verified classifications.[/yellow]")


if __name__ == "__main__":
    app()
