from datetime import date
from pathlib import Path

from app.enrich.genres import genres_from_tags
from app.enrich.musicbrainz import classify, pick_match
from app.importers import uk, wikipedia
from app.importers.base import ChartEntry, song_key, upsert_entries
from app.models import Song, SongChart
from app.normalize import credit_key, smart_title

FIX = Path(__file__).parent / "fixtures"


def test_uk_parse_week():
    entries, nxt = uk.parse_week((FIX / "uk_19850616.html").read_text(), date(1985, 6, 16))
    assert nxt == date(1985, 6, 23)
    assert [e.peak_position for e in entries] == [1, 2, 3, 2]
    assert entries[1].title == "Frankie"
    assert entries[1].artist == "Sister Sledge"
    assert entries[1].weeks_on_chart == 5
    assert entries[0].title == "You'll Never Walk Alone"


def test_wikipedia_parse():
    entries = wikipedia.parse_page((FIX / "wp_at_1985.html").read_text())
    assert [e.artist for e in entries] == ["Scotch", "Band Aid", "Opus"]
    assert entries[0].title == "Disco Band"
    assert entries[0].first_date == date(1984, 12, 1)
    assert entries[0].weeks_on_chart == 7
    assert entries[1].title == "Do They Know It’s Christmas?"
    assert all(e.peak_position == 1 for e in entries)


def test_smart_title():
    assert smart_title("DON'T YOU WANT ME") == "Don't You Want Me"
    assert smart_title("NAT 'KING' COLE") == "Nat 'King' Cole"
    assert smart_title("THE POWER OF LOVE") == "The Power of Love"
    assert smart_title("Already Fine") == "Already Fine"


def test_credit_key_merges_feat_spellings():
    assert credit_key("Drake Featuring Lil Wayne") == credit_key("DRAKE FT LIL WAYNE")
    assert credit_key("Elton John & Kiki Dee") == credit_key("Elton John and Kiki Dee")
    assert song_key("Old Town Road", "Lil Nas X Feat. Billy Ray Cyrus") == song_key(
        "OLD TOWN ROAD", "Lil Nas X Featuring Billy Ray Cyrus"
    )


def test_upsert_merge_mode(session):
    e1 = ChartEntry("Merge Me", "Merge Artist", 30, 2, date(1990, 1, 7), date(1990, 1, 14))
    e2 = ChartEntry("MERGE ME", "MERGE ARTIST", 12, 6, date(1990, 1, 21), date(1990, 2, 18))
    upsert_entries(session, "UK", [e1], merge=True)
    upsert_entries(session, "UK", [e2], merge=True)
    song = session.query(Song).filter_by(title="Merge Me").one()  # first spelling wins
    chart = session.query(SongChart).filter_by(song_id=song.id, region="UK").one()
    assert (chart.peak_position, chart.weeks_on_chart) == (12, 6)
    assert (chart.first_date, chart.last_date) == (date(1990, 1, 7), date(1990, 2, 18))
    # replace mode overwrites
    upsert_entries(session, "UK", [e1])
    session.refresh(chart)
    assert chart.peak_position == 30


def test_genres_from_tags():
    assert genres_from_tags([("pop rock", 9), ("rock", 8), ("american", 2)]) == ["rock", "pop"]
    assert genres_from_tags([("hip hop", 5), ("seen live", 4)]) == ["hiphop"]
    assert genres_from_tags([("british", 3)]) == []
    assert "electronic" in genres_from_tags([("synthpop", 4)])


def test_classify_and_match():
    assert classify("Toni Basil", "Person") == "person"
    assert classify("Toto", "Group") == "group"
    assert classify("Simon & Garfunkel", "Group") == "duo"
    assert classify("Kool & The Gang", "Group") == "group"
    hits = [
        {"name": "Toto Cutugno", "score": 100, "type": "Person", "tags": []},
        {"name": "Toto", "score": 100, "type": "Group", "tags": [{"name": "rock", "count": 8}]},
        {"name": "The Beatles", "score": 100, "type": "Group", "tags": []},
    ]
    assert pick_match("Toto", hits)["type"] == "Group"
    assert pick_match("Beatles", hits)["name"] == "The Beatles"
    assert pick_match("Nobody Famous", hits) is None


def test_dedupe_merges_spelling_variants():
    from app.importers.base import dedupe

    a = ChartEntry("Hello", "Adele", 5, 3, date(2015, 11, 1), date(2015, 11, 15))
    b = ChartEntry("HELLO", "ADELE", 1, 10, date(2015, 10, 25), date(2016, 1, 3))
    (m,) = dedupe([a, b])
    assert (m.title, m.peak_position, m.weeks_on_chart) == ("Hello", 1, 10)
    assert (m.first_date, m.last_date) == (date(2015, 10, 25), date(2016, 1, 3))


def test_reggaeton_is_latin_not_reggae():
    assert genres_from_tags([("reggaeton", 5)]) == ["latin"]
