"""Turn a PlaylistQuery into a list of tracks.

Strategy: build one SQL query for the candidate set (all filters except
diversity), fetch it, then apply ordering / seeded shuffle / max-per-artist in
Python. Candidate sets are at most a few ten-thousand rows, so this is cheap
and keeps the random ordering reproducible across SQLite and Postgres.
"""

import random
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Artist, ArtistGenre, ArtistRegionStats, Genre, Song, SongChart, SongGenre
from ..normalize import artist_key
from ..schemas import ArtistTypeFilter, OneHitWonder, PlaylistQuery, Sort

ALL_REGIONS = ["US", "UK", "AT", "DE"]
# Regions with complete weekly charts. AT/DE only carry number-one hits, which is
# not enough to decide whether an artist is a one-hit wonder.
FULL_CHART_REGIONS = ["US", "UK"]


@dataclass
class Track:
    song: Song
    best_peak: int
    total_weeks: int


def _decade_bounds(decades: list[str]) -> list[tuple[int, int]]:
    out = []
    for d in decades:
        d = d.strip().lower().rstrip("s")
        if d.isdigit() and len(d) == 4:
            start = int(d) // 10 * 10
            out.append((start, start + 9))
    return out


def build_candidates(session: Session, q: PlaylistQuery) -> list[Track]:
    regions = [r for r in q.regions if r in ALL_REGIONS] or ALL_REGIONS

    chart_filter = and_(
        SongChart.song_id == Song.id,
        SongChart.region.in_(regions),
        SongChart.peak_position <= q.level.max_peak,
    )

    stmt = (
        select(
            Song,
            func.min(SongChart.peak_position).label("best_peak"),
            func.sum(SongChart.weeks_on_chart).label("total_weeks"),
        )
        .join(SongChart, chart_filter)
        .join(Artist, Artist.id == Song.artist_id)
        .group_by(Song.id)
        .options(selectinload(Song.charts))
    )

    bounds = _decade_bounds(q.decades)
    if bounds:
        stmt = stmt.where(or_(*[Song.year.between(a, b) for a, b in bounds]))
    if q.year_from:
        stmt = stmt.where(Song.year >= q.year_from)
    if q.year_to:
        stmt = stmt.where(Song.year <= q.year_to)

    if q.artist_type != ArtistTypeFilter.ANY:
        stmt = stmt.where(Artist.type == q.artist_type.value)

    if q.artists:
        keys = [artist_key(a) for a in q.artists]
        stmt = stmt.where(Artist.name_norm.in_(keys))

    if q.genres:
        song_has = exists().where(
            SongGenre.song_id == Song.id,
            SongGenre.genre_id == Genre.id,
            Genre.slug.in_(q.genres),
        )
        artist_has = exists().where(
            ArtistGenre.artist_id == Artist.id,
            ArtistGenre.genre_id == Genre.id,
            Genre.slug.in_(q.genres),
        )
        stmt = stmt.where(or_(song_has, artist_has))

    if q.ohw != OneHitWonder.ANY:
        # One-hit-wonder: exactly one Top-40 song in the selected full-chart regions
        # (falls back to all full-chart regions if only AT/DE are selected)
        ohw_regions = [r for r in regions if r in FULL_CHART_REGIONS] or FULL_CHART_REGIONS
        ohw_exists = exists().where(
            ArtistRegionStats.artist_id == Artist.id,
            ArtistRegionStats.region.in_(ohw_regions),
            ArtistRegionStats.songs_top40 == 1,
        )
        # ...and no region where they had more than one
        multi_exists = exists().where(
            ArtistRegionStats.artist_id == Artist.id,
            ArtistRegionStats.region.in_(ohw_regions),
            ArtistRegionStats.songs_top40 > 1,
        )
        is_ohw = and_(ohw_exists, ~multi_exists, SongChart.peak_position <= 40)
        stmt = stmt.where(is_ohw if q.ohw == OneHitWonder.ONLY else ~is_ohw)

    rows = session.execute(stmt).all()
    return [Track(song, int(bp), int(tw)) for song, bp, tw in rows]


def order_and_pick(tracks: list[Track], q: PlaylistQuery, seed: int) -> list[Track]:
    if q.sort == Sort.RANDOM:
        rng = random.Random(seed)
        rng.shuffle(tracks)
    elif q.sort == Sort.SUCCESS:
        tracks.sort(key=lambda t: (t.best_peak, -t.total_weeks, t.song.year))
    elif q.sort == Sort.YEAR:
        tracks.sort(key=lambda t: (t.song.year, t.best_peak))
    elif q.sort == Sort.YEAR_DESC:
        tracks.sort(key=lambda t: (-t.song.year, t.best_peak))

    # An explicit artist filter overrides the diversity cap
    cap = q.count if q.artists else q.max_per_artist
    per_artist: dict[int, int] = defaultdict(int)
    picked: list[Track] = []
    for t in tracks:
        if per_artist[t.song.artist_id] >= cap:
            continue
        per_artist[t.song.artist_id] += 1
        picked.append(t)
        if len(picked) >= q.count:
            break
    return picked


def generate(session: Session, q: PlaylistQuery) -> tuple[list[Track], int, int]:
    """Returns (tracks, total_matching, seed)."""
    seed = q.seed if q.seed is not None else random.randrange(1, 10**9)
    candidates = build_candidates(session, q)
    return order_and_pick(candidates, q, seed), len(candidates), seed


def playlist_name(q: PlaylistQuery, genre_names: dict[str, str] | None = None) -> str:
    parts: list[str] = []
    if q.artists:
        parts.append(", ".join(q.artists))
    if q.decades:
        parts.append(" & ".join(d.replace("s", "er") for d in sorted(q.decades)))
    elif q.year_from or q.year_to:
        parts.append(f"{q.year_from or ''}–{q.year_to or ''}")
    if q.level.value != "all":
        parts.append({"no1": "Nr.-1-Hits", "top10": "Top 10", "top40": "Top 40"}[q.level.value])
    if q.ohw == OneHitWonder.ONLY:
        parts.append("One-Hit-Wonder")
    if q.artist_type != ArtistTypeFilter.ANY:
        parts.append({"person": "Solo", "group": "Bands", "duo": "Duos"}[q.artist_type.value])
    if q.genres:
        names = genre_names or {}
        parts.append(", ".join(names.get(g, g) for g in q.genres))
    if q.regions:
        parts.append("/".join(q.regions))
    return " · ".join(parts) or "Playlist"
