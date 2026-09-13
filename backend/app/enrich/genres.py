"""Map free-form MusicBrainz tags onto a small, user-facing genre taxonomy."""

from collections import defaultdict

# slug → (display name, keyword rules). A tag matches a genre if it contains any
# keyword; a tag may map to several genres ("pop rock" → Pop + Rock).
GENRES: dict[str, tuple[str, tuple[str, ...]]] = {
    "hiphop": ("Hip-Hop / Rap", ("hip hop", "hip-hop", "hiphop", "rap", "trap", "drill", "grime")),
    "rnb": (
        "R&B / Soul",
        ("r&b", "rnb", "rhythm and blues", "soul", "motown", "doo-wop", "doo wop"),
    ),
    "disco": ("Disco / Funk", ("disco", "funk", "boogie")),
    "electronic": (
        "Dance / Electronic",
        (
            "electro",
            "edm",
            "house",
            "techno",
            "trance",
            "dance",
            "synth",
            "drum and bass",
            "dubstep",
            "eurobeat",
            "italo",
            "rave",
            "garage",
            "big beat",
            "trip hop",
            "downtempo",
        ),
    ),
    "country": ("Country", ("country", "bluegrass", "americana", "honky tonk")),
    "metal": ("Metal", ("metal", "hardcore punk", "thrash", "grindcore")),
    "punk": ("Punk / New Wave", ("punk", "new wave", "post-punk", "emo", "ska punk")),
    "indie": (
        "Alternative / Indie",
        ("indie", "alternative", "grunge", "shoegaze", "britpop", "lo-fi"),
    ),
    "reggae": ("Reggae / Dancehall", ("reggae", "ska", "dancehall", "dub")),
    "jazz": ("Jazz / Blues", ("jazz", "blues", "swing", "big band", "bebop")),
    "folk": ("Folk", ("folk", "singer-songwriter", "singer/songwriter", "acoustic")),
    "latin": (
        "Latin",
        (
            "latin",
            "salsa",
            "reggaeton",
            "bachata",
            "cumbia",
            "flamenco",
            "tango",
            "bossa nova",
            "samba",
            "merengue",
            "tejano",
        ),
    ),
    "schlager": ("Schlager / Volksmusik", ("schlager", "volksmusik", "volkstümlich", "austropop")),
    "soundtrack": (
        "Soundtrack / Klassik",
        ("soundtrack", "classical", "orchestral", "film score", "musical", "film music", "opera"),
    ),
    "gospel": ("Gospel / Christian", ("gospel", "christian", "worship")),
    "rock": ("Rock", ("rock", "rockabilly", "psychedelic", "glam", "prog", "surf")),
    "pop": (
        "Pop",
        (
            "pop",
            "adult contemporary",
            "easy listening",
            "boy band",
            "girl group",
            "bubblegum",
            "eurovision",
            "vocal",
            "crooner",
            "ballad",
        ),
    ),
}

# tags that contain a keyword but mean something else
_EXCLUDE = {
    "rock": ("post-rock",),
    "pop": ("popular music", "k-pop", "j-pop", "populaire"),
    "reggae": ("reggaeton",),
    "electronic": ("dancehall",),
}
_NOISE = (
    "seen live",
    "vocalists",
    "american",
    "british",
    "german",
    "austrian",
    "usa",
    "uk",
    "male",
    "female",
    "1960s",
    "1970s",
    "1980s",
    "1990s",
    "2000s",
    "70s",
    "80s",
    "90s",
)


def genres_for_tag(tag: str) -> set[str]:
    t = tag.lower().strip()
    if any(n in t for n in _NOISE) and not any(kw in t for _, kws in GENRES.values() for kw in kws):
        return set()
    out = set()
    for slug, (_, kws) in GENRES.items():
        if any(kw in t for kw in kws) and not any(x in t for x in _EXCLUDE.get(slug, ())):
            out.add(slug)
    return out


def genres_from_tags(tags: list[tuple[str, int]], max_genres: int = 3) -> list[str]:
    """Weighted tags [(name, count)] → up to `max_genres` genre slugs, most voted first."""
    score: dict[str, float] = defaultdict(float)
    for name, count in tags:
        for slug in genres_for_tag(name):
            score[slug] += max(count, 0) + 0.5  # 0-count tags still carry a little weight
    ranked = sorted(score.items(), key=lambda kv: -kv[1])
    if not ranked:
        return []
    top = ranked[0][1]
    # keep genres that are at least a quarter as strong as the best one
    return [slug for slug, sc in ranked[:max_genres] if sc >= top / 4]
