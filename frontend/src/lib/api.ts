export type Meta = {
  songs: number;
  artists: number;
  decades: string[];
  regions: { code: string; name: string; songs: number; coverage: 'full' | 'no1' }[];
  genres: { slug: string; name: string; songs: number }[];
  imports: { source: string; finished_at: string; latest_chart_date: string | null }[];
};

export type Query = {
  decades: string[];
  regions: string[];
  level: 'no1' | 'top10' | 'top40' | 'all';
  ohw: 'any' | 'only' | 'exclude';
  artist_type: 'any' | 'person' | 'group' | 'duo';
  artists: string[];
  genres: string[];
  count: number;
  max_per_artist: number;
  sort: 'random' | 'success' | 'year' | 'year_desc';
  seed: number | null;
};

export type Track = {
  position: number;
  title: string;
  artist: string;
  year: number;
  charts: { region: string; peak: number; weeks: number; year: number }[];
};

export type Playlist = {
  name: string;
  seed: number;
  total_matching: number;
  tracks: Track[];
  query: Query;
};

export type ArtistHit = { id: number; name: string; type: string; songs: number };

export const defaultQuery = (): Query => ({
  decades: [],
  regions: [],
  level: 'all',
  ohw: 'any',
  artist_type: 'any',
  artists: [],
  genres: [],
  count: 30,
  max_per_artist: 3,
  sort: 'random',
  seed: null
});

/** Query → URLSearchParams, omitting defaults so share links stay short. */
export function toParams(q: Query, format?: string): URLSearchParams {
  const d = defaultQuery();
  const p = new URLSearchParams();
  if (q.decades.length) p.set('decades', q.decades.join(','));
  if (q.regions.length) p.set('regions', q.regions.join(','));
  if (q.level !== d.level) p.set('level', q.level);
  if (q.ohw !== d.ohw) p.set('ohw', q.ohw);
  if (q.artist_type !== d.artist_type) p.set('artist_type', q.artist_type);
  if (q.artists.length) p.set('artists', q.artists.join(','));
  if (q.genres.length) p.set('genres', q.genres.join(','));
  if (q.count !== d.count) p.set('count', String(q.count));
  if (q.max_per_artist !== d.max_per_artist) p.set('max_per_artist', String(q.max_per_artist));
  if (q.sort !== d.sort) p.set('sort', q.sort);
  if (q.seed !== null) p.set('seed', String(q.seed));
  if (format) p.set('format', format);
  return p;
}

export function fromParams(p: URLSearchParams): Query {
  const q = defaultQuery();
  const list = (k: string) => (p.get(k) ?? '').split(',').filter(Boolean);
  q.decades = list('decades');
  q.regions = list('regions');
  q.artists = list('artists');
  q.genres = list('genres');
  q.level = (p.get('level') as Query['level']) ?? q.level;
  q.ohw = (p.get('ohw') as Query['ohw']) ?? q.ohw;
  q.artist_type = (p.get('artist_type') as Query['artist_type']) ?? q.artist_type;
  q.sort = (p.get('sort') as Query['sort']) ?? q.sort;
  if (p.get('count')) q.count = Number(p.get('count'));
  if (p.get('max_per_artist')) q.max_per_artist = Number(p.get('max_per_artist'));
  if (p.get('seed')) q.seed = Number(p.get('seed'));
  return q;
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const body = await r.json();
      if (body.detail) msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      if (body.error) msg = body.error;
    } catch {
      /* not json */
    }
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  meta: () => get<Meta>('/api/meta'),
  artists: (q: string) => get<ArtistHit[]>(`/api/artists?q=${encodeURIComponent(q)}`),
  playlist: (q: Query) => get<Playlist>(`/api/playlist?${toParams(q)}`),
  downloadUrl: (q: Query, format: string) => `/api/playlist?${toParams(q, format)}`
};

export function playlistText(p: Playlist): string {
  const w = String(p.tracks.length).length;
  return p.tracks
    .map((t) => `${String(t.position).padStart(w)}. ${t.artist} – ${t.title} (${t.year})`)
    .join('\n');
}
