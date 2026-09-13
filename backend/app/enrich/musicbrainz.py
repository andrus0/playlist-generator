"""Artist enrichment via the MusicBrainz web service: type, country, genre tags.

MusicBrainz asks for ≤1 request/s and a descriptive User-Agent; both are
handled by PoliteClient. The job is resumable – artists already looked up
(mb_checked set) are skipped.
"""

import logging
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..importers.http import PoliteClient
from ..models import Artist, ArtistType, Genre, Song
from ..normalize import artist_key
from .genres import GENRES, genres_from_tags

log = logging.getLogger(__name__)

API = "https://musicbrainz.org/ws/2/artist/"
_DUO_RE = re.compile(r"^[^&]+?\s(&|and)\s(?!the\s)[^&]+$", re.IGNORECASE)


def ensure_genres(session: Session) -> dict[str, Genre]:
    existing = {g.slug: g for g in session.scalars(select(Genre)).all()}
    for slug, (name, _) in GENRES.items():
        if slug not in existing:
            g = Genre(slug=slug, name=name)
            session.add(g)
            existing[slug] = g
    session.flush()
    return existing


def pick_match(name: str, candidates: list[dict]) -> dict | None:
    """Best search hit: exact normalised name and high score, prefer well-tagged entries."""
    key = artist_key(name)
    good = [
        c
        for c in candidates
        if c.get("score", 0) >= 90
        and (
            artist_key(c["name"]) == key
            or any(artist_key(a.get("name", "")) == key for a in c.get("aliases", []))
        )
    ]
    if not good:
        return None
    good.sort(key=lambda c: (-c.get("score", 0), -len(c.get("tags", []))))
    return good[0]


def classify(name: str, mb_type: str | None) -> str:
    if mb_type == "Person":
        return ArtistType.PERSON
    if mb_type in ("Group", "Orchestra", "Choir"):
        return ArtistType.DUO if _DUO_RE.match(name) else ArtistType.GROUP
    return ArtistType.UNKNOWN


def apply(artist: Artist, hit: dict | None, genres: dict[str, Genre]) -> None:
    artist.mb_checked = date.today()
    if not hit:
        return
    artist.mb_id = hit.get("id")
    artist.country = hit.get("country")
    artist.type = classify(artist.name, hit.get("type"))
    tags = [(t["name"], int(t.get("count", 0))) for t in hit.get("tags", [])]
    artist.genres = [genres[s] for s in genres_from_tags(tags)]


def run(session: Session, limit: int | None = None, only_unchecked: bool = True) -> int:
    genres = ensure_genres(session)
    # most-charting artists first, so partial runs already cover what users see most
    stmt = (
        select(Artist)
        .join(Song, Song.artist_id == Artist.id)
        .group_by(Artist.id)
        .order_by(func.count(Song.id).desc())
    )
    if only_unchecked:
        stmt = stmt.where(Artist.mb_checked.is_(None))
    if limit:
        stmt = stmt.limit(limit)
    artists = session.scalars(stmt).all()
    log.info("musicbrainz: %d artists to look up", len(artists))
    done = 0
    with PoliteClient(min_interval=1.1) as client:
        for artist in artists:
            q = artist.name.replace('"', "")
            try:
                r = client.get(API, params={"query": f'artist:"{q}"', "fmt": "json", "limit": 5})
            except Exception as exc:  # network trouble: keep what we have, skip this artist
                log.warning("musicbrainz %s: %s – skipping", artist.name, exc)
                session.commit()
                continue
            if r.status_code != 200:
                log.warning("musicbrainz %s: HTTP %s", artist.name, r.status_code)
                continue
            hit = pick_match(artist.name, r.json().get("artists", []))
            apply(artist, hit, genres)
            done += 1
            if done % 50 == 0:
                session.commit()
                log.info("musicbrainz: %d/%d", done, len(artists))
    session.commit()
    return done
