"""Name normalisation and artist-credit parsing shared by all importers."""

import re
import unicodedata

# Separators that split a chart credit into individual artists. Order matters:
# longer / more specific tokens first. Matching is case-insensitive.
_CREDIT_SEPARATORS = [
    r"\s+a\s+duet\s+with\s+",
    r"\s+duet\s+with\s+",
    r"\s+featuring\s+",
    r"\s+feat\.?\s+",
    r"\s+ft\.?\s+",
    r"\s+with\s+",
    r"\s+&\s+",
    r"\s+and\s+",
    r"\s+\+\s+",
    r"\s*/\s*",
    r"\s*,\s*",
]
_SPLIT_RE = re.compile("|".join(_CREDIT_SEPARATORS), re.IGNORECASE)
# "(Duet With X)", "(Featuring X)" → " featuring X"
_PAREN_CREDIT_RE = re.compile(
    r"\s*\((?:a\s+)?(?:duet\s+with|featuring|feat\.?|ft\.?|with)\s+([^)]*)\)", re.IGNORECASE
)

# Artists whose names contain a separator token and must not be split.
_PROTECTED = {
    "earth, wind & fire",
    "simon & garfunkel",
    "hall & oates",
    "daryl hall & john oates",
    "kool & the gang",
    "peaches & herb",
    "ike & tina turner",
    "sonny & cher",
    "captain & tennille",
    "ashford & simpson",
    "mel & kim",
    "chas & dave",
    "sam & dave",
    "brooks & dunn",
    "florida georgia line",
    "salt-n-pepa",
    "kc and the sunshine band",
    "kc & the sunshine band",
    "bob seger & the silver bullet band",
    "tom petty and the heartbreakers",
    "tom petty & the heartbreakers",
    "prince and the revolution",
    "prince & the revolution",
    "bruce hornsby & the range",
    "huey lewis & the news",
    "gladys knight & the pips",
    "martha & the vandellas",
    "smokey robinson & the miracles",
    "diana ross & the supremes",
    "sly & the family stone",
    "gary puckett & the union gap",
    "paul revere & the raiders",
    "tommy james & the shondells",
    "bill haley & his comets",
    "buddy holly & the crickets",
    "derek & the dominos",
    "big brother & the holding company",
    "country joe & the fish",
    "mike + the mechanics",
    "mike & the mechanics",
    "bob marley & the wailers",
    "the mamas & the papas",
    "the mamas and the papas",
    "peter, paul & mary",
    "peter, paul and mary",
    "emerson, lake & palmer",
    "crosby, stills & nash",
    "crosby, stills, nash & young",
    "blood, sweat & tears",
    "hootie & the blowfish",
    "edward sharpe & the magnetic zeros",
    "rob thomas",
    "florence + the machine",
    "marina and the diamonds",
    "echo & the bunnymen",
    "siouxsie & the banshees",
    "nick cave & the bad seeds",
    "belle & sebastian",
    "she & him",
    "of monsters and men",
    "the pretty reckless",
    "dan + shay",
    "chase & status",
    "rizzle kicks",
    "sugarland",
}


def normalize(s: str) -> str:
    """Lower-case, strip accents and punctuation, collapse whitespace."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _strip_the(s: str) -> str:
    return s[4:] if s.lower().startswith("the ") else s


def split_credit(credit: str) -> list[str]:
    """Split a chart credit like "Elton John & Kiki Dee" into ["Elton John", "Kiki Dee"].

    Protected band names containing '&', 'and' or ',' are kept intact.
    """
    credit = _PAREN_CREDIT_RE.sub(r" featuring \1", credit).strip()
    if credit.lower() in _PROTECTED:
        return [credit]
    # "X & The Y" is almost always a single act (leader + backing band)
    if re.search(r"\s(&|and)\s+the\s", credit, re.IGNORECASE) and not re.search(
        r"\s(featuring|feat\.?|ft\.?|with)\s", credit, re.IGNORECASE
    ):
        return [credit]
    parts = [p.strip() for p in _SPLIT_RE.split(credit) if p and p.strip()]
    if not parts:
        return [credit]
    # Re-join accidental splits of protected names inside a longer credit
    out: list[str] = []
    for p in parts:
        if out and f"{out[-1]} & {p}".lower() in _PROTECTED:
            out[-1] = f"{out[-1]} & {p}"
        elif out and f"{out[-1]}, {p}".lower() in _PROTECTED:
            out[-1] = f"{out[-1]}, {p}"
        else:
            out.append(p)
    return out


def primary_artist(credit: str) -> str:
    return split_credit(credit)[0]


def artist_key(name: str) -> str:
    """Normalised key used to merge the same artist across sources ("The Beatles" == "Beatles")."""
    return normalize(_strip_the(name.strip()))


def decade_of(year: int) -> str:
    return f"{year // 10 * 10}s"
