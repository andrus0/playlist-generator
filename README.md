# Playlist Generator

Filter-based playlist generator built on real chart data. Pick decades, chart
position (No. 1 / Top 10 / Top 40), one-hit-wonders, genre, band vs. solo
artist or specific artists — get a track list as text, `.txt`, `.csv` or
`.m3u`. Every playlist has a seed, so a share link reproduces it exactly.

Live: https://playlist.kingsyard.at (soon)

## Data

| Region | Source | Status |
|---|---|---|
| US | Billboard Hot 100, 1958 → today ([open dataset](https://github.com/mhollingshead/billboard-hot-100)) | ✅ ~32,700 songs |
| UK | Official Singles Chart | planned |
| AT | Ö3 Austria Top 40 (number ones / year-end via Wikipedia) | planned |
| DE | Offizielle Deutsche Charts (number ones / year-end via Wikipedia) | planned |
| Genres, artist type | MusicBrainz | planned |

Chart runs are stored aggregated per song and region (peak, weeks, first/last
week). *One-hit-wonder* = an artist with exactly one Top-40 song in the
selected regions.

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

The app listens on `127.0.0.1:8080`; terminate TLS with the reverse proxy
already running on the host.

## Configuration

All settings are environment variables prefixed `PLG_` (see `backend/app/config.py`):
`DATABASE_URL`, `RATE_LIMIT` (default `60/minute` per IP), `AUTO_IMPORT`,
`MAX_COUNT`, `CORS_ORIGINS`, `STATIC_DIR`.
