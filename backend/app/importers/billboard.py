"""Billboard Hot 100, 1958 → today.

Source: https://github.com/mhollingshead/billboard-hot-100 (weekly-updated JSON dump).
"""

import json
import logging
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Region
from .base import aggregate_weeks, upsert_entries

log = logging.getLogger(__name__)


def load(source: str | Path | None = None) -> list[dict]:
    src = str(source or settings.billboard_url)
    if src.startswith("http"):
        log.info("downloading %s", src)
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            r = client.get(src)
            r.raise_for_status()
            return r.json()
    return json.loads(Path(src).read_text())


def rows_from_dump(weeks: list[dict]):
    for week in weeks:
        d = date.fromisoformat(week["date"])
        for r in week["data"]:
            yield r["song"], r["artist"], int(r["this_week"]), d


def run(session: Session, source: str | Path | None = None) -> int:
    weeks = load(source)
    entries = list(aggregate_weeks(rows_from_dump(weeks)).values())
    return upsert_entries(session, Region.US, entries)
