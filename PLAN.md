# Roadmap

Decisions from the initial planning session (2026-09-13):

- Output is **text only** for now (no Spotify/Apple integration); a provider
  interface for exports comes later.
- Generation is **filter-based** (charts, decades, one-hit-wonder, genre,
  artist type, specific artists), deterministic via seed.
- **Public** app, no login, per-IP rate limiting.
- Data: all of Billboard (US), UK, AT, DE + MusicBrainz enrichment; Claude as
  an optional "creative mode" later.
- Domain `playlist.kingsyard.at`, deployed in new containers on the existing
  Ventuscloud host (next to buddyknifes), behind its reverse proxy.

## Phase 1 — foundation ✅
- [x] Repo, backend (FastAPI + SQLAlchemy), schema, Billboard import
- [x] Filter API, seeded ordering, per-artist cap, txt/csv/m3u export
- [x] SvelteKit frontend with share links
- [x] Dockerfile, docker-compose (app + Postgres + weekly updater), CI → GHCR

## Phase 2 — more data ✅
- [x] UK Official Singles Chart importer (officialcharts.com, incremental crawl)
- [x] AT / DE: number-one lists from Wikipedia (chart companies block crawlers)
- [x] MusicBrainz enrichment: artist type (person/group/duo), country, genres
- [x] Genre filter (multi-select) and region coverage hints in the UI
- [ ] Song length (would need ~1 MusicBrainz recording lookup per song) → later

## Phase 3 — deploy
- [ ] Server access (Ventuscloud host, SSH port TBD)
- [ ] Reverse proxy entry for playlist.kingsyard.at + TLS
- [ ] DNS record, GitHub Actions deploy job (`docker compose pull && up -d`)

## Phase 4 — creative mode
- [ ] Free-text prompt → Claude proposes tracks → validated against the DB
- [ ] Daily quota for the creative mode

## Later
- [ ] Spotify / Apple Music / YouTube Music export via provider interface
