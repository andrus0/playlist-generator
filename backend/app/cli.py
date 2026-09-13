"""Management commands: `python -m app.cli --help`."""

import logging

import typer

from .db import SessionLocal, init_db

app = typer.Typer(no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@app.command()
def initdb() -> None:
    """Create tables."""
    init_db()
    typer.echo("ok")


@app.command()
def import_billboard(source: str | None = None) -> None:
    """Import Billboard Hot 100 (URL or local JSON path)."""
    from .importers import billboard

    init_db()
    with SessionLocal() as s:
        n = billboard.run(s, source)
    typer.echo(f"billboard: {n} songs")


@app.command()
def stats() -> None:
    """Recompute artist/region statistics (one-hit-wonders etc.)."""
    from .importers.base import compute_artist_stats

    with SessionLocal() as s:
        compute_artist_stats(s)
    typer.echo("ok")


@app.command()
def import_all() -> None:
    """Run every importer, then recompute stats."""
    from .importers import billboard
    from .importers.base import compute_artist_stats

    init_db()
    with SessionLocal() as s:
        billboard.run(s)
        compute_artist_stats(s)
    typer.echo("ok")


if __name__ == "__main__":
    app()
