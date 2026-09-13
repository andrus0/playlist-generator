"""Shared import machinery: aggregated chart entries → songs/artists/song_charts."""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from ..models import Artist, ArtistRegionStats, ImportRun, Song, SongChart
from ..normalize import artist_key, credit_key, normalize, primary_artist

log = logging.getLogger(__name__)


@dataclass
class ChartEntry:
    """One song's aggregated run on one chart."""

    title: str
    artist: str  # full credit as printed
    peak_position: int
    weeks_on_chart: int
    first_date: date
    last_date: date


def song_key(title: str, credit: str) -> tuple[str, str]:
    return normalize(title), credit_key(credit)


def aggregate_weeks(rows) -> dict[tuple[str, str], ChartEntry]:
    """Fold week-by-week rows (title, artist, position, date) into one ChartEntry per song."""
    agg: dict[tuple[str, str], ChartEntry] = {}
    weeks: dict[tuple[str, str], int] = {}
    for title, artist, position, week in rows:
        key = song_key(title, artist)
        if not key[0] or not key[1]:
            continue
        e = agg.get(key)
        if e is None:
            agg[key] = ChartEntry(title.strip(), artist.strip(), position, 0, week, week)
            weeks[key] = 1
        else:
            e.peak_position = min(e.peak_position, position)
            e.first_date = min(e.first_date, week)
            e.last_date = max(e.last_date, week)
            weeks[key] += 1
    for key, e in agg.items():
        e.weeks_on_chart = weeks[key]
    return agg


def dedupe(entries: list[ChartEntry]) -> list[ChartEntry]:
    """Merge entries that normalise to the same song (spelling variants of title/credit)."""
    merged: dict[tuple[str, str], ChartEntry] = {}
    for e in entries:
        key = song_key(e.title, e.artist)
        m = merged.get(key)
        if m is None:
            merged[key] = ChartEntry(**vars(e))
        else:
            m.peak_position = min(m.peak_position, e.peak_position)
            m.weeks_on_chart = max(m.weeks_on_chart, e.weeks_on_chart)
            m.first_date = min(m.first_date, e.first_date)
            m.last_date = max(m.last_date, e.last_date)
    return list(merged.values())


def _get_or_create_artists(session: Session, names: set[str]) -> dict[str, int]:
    """Map artist_key → artists.id, creating missing rows."""
    keys = {artist_key(n): n for n in names}
    existing = dict(
        session.execute(select(Artist.name_norm, Artist.id).where(Artist.name_norm.in_(keys))).all()
    )
    missing = [Artist(name=name, name_norm=k) for k, name in keys.items() if k not in existing]
    if missing:
        session.add_all(missing)
        session.flush()
        existing.update({a.name_norm: a.id for a in missing})
    return existing


def upsert_entries(
    session: Session, region: str, entries: list[ChartEntry], *, merge: bool = False
) -> int:
    """Insert/update songs and their chart run for one region. Returns number of songs touched.

    merge=False: the entries are the complete dataset → chart rows are replaced.
    merge=True: incremental batch → peak=min, weeks=max, first=min, last=max.
    """
    entries = dedupe(entries)
    if not entries:
        return 0
    artists = _get_or_create_artists(session, {primary_artist(e.artist) for e in entries})

    existing_songs = {
        (t, a): (sid, y)
        for sid, t, a, y in session.execute(
            select(Song.id, Song.title_norm, Song.artist_display_norm, Song.year)
        ).all()
    }
    existing_charts = {
        row.song_id: row
        for row in session.execute(
            select(
                SongChart.id,
                SongChart.song_id,
                SongChart.peak_position,
                SongChart.weeks_on_chart,
                SongChart.first_date,
                SongChart.last_date,
            ).where(SongChart.region == region)
        ).all()
    }

    new_songs: list[Song] = []
    pending: list[tuple[tuple[str, str], ChartEntry]] = []
    for e in entries:
        key = song_key(e.title, e.artist)
        if key in existing_songs:
            sid, year = existing_songs[key]
            if e.first_date.year < year:
                session.execute(
                    Song.__table__.update().where(Song.id == sid).values(year=e.first_date.year)
                )
        else:
            song = Song(
                title=e.title,
                title_norm=key[0],
                artist_display=e.artist,
                artist_display_norm=key[1],
                artist_id=artists[artist_key(primary_artist(e.artist))],
                year=e.first_date.year,
            )
            new_songs.append(song)
            existing_songs[key] = (None, e.first_date.year)  # placeholder until flush
        pending.append((key, e))

    if new_songs:
        session.add_all(new_songs)
        session.flush()
        for s in new_songs:
            existing_songs[(s.title_norm, s.artist_display_norm)] = (s.id, s.year)

    charts_new: list[dict] = []
    for key, e in pending:
        sid = existing_songs[key][0]
        values = dict(
            peak_position=e.peak_position,
            weeks_on_chart=e.weeks_on_chart,
            first_date=e.first_date,
            last_date=e.last_date,
        )
        if sid in existing_charts:
            old = existing_charts[sid]
            if merge:
                values = dict(
                    peak_position=min(old.peak_position, e.peak_position),
                    weeks_on_chart=max(old.weeks_on_chart, e.weeks_on_chart),
                    first_date=min(old.first_date, e.first_date),
                    last_date=max(old.last_date, e.last_date),
                )
            session.execute(
                SongChart.__table__.update().where(SongChart.id == old.id).values(**values)
            )
        else:
            charts_new.append(dict(song_id=sid, region=region, **values))
    if charts_new:
        session.execute(SongChart.__table__.insert(), charts_new)

    session.add(
        ImportRun(
            source=region,
            finished_at=date.today(),
            latest_chart_date=max(e.last_date for e in entries) if entries else None,
            songs=len(entries),
        )
    )
    session.commit()
    log.info("%s: %d entries (%d new songs)", region, len(entries), len(new_songs))
    return len(entries)


def compute_artist_stats(session: Session) -> None:
    """Rebuild artist_region_stats from song_charts. Drives the one-hit-wonder filter."""
    session.execute(delete(ArtistRegionStats))
    rows = session.execute(
        select(
            Song.artist_id,
            SongChart.region,
            func.count(),
            func.sum(case((SongChart.peak_position <= 40, 1), else_=0)),
            func.sum(case((SongChart.peak_position <= 10, 1), else_=0)),
            func.sum(case((SongChart.peak_position == 1, 1), else_=0)),
        )
        .join(SongChart, SongChart.song_id == Song.id)
        .group_by(Song.artist_id, SongChart.region)
    ).all()
    session.execute(
        ArtistRegionStats.__table__.insert(),
        [
            dict(
                artist_id=a,
                region=r,
                songs_total=int(total),
                songs_top40=int(t40 or 0),
                songs_top10=int(t10 or 0),
                number_ones=int(n1 or 0),
            )
            for a, r, total, t40, t10, n1 in rows
        ],
    )
    session.commit()
    log.info("artist stats: %d rows", len(rows))
