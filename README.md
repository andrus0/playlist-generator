# Playlist Generator

Filter-based playlist generator built on real chart data. Pick decades, chart
position (No. 1 / Top 10 / Top 40), one-hit-wonders, genre, band vs. solo
artist or specific artists — get a track list as text, `.txt`, `.csv` or
`.m3u`. Every playlist has a seed, so a share link reproduces it exactly.

Live: https://moneymaker.kingscourt.at (soon)

## Data

| Region | Source | Coverage |
|---|---|---|
| US | Billboard Hot 100, 1958 → today ([open dataset](https://github.com/mhollingshead/billboard-hot-100)) | full chart, ~32,700 songs |
| UK | Official Singles Chart, 1952 → today (officialcharts.com, crawled at 1 req/s) | full chart |
| AT | Ö3 Austria Top 40 — number ones from [de.wikipedia](https://de.wikipedia.org/wiki/Liste_der_Nummer-eins-Hits_in_%C3%96sterreich) (CC BY-SA) | #1 hits only, 1965 → |
| DE | Offizielle Deutsche Charts — number ones from de.wikipedia (CC BY-SA) | #1 hits only, 1953 → |
| Genres, artist type, country | [MusicBrainz](https://musicbrainz.org) artist search (1 req/s, resumable) | ~16 genres |

The Austrian and German chart companies block crawlers, so those regions only
carry number-one hits. Chart runs are stored aggregated per song and region
(peak, weeks, first/last week). *One-hit-wonder* = an artist with exactly one
Top-40 song in the selected full-chart regions (US/UK).

Genres are derived from weighted MusicBrainz tags and mapped onto a fixed
taxonomy (`backend/app/enrich/genres.py`): Pop, Rock, Hip-Hop/Rap, R&B/Soul,
Dance/Electronic, Country, Disco/Funk, Metal, Punk/New Wave,
Alternative/Indie, Reggae/Dancehall, Jazz/Blues, Folk, Latin,
Schlager/Volksmusik, Soundtrack/Klassik, Gospel.

## Stack

- **Backend** `backend/` — Python 3.12, FastAPI, SQLAlchemy 2, SQLite (dev) / Postgres (prod)
- **Frontend** `frontend/` — SvelteKit 2 + Svelte 5, static build served by the backend
- **Deploy** — one image (`ghcr.io/andrus0/playlist-generator`), `docker compose` with Postgres, weekly re-import

## Development

```bash
# backend
cd backend
uv sync
uv run python -m app.cli import-billboard        # downloads ~45 MB, ~10 s
uv run python -m app.cli import-wikipedia AT     # ~1 min
uv run python -m app.cli import-wikipedia DE
uv run python -m app.cli import-uk --max-weeks 200   # full crawl ≈ 1 h; resumable
uv run python -m app.cli stats
uv run python -m app.cli enrich --limit 300      # MusicBrainz, ~1 artist/s; resumable
uv run uvicorn app.main:app --reload             # http://localhost:8000/api/docs

# frontend (proxies /api to :8000)
cd frontend
npm install
npm run dev                                      # http://localhost:5173
```

Tests and lint:

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm run check
```

## API

- `GET /api/meta` — counts, decades, regions, genres, import dates
- `GET /api/artists?q=` — artist autocomplete
- `GET /api/playlist?…` — the generator. Parameters: `decades`, `year_from`,
  `year_to`, `regions`, `level` (`no1|top10|top40|all`), `ohw`
  (`any|only|exclude`), `artist_type` (`any|person|group|duo`), `artists`,
  `genres`, `count`, `max_per_artist`, `sort`
  (`random|success|year|year_desc`), `seed`, `format` (`json|txt|csv|m3u`)
- Interactive docs at `/api/docs`

## Production

```bash
cp .env.example .env   # set POSTGRES_PASSWORD
docker compose up -d   # first start imports the data automatically (PLG_AUTO_IMPORT)
```

On an empty database the app imports Billboard and the AT/DE number ones
first (a few minutes, the app is usable meanwhile), then crawls the UK chart
and enriches artists via MusicBrainz in the background (a few hours). The
`updater` service repeats `import-all` weekly; all imports are incremental.

The app listens on `127.0.0.1:8080`; terminate TLS with the reverse proxy
already running on the host.

## Configuration

All settings are environment variables prefixed `PLG_` (see `backend/app/config.py`):
`DATABASE_URL`, `RATE_LIMIT` (default `60/minute` per IP), `AUTO_IMPORT`,
`MAX_COUNT`, `CORS_ORIGINS`, `STATIC_DIR`.
