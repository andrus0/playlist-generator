"""Number-one singles for Austria (Ö3 Austria Top 40) and Germany from the German
Wikipedia lists "Liste der Nummer-eins-Hits in Österreich/Deutschland (JAHR)".

Only #1 hits are available this way (the chart companies block crawlers), so
these regions have *no1* coverage rather than full charts. Content: CC BY-SA.
"""

import html as htmllib
import logging
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Region, SongChart
from .base import ChartEntry, upsert_entries
from .http import PoliteClient

log = logging.getLogger(__name__)

PAGE = {
    Region.AT: ("Liste der Nummer-eins-Hits in Österreich ({year})", 1965),
    Region.DE: ("Liste der Nummer-eins-Hits in Deutschland ({year})", 1953),
}
API = "https://de.wikipedia.org/api/rest_v1/page/html/{title}"

_TABLE_RE = re.compile(r'<table class="wikitable.*?</table>', re.S)
_ROW_RE = re.compile(r"<tr.*?</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_SORT_RE = re.compile(r'data-sort-value="(\d{4}-\d{2}-\d{2})"')
_TAG_RE = re.compile(r"<[^>]+>")
_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "januar",
            "februar",
            "märz",
            "april",
            "mai",
            "juni",
            "juli",
            "august",
            "september",
            "oktober",
            "november",
            "dezember",
        ],
        1,
    )
}
_DATE_RE = re.compile(r"(\d{1,2})\.\s*([A-Za-zä]+)\s*(\d{4})")


def _first_line(cell: str) -> str:
    """Text before the first <br> (title/artist sit above authors/extra info)."""
    cell = re.split(r"<br\s*/?>", cell, maxsplit=1)[0]
    return htmllib.unescape(_TAG_RE.sub("", cell)).replace("\xa0", " ").strip()


def _parse_date(cell_html: str) -> date | None:
    m = _SORT_RE.search(cell_html)
    if m:
        return date.fromisoformat(m.group(1))
    text = htmllib.unescape(_TAG_RE.sub("", cell_html)).replace("\xa0", " ")
    m = _DATE_RE.search(text)
    if m and m.group(2).lower() in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def parse_page(page: str) -> list[ChartEntry]:
    """First wikitable = singles. Columns: Zeitraum | Wo.ges. | Interpret | Titel | ..."""
    tables = _TABLE_RE.findall(page)
    if not tables:
        return []
    entries = []
    for row in _ROW_RE.findall(tables[0]):
        cells = _CELL_RE.findall(row)
        if len(cells) < 4 or "<th" in row:
            continue
        start = _parse_date(cells[0])
        if not start:
            continue
        weeks_txt = _TAG_RE.sub("", cells[1]).strip()
        weeks = int(weeks_txt) if weeks_txt.isdigit() else 1
        artist, title = _first_line(cells[2]), _first_line(cells[3])
        if not artist or not title:
            continue
        entries.append(
            ChartEntry(
                title=title,
                artist=artist,
                peak_position=1,
                weeks_on_chart=weeks,
                first_date=start,
                last_date=min(
                    start + timedelta(weeks=max(weeks, 1)) - timedelta(days=1), date.today()
                ),
            )
        )
    return entries


def has_data(session: Session, region: str) -> bool:
    return (
        session.scalar(select(SongChart.id).where(SongChart.region == region).limit(1)) is not None
    )


def run(session: Session, region: str, years: range | None = None) -> int:
    template, first_year = PAGE[Region(region)]
    years = years or range(first_year, date.today().year + 1)
    merged: dict[tuple[str, str], ChartEntry] = {}
    with PoliteClient(min_interval=0.5) as client:
        for year in years:
            title = template.format(year=year).replace(" ", "_")
            r = client.get(API.format(title=title))
            if r.status_code == 404:
                log.info("%s %s: no page", region, year)
                continue
            r.raise_for_status()
            for e in parse_page(r.text):
                key = (e.title.lower(), e.artist.lower())
                if key in merged:
                    m = merged[key]
                    m.weeks_on_chart = max(m.weeks_on_chart, e.weeks_on_chart)
                    m.first_date = min(m.first_date, e.first_date)
                    m.last_date = max(m.last_date, e.last_date)
                else:
                    merged[key] = e
    return upsert_entries(session, region, list(merged.values()), merge=True)
