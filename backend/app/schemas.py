from enum import StrEnum
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

from .config import settings


class ChartLevel(StrEnum):
    NUMBER_ONE = "no1"
    TOP10 = "top10"
    TOP40 = "top40"
    ALL = "all"

    @property
    def max_peak(self) -> int:
        return {"no1": 1, "top10": 10, "top40": 40, "all": 100}[self.value]


class OneHitWonder(StrEnum):
    ANY = "any"
    ONLY = "only"
    EXCLUDE = "exclude"


class ArtistTypeFilter(StrEnum):
    ANY = "any"
    PERSON = "person"
    GROUP = "group"
    DUO = "duo"


class Sort(StrEnum):
    RANDOM = "random"
    SUCCESS = "success"
    YEAR = "year"
    YEAR_DESC = "year_desc"


class Format(StrEnum):
    JSON = "json"
    TXT = "txt"
    CSV = "csv"
    M3U = "m3u"


class PlaylistQuery(BaseModel):
    """All filters. Every field is optional so the URL stays short and shareable."""

    decades: list[str] = Field(default_factory=list, description="e.g. 1970s,1980s")
    year_from: int | None = Field(None, ge=1950, le=2100)
    year_to: int | None = Field(None, ge=1950, le=2100)
    regions: list[str] = Field(default_factory=list, description="US,UK,AT,DE")
    level: ChartLevel = ChartLevel.ALL
    ohw: OneHitWonder = OneHitWonder.ANY
    artist_type: ArtistTypeFilter = ArtistTypeFilter.ANY
    artists: list[str] = Field(default_factory=list, description="artist names")
    genres: list[str] = Field(default_factory=list, description="genre slugs")
    count: int = Field(30, ge=1, le=settings.max_count)
    max_per_artist: int = Field(3, ge=1, le=settings.max_count)
    sort: Sort = Sort.RANDOM
    seed: int | None = None


def _csv(v: str | None) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()] if v else []


def playlist_query(
    decades: Annotated[str | None, Query()] = None,
    year_from: Annotated[int | None, Query(ge=1950, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1950, le=2100)] = None,
    regions: Annotated[str | None, Query()] = None,
    level: ChartLevel = ChartLevel.ALL,
    ohw: OneHitWonder = OneHitWonder.ANY,
    artist_type: ArtistTypeFilter = ArtistTypeFilter.ANY,
    artists: Annotated[str | None, Query()] = None,
    genres: Annotated[str | None, Query()] = None,
    count: Annotated[int, Query(ge=1, le=settings.max_count)] = 30,
    max_per_artist: Annotated[int, Query(ge=1, le=settings.max_count)] = 3,
    sort: Sort = Sort.RANDOM,
    seed: int | None = None,
) -> PlaylistQuery:
    """FastAPI dependency: comma-separated query params → PlaylistQuery."""
    return PlaylistQuery(
        decades=_csv(decades),
        year_from=year_from,
        year_to=year_to,
        regions=[r.upper() for r in _csv(regions)],
        level=level,
        ohw=ohw,
        artist_type=artist_type,
        artists=_csv(artists),
        genres=_csv(genres),
        count=count,
        max_per_artist=max_per_artist,
        sort=sort,
        seed=seed,
    )


class ChartOut(BaseModel):
    region: str
    peak: int
    weeks: int
    year: int


class TrackOut(BaseModel):
    position: int
    title: str
    artist: str
    year: int
    charts: list[ChartOut]


class PlaylistOut(BaseModel):
    name: str
    seed: int
    total_matching: int
    tracks: list[TrackOut]
    query: PlaylistQuery


class ArtistOut(BaseModel):
    id: int
    name: str
    type: str
    songs: int


class MetaOut(BaseModel):
    songs: int
    artists: int
    decades: list[str]
    regions: list[dict]
    genres: list[dict]
    imports: list[dict]
