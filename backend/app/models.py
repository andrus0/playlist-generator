"""Database schema.

Chart data is stored *aggregated per song and region* (peak, weeks, first/last
week) rather than week-by-week – that is all the filters need and keeps the
table small. Artist statistics per region (number of charting songs etc.) are
derived after import and drive the one-hit-wonder filter.
"""

from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Region(StrEnum):
    US = "US"  # Billboard Hot 100
    UK = "UK"  # Official Singles Chart
    AT = "AT"  # Ö3 Austria Top 40
    DE = "DE"  # Offizielle Deutsche Charts


class ArtistType(StrEnum):
    PERSON = "person"
    GROUP = "group"
    DUO = "duo"
    UNKNOWN = "unknown"


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    name_norm: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(16), default=ArtistType.UNKNOWN, index=True)
    mb_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    country: Mapped[str | None] = mapped_column(String(2))
    # date of the last MusicBrainz lookup (None = not enriched yet)
    mb_checked: Mapped[date | None] = mapped_column(Date)

    songs: Mapped[list["Song"]] = relationship(back_populates="artist")
    stats: Mapped[list["ArtistRegionStats"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )
    genres: Mapped[list["Genre"]] = relationship(
        secondary="artist_genres", back_populates="artists"
    )


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (UniqueConstraint("title_norm", "artist_display_norm"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    title_norm: Mapped[str] = mapped_column(String(255), index=True)
    # Full credit as printed on the chart, e.g. "Elton John & Kiki Dee"
    artist_display: Mapped[str] = mapped_column(String(255))
    artist_display_norm: Mapped[str] = mapped_column(String(255))
    # Primary (first credited) artist
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), index=True)
    # Year of first chart appearance across all regions
    year: Mapped[int] = mapped_column(Integer, index=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    mb_id: Mapped[str | None] = mapped_column(String(36))

    artist: Mapped[Artist] = relationship(back_populates="songs")
    charts: Mapped[list["SongChart"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )
    genres: Mapped[list["Genre"]] = relationship(secondary="song_genres", back_populates="songs")


class SongChart(Base):
    __tablename__ = "song_charts"
    __table_args__ = (
        UniqueConstraint("song_id", "region"),
        Index("ix_song_charts_region_peak", "region", "peak_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    region: Mapped[str] = mapped_column(String(2))
    peak_position: Mapped[int] = mapped_column(Integer)
    weeks_on_chart: Mapped[int] = mapped_column(Integer)
    first_date: Mapped[date] = mapped_column(Date)
    last_date: Mapped[date] = mapped_column(Date)

    song: Mapped[Song] = relationship(back_populates="charts")


class ArtistRegionStats(Base):
    """Derived per import: how many charting songs an artist has in a region."""

    __tablename__ = "artist_region_stats"
    __table_args__ = (UniqueConstraint("artist_id", "region"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    region: Mapped[str] = mapped_column(String(2), index=True)
    songs_total: Mapped[int] = mapped_column(Integer, default=0)
    songs_top40: Mapped[int] = mapped_column(Integer, default=0)
    songs_top10: Mapped[int] = mapped_column(Integer, default=0)
    number_ones: Mapped[int] = mapped_column(Integer, default=0)

    artist: Mapped[Artist] = relationship(back_populates="stats")


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    artists: Mapped[list[Artist]] = relationship(secondary="artist_genres", back_populates="genres")
    songs: Mapped[list[Song]] = relationship(secondary="song_genres", back_populates="genres")


class ArtistGenre(Base):
    __tablename__ = "artist_genres"

    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class SongGenre(Base):
    __tablename__ = "song_genres"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class ImportRun(Base):
    """Bookkeeping for data imports (shown on /api/meta)."""

    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    finished_at: Mapped[date] = mapped_column(Date)
    latest_chart_date: Mapped[date | None] = mapped_column(Date)
    songs: Mapped[int] = mapped_column(Integer, default=0)
