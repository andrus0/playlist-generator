from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_session
from ..models import Artist, ArtistGenre, Genre, ImportRun, Song, SongChart
from ..normalize import normalize
from ..schemas import (
    ArtistOut,
    ChartOut,
    Format,
    MetaOut,
    PlaylistOut,
    PlaylistQuery,
    TrackOut,
    playlist_query,
)
from ..services import export
from ..services.generator import ALL_REGIONS, FULL_CHART_REGIONS, generate, playlist_name

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
router = APIRouter(prefix="/api")

REGION_NAMES = {
    "US": "Billboard Hot 100 (US)",
    "UK": "Official Singles Chart (UK)",
    "AT": "Ö3 Austria Top 40",
    "DE": "Offizielle Deutsche Charts",
}


@router.get("/healthz", include_in_schema=False)
def healthz(session: Annotated[Session, Depends(get_session)]) -> dict:
    session.execute(select(1))
    return {"status": "ok"}


@router.get("/meta", response_model=MetaOut)
def meta(session: Annotated[Session, Depends(get_session)]) -> MetaOut:
    songs = session.scalar(select(func.count(Song.id))) or 0
    artists = session.scalar(select(func.count(Artist.id))) or 0
    years = session.execute(select(func.min(Song.year), func.max(Song.year))).one()
    decades = []
    if years[0]:
        decades = [f"{d}s" for d in range(years[0] // 10 * 10, years[1] // 10 * 10 + 1, 10)]
    region_counts = dict(
        session.execute(select(SongChart.region, func.count()).group_by(SongChart.region)).all()
    )
    # songs per genre = songs tagged directly + songs whose artist carries the genre
    genres = session.execute(
        select(Genre.slug, Genre.name, func.count(func.distinct(Song.id)))
        .outerjoin(ArtistGenre, ArtistGenre.genre_id == Genre.id)
        .outerjoin(Song, Song.artist_id == ArtistGenre.artist_id)
        .group_by(Genre.id)
        .order_by(Genre.name)
    ).all()
    genres = [g for g in genres if g[2] > 0]
    imports = session.execute(
        select(
            ImportRun.source, func.max(ImportRun.finished_at), func.max(ImportRun.latest_chart_date)
        ).group_by(ImportRun.source)
    ).all()
    return MetaOut(
        songs=songs,
        artists=artists,
        decades=decades,
        regions=[
            {
                "code": r,
                "name": REGION_NAMES[r],
                "songs": region_counts.get(r, 0),
                "coverage": "full" if r in FULL_CHART_REGIONS else "no1",
            }
            for r in ALL_REGIONS
        ],
        genres=[{"slug": s, "name": n, "songs": c} for s, n, c in genres],
        imports=[
            {"source": s, "finished_at": f, "latest_chart_date": latest} for s, f, latest in imports
        ],
    )


@router.get("/artists", response_model=list[ArtistOut])
def artists(
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[ArtistOut]:
    key = normalize(q)
    stmt = (
        select(Artist, func.count(Song.id).label("n"))
        .join(Song, Song.artist_id == Artist.id)
        .where(Artist.name_norm.like(f"%{key}%"))
        .group_by(Artist.id)
        .order_by(
            # prefix matches first, then by number of songs
            (Artist.name_norm.like(f"{key}%")).desc(),
            func.count(Song.id).desc(),
        )
        .limit(limit)
    )
    return [
        ArtistOut(id=a.id, name=a.name, type=a.type, songs=n)
        for a, n in session.execute(stmt).all()
    ]


def _to_out(
    q: PlaylistQuery, tracks, total: int, seed: int, genre_names: dict[str, str] | None = None
) -> PlaylistOut:
    out = []
    for i, t in enumerate(tracks, 1):
        out.append(
            TrackOut(
                position=i,
                title=t.song.title,
                artist=t.song.artist_display,
                year=t.song.year,
                charts=[
                    ChartOut(
                        region=c.region,
                        peak=c.peak_position,
                        weeks=c.weeks_on_chart,
                        year=c.first_date.year,
                    )
                    for c in sorted(t.song.charts, key=lambda c: c.region)
                ],
            )
        )
    q = q.model_copy(update={"seed": seed})
    return PlaylistOut(
        name=playlist_name(q, genre_names), seed=seed, total_matching=total, tracks=out, query=q
    )


@router.get("/playlist", response_model=PlaylistOut)
@limiter.limit(settings.rate_limit)
def playlist(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[PlaylistQuery, Depends(playlist_query)],
    format: Format = Format.JSON,
):
    tracks, total, seed = generate(session, q)
    genre_names = (
        dict(session.execute(select(Genre.slug, Genre.name).where(Genre.slug.in_(q.genres))).all())
        if q.genres
        else None
    )
    out = _to_out(q, tracks, total, seed, genre_names)
    filename = "playlist"
    match format:
        case Format.TXT:
            return PlainTextResponse(
                export.to_txt(out),
                headers={"Content-Disposition": f'attachment; filename="{filename}.txt"'},
            )
        case Format.CSV:
            return Response(
                export.to_csv(out),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
            )
        case Format.M3U:
            return Response(
                export.to_m3u(out),
                media_type="audio/x-mpegurl",
                headers={"Content-Disposition": f'attachment; filename="{filename}.m3u"'},
            )
    return out
