from app.schemas import ArtistTypeFilter, ChartLevel, OneHitWonder, PlaylistQuery, Sort
from app.services.generator import generate


def titles(tracks):
    return [t.song.title for t in tracks]


def test_decade_filter(session):
    tracks, total, _ = generate(session, PlaylistQuery(decades=["1980s"], count=100, seed=1))
    assert total == 10
    assert all(1980 <= t.song.year <= 1989 for t in tracks)


def test_year_range(session):
    tracks, _, _ = generate(session, PlaylistQuery(year_from=1968, year_to=1977, count=100))
    assert sorted(titles(tracks)) == [
        "Bohemian Rhapsody",
        "Hey Jude",
        "Let It Be",
        "We Are The Champions",
    ]


def test_chart_level_number_one_in_region(session):
    # Bohemian Rhapsody peaked #9 in the US but #1 in the UK
    us, _, _ = generate(
        session, PlaylistQuery(regions=["US"], level=ChartLevel.NUMBER_ONE, count=100)
    )
    uk, _, _ = generate(
        session, PlaylistQuery(regions=["UK"], level=ChartLevel.NUMBER_ONE, count=100)
    )
    assert "Bohemian Rhapsody" not in titles(us)
    assert "Bohemian Rhapsody" in titles(uk)


def test_one_hit_wonder_only(session):
    tracks, _, _ = generate(
        session, PlaylistQuery(regions=["US"], ohw=OneHitWonder.ONLY, count=100)
    )
    got = set(titles(tracks))
    # Toni Basil: one top-40 song. Dexys: one in the US (two in the UK, but UK not selected).
    assert got == {"Mickey", "Come On Eileen", "Baby One More Time", "Old Town Road"}


def test_one_hit_wonder_across_regions(session):
    # With the UK included, Dexys had two Top-40 hits → not a one-hit wonder
    tracks, _, _ = generate(session, PlaylistQuery(ohw=OneHitWonder.ONLY, count=100))
    assert "Come On Eileen" not in titles(tracks)
    assert "Mickey" in titles(tracks)


def test_one_hit_wonder_exclude(session):
    tracks, _, _ = generate(
        session, PlaylistQuery(regions=["US"], ohw=OneHitWonder.EXCLUDE, count=100)
    )
    assert "Mickey" not in titles(tracks)
    assert "Africa" in titles(tracks)
    # "Obscure" never reached the top 40 → its artist is not an OHW, and it's kept
    assert "Obscure" in titles(tracks)


def test_artist_filter_ignores_the_prefix_and_cap(session):
    tracks, total, _ = generate(
        session, PlaylistQuery(artists=["Beatles"], count=10, max_per_artist=1)
    )
    assert total == 2 and len(tracks) == 2


def test_artist_type(session):
    tracks, _, _ = generate(session, PlaylistQuery(artist_type=ArtistTypeFilter.PERSON, count=100))
    assert set(titles(tracks)) == {"Mickey", "Baby One More Time"}


def test_max_per_artist(session):
    tracks, _, _ = generate(session, PlaylistQuery(count=100, max_per_artist=1, seed=3))
    artists = [t.song.artist_id for t in tracks]
    assert len(artists) == len(set(artists))


def test_seed_is_reproducible(session):
    a, _, seed = generate(session, PlaylistQuery(count=5, seed=99))
    b, _, _ = generate(session, PlaylistQuery(count=5, seed=99))
    c, _, _ = generate(session, PlaylistQuery(count=5, seed=100))
    assert titles(a) == titles(b)
    assert seed == 99
    assert titles(a) != titles(c)


def test_sort_success(session):
    tracks, _, _ = generate(session, PlaylistQuery(sort=Sort.SUCCESS, count=3))
    assert titles(tracks)[0] == "Old Town Road"  # #1 with the most weeks


def test_sort_year(session):
    tracks, _, _ = generate(session, PlaylistQuery(sort=Sort.YEAR, count=100))
    years = [t.song.year for t in tracks]
    assert years == sorted(years)
