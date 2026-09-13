"""UK Official Singles Chart, 1952 → today (officialcharts.com).

Every weekly page carries each song's peak and weeks-on-chart, so a single
pass over all weeks yields complete chart runs. The crawl is incremental: it
resumes from the last imported week and follows the page's "next week" link.
"""

import html as htmllib
import logging
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportRun, Region
from ..normalize import smart_title
from .base import ChartEntry, upsert_entries
from .http import PoliteClient

log = logging.getLogger(__name__)

BASE = "https://www.officialcharts.com"
FIRST_CHART = date(1952, 11, 14)
CHART_URL = BASE + "/charts/singles-chart/{:%Y%m%d}/7501/"

_ITEM_RE = re.compile(
    r'<div class="(?:primis )?chart-item relative text-right".*?'
    r'(?=<div class="(?:primis )?chart-item (?:relative|chart-ad)|$)',
    re.S,
)
_POS_RE = re.compile(r'class="position">.*?<strong>(\d+)</strong>', re.S)
# the title is the last plain <span> inside the chart-name link (movement badges come first)
_NAME_RE = re.compile(
    r'class="chart-name[^"]*">(?:<!---->|<span[^>]*>.*?</span>)*?<span>(.*?)</span></a>', re.S
)
_ARTIST_RE = re.compile(r'class="chart-artist[^"]*"><span>(.*?)</span>', re.S)
_PEAK_RE = re.compile(r"Peak: <span[^>]*>(\d+)</span>")
_WEEKS_RE = re.compile(r"Weeks: <span[^>]*>(\d+)</span>")
_NEXT_RE = re.compile(r'href="/charts/singles-chart/(\d{8})/7501/"')
_TAG_RE = re.compile(r"<[^>]+>")


def _text(s: str) -> str:
    return htmllib.unescape(_TAG_RE.sub("", s)).strip()


def parse_week(page: str, week: date) -> tuple[list[ChartEntry], date | None]:
    """Parse one chart page → (entries, next_week_date)."""
    entries: list[ChartEntry] = []
    for m in _ITEM_RE.finditer(page):
        item = m.group(0)
        pos, name, artist = _POS_RE.search(item), _NAME_RE.search(item), _ARTIST_RE.search(item)
        if not (pos and name and artist):
            continue
        peak = _PEAK_RE.search(item)
        weeks = _WEEKS_RE.search(item)
        entries.append(
            ChartEntry(
                title=smart_title(_text(name.group(1))),
                artist=smart_title(_text(artist.group(1))),
                peak_position=int(peak.group(1)) if peak else int(pos.group(1)),
                weeks_on_chart=int(weeks.group(1)) if weeks else 1,
                first_date=week,
                last_date=week,
            )
        )
    nxt = None
    for d in _NEXT_RE.findall(page):
        cand = date(int(d[:4]), int(d[4:6]), int(d[6:]))
        if cand > week and (nxt is None or cand < nxt):
            nxt = cand
    return entries, nxt


def last_imported_week(session: Session) -> date | None:
    return session.scalar(
        select(ImportRun.latest_chart_date)
        .where(ImportRun.source == Region.UK)
        .order_by(ImportRun.latest_chart_date.desc())
        .limit(1)
    )


def _fetch_week(client: PoliteClient, wanted: date) -> tuple[str, date] | None:
    """GET the chart for `wanted`; the site redirects to the nearest chart date on/before it."""
    r = client.get(CHART_URL.format(wanted))
    if r.status_code == 404:
        return None
    r.raise_for_status()
    m = re.search(r"/singles-chart/(\d{8})/", str(r.url))
    actual = date(int(m[1][:4]), int(m[1][4:6]), int(m[1][6:])) if m else wanted
    return r.text, actual


def run(session: Session, start: date | None = None, max_weeks: int | None = None) -> int:
    """Crawl weekly charts from `start` (default: after the last imported week) and merge them.

    Chart dates are stepped by 7 days; when the chart day shifts (e.g. Sunday → Friday
    in 2015) the site's redirect to the nearest chart date re-syncs the walk.
    """
    last = None if start else last_imported_week(session)
    wanted = start or (last + timedelta(days=7) if last else FIRST_CHART)
    total, done = 0, 0
    batch: dict[tuple[str, str], ChartEntry] = {}
    with PoliteClient(min_interval=1.0) as client:
        while wanted <= date.today():
            fetched = _fetch_week(client, wanted)
            if fetched is None:
                break
            page, week = fetched
            if last and week <= last:
                # redirected back to an already imported chart → probe a few days further
                if wanted - last > timedelta(days=21):
                    break  # no newer chart exists yet
                wanted += timedelta(days=1)
                continue
            entries, _ = parse_week(page, week)
            for e in entries:
                key = (e.title.lower(), e.artist.lower())
                if key in batch:
                    b = batch[key]
                    b.peak_position = min(b.peak_position, e.peak_position)
                    b.weeks_on_chart = max(b.weeks_on_chart, e.weeks_on_chart)
                    b.last_date = week
                else:
                    batch[key] = e
            last = week
            done += 1
            if done % 10 == 0:
                log.info("UK: week %s (%d/%s)", week, done, max_weeks or "∞")
            if done % 26 == 0 or (max_weeks and done >= max_weeks):
                total += upsert_entries(session, Region.UK, list(batch.values()), merge=True)
                batch.clear()
                log.info("UK: imported up to %s (%d weeks this run)", week, done)
            if max_weeks and done >= max_weeks:
                break
            wanted = week + timedelta(days=7)
    if batch:
        total += upsert_entries(session, Region.UK, list(batch.values()), merge=True)
        log.info("UK: imported up to %s (%d weeks this run)", last, done)
    return total
