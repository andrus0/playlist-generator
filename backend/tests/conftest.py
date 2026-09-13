import os
from datetime import date

os.environ["PLG_DATABASE_URL"] = "sqlite://"  # in-memory, set before app import
os.environ["PLG_RATE_LIMIT"] = "1000/minute"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db as _db  # noqa: E402
from app.importers.base import ChartEntry, compute_artist_stats, upsert_entries  # noqa: E402
from app.models import Artist, ArtistType  # noqa: E402

# One shared in-memory connection for the whole test session
_db.engine = _db._make_engine("sqlite://")
_db.engine.dispose()
from sqlalchemy import create_engine  # noqa: E402

_db.engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
_db.SessionLocal.configure(bind=_db.engine)


def entry(title, artist, peak, weeks, year, region_first=None):
    return ChartEntry(title, artist, peak, weeks, date(year, 6, 1), date(year, 6, 1))


FIXTURE = {
    "US": [
        entry("Africa", "Toto", 1, 20, 1982),
        entry("Rosanna", "Toto", 2, 22, 1982),
        entry("Mickey", "Toni Basil", 1, 18, 1982),
        entry("Come On Eileen", "Dexys Midnight Runners", 1, 15, 1983),
        entry("Bohemian Rhapsody", "Queen", 9, 24, 1976),
        entry("We Are The Champions", "Queen", 4, 20, 1977),
        entry("Hey Jude", "The Beatles", 1, 19, 1968),
        entry("Let It Be", "The Beatles", 1, 14, 1970),
        entry("Don't You Want Me", "The Human League", 1, 20, 1982),
        entry("Fascination", "The Human League", 8, 20, 1983),
        entry("Take On Me", "a-ha", 1, 27, 1985),
        entry("The Sun Always Shines On T.V.", "a-ha", 20, 12, 1985),
        entry("Baby One More Time", "Britney Spears", 1, 32, 1999),
        entry("Old Town Road", "Lil Nas X Featuring Billy Ray Cyrus", 1, 45, 2019),
        entry("Obscure", "Nobody", 95, 2, 1985),
    ],
    "UK": [
        entry("Come On Eileen", "Dexys Midnight Runners", 1, 17, 1982),
        entry("Geno", "Dexys Midnight Runners", 1, 14, 1980),
        entry("Bohemian Rhapsody", "Queen", 1, 17, 1975),
    ],
}


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    _db.init_db()
    with _db.SessionLocal() as s:
        for region, entries in FIXTURE.items():
            upsert_entries(s, region, entries)
        compute_artist_stats(s)
        # artist types (would come from MusicBrainz in production)
        for a in s.query(Artist).all():
            if a.name in ("Toto", "Queen", "Beatles", "Dexys Midnight Runners", "Human League"):
                a.type = ArtistType.GROUP
            elif a.name in ("Toni Basil", "Britney Spears"):
                a.type = ArtistType.PERSON
        s.commit()
    yield


@pytest.fixture
def session():
    with _db.SessionLocal() as s:
        yield s


@pytest.fixture(scope="session")
def client():
    from app.main import app

    return TestClient(app)
