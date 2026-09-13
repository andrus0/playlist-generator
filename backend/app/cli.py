"""Management commands: `python -m app.cli --help`."""

import logging

import typer

from .db import SessionLocal, init_db

app = typer.Typer(no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


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
def import_uk(max_weeks: int | None = None, from_start: bool = False) -> None:
    """Crawl the UK Official Singles Chart (incremental; resumes after the last week)."""
    from .importers import uk

    init_db()
    with SessionLocal() as s:
        n = uk.run(s, start=uk.FIRST_CHART if from_start else None, max_weeks=max_weeks)
    typer.echo(f"uk: {n} songs")


@app.command()
def import_wikipedia(region: str, year: int | None = None) -> None:
    """Import number-one singles for AT or DE from Wikipedia (all years, or one year)."""
    from .importers import wikipedia

    init_db()
    with SessionLocal() as s:
        n = wikipedia.run(s, region.upper(), range(year, year + 1) if year else None)
    typer.echo(f"{region}: {n} songs")


@app.command()
def enrich(limit: int | None = None, recheck: bool = False) -> None:
    """Look up artists on MusicBrainz (type, country, genres). Resumable, ~1 artist/s."""
    from .enrich import musicbrainz

    init_db()
    with SessionLocal() as s:
        n = musicbrainz.run(s, limit=limit, only_unchecked=not recheck)
    typer.echo(f"enriched {n} artists")


@app.command()
def stats() -> None:
    """Recompute artist/region statistics (one-hit-wonders etc.)."""
    from .importers.base import compute_artist_stats

    with SessionLocal() as s:
        compute_artist_stats(s)
    typer.echo("ok")


@app.command()
def import_all(enrich_limit: int | None = None, skip_uk: bool = False) -> None:
    """Run every importer (US full, UK incremental, AT/DE current+previous year),
    recompute stats, then enrich new artists on MusicBrainz."""
    from .importers import all as all_importers

    init_db()
    with SessionLocal() as s:
        all_importers.run(s, enrich_limit=enrich_limit, skip_uk=skip_uk)
    typer.echo("ok")


if __name__ == "__main__":
    app()
