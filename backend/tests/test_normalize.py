import pytest

from app.normalize import artist_key, decade_of, normalize, primary_artist, split_credit


@pytest.mark.parametrize(
    "credit,expected",
    [
        ("Elton John & Kiki Dee", ["Elton John", "Kiki Dee"]),
        ("Drake Featuring Lil Wayne", ["Drake", "Lil Wayne"]),
        ("Lil Nas X Featuring Billy Ray Cyrus", ["Lil Nas X", "Billy Ray Cyrus"]),
        ("Earth, Wind & Fire", ["Earth, Wind & Fire"]),
        ("Simon & Garfunkel", ["Simon & Garfunkel"]),
        ("Tom Petty And The Heartbreakers", ["Tom Petty And The Heartbreakers"]),
        ("Bob Seger & The Silver Bullet Band", ["Bob Seger & The Silver Bullet Band"]),
        ("Paula Abdul (Duet With The Wild Pair)", ["Paula Abdul", "The Wild Pair"]),
        ("Patti Austin A Duet With James Ingram", ["Patti Austin", "James Ingram"]),
        ("Peter, Paul & Mary", ["Peter, Paul & Mary"]),
        ("Queen", ["Queen"]),
    ],
)
def test_split_credit(credit, expected):
    assert split_credit(credit) == expected


def test_primary_artist():
    assert primary_artist("Wham! Featuring George Michael") == "Wham!"


def test_normalize_and_key():
    assert normalize("Beyoncé – Déjà Vu!") == "beyonce deja vu"
    assert artist_key("The Beatles") == artist_key("Beatles") == "beatles"
    assert artist_key("Earth, Wind & Fire") == "earth wind and fire"


def test_decade():
    assert decade_of(1987) == "1980s"
    assert decade_of(2000) == "2000s"


def test_comma_the_is_not_a_separator():
    assert split_credit("Tyler, The Creator") == ["Tyler, The Creator"]
    assert split_credit("Elton John, Dua Lipa") == ["Elton John", "Dua Lipa"]
