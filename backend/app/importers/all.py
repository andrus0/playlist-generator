"""Full data refresh: every chart importer, derived stats, then MusicBrainz enrichment."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from ..enrich import musicbrainz
from ..models import Region
from . import billboard, uk, wikipedia
from .base import compute_artist_stats

log = logging.getLogger(__name__)


def run(session: Session, enrich_limit: int | None = None, skip_uk: bool = False) -> None:
    year = date.today().year
    billboard.run(session)
    for region in (Region.AT, Region.DE):
        # first run: every year; later runs: only the current and previous year
        years = None if not wikipedia.has_data(session, region) else range(year - 1, year + 1)
        wikipedia.run(session, region, years)
    if not skip_uk:
        uk.run(session)
    compute_artist_stats(session)
    musicbrainz.run(session, limit=enrich_limit)
    log.info("import-all finished")
