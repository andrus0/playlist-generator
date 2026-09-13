<script lang="ts">
  import { onMount } from 'svelte';
  import { replaceState } from '$app/navigation';
  import {
    api,
    defaultQuery,
    fromParams,
    playlistText,
    toParams,
    type Meta,
    type Playlist,
    type Query
  } from '$lib/api';
  import Segmented from '$lib/Segmented.svelte';
  import ArtistPicker from '$lib/ArtistPicker.svelte';

  let meta = $state<Meta | null>(null);
  let q = $state<Query>(defaultQuery());
  let playlist = $state<Playlist | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let copied = $state<string | null>(null);

  const levels = [
    { value: 'no1', label: 'Nr. 1' },
    { value: 'top10', label: 'Top 10' },
    { value: 'top40', label: 'Top 40' },
    { value: 'all', label: 'Alle' }
  ] as const;
  const ohws = [
    { value: 'any', label: 'Egal' },
    { value: 'only', label: 'Nur', hint: 'Nur Artists mit genau einem Top-40-Hit' },
    { value: 'exclude', label: 'Ohne' }
  ] as const;
  const types = [
    { value: 'any', label: 'Egal' },
    { value: 'person', label: 'Solo' },
    { value: 'group', label: 'Band' },
    { value: 'duo', label: 'Duo' }
  ] as const;
  const sorts = [
    { value: 'random', label: 'Zufällig' },
    { value: 'success', label: 'Chart-Erfolg' },
    { value: 'year', label: 'Jahr aufsteigend' },
    { value: 'year_desc', label: 'Jahr absteigend' }
  ] as const;

  function toggle(list: string[], v: string): string[] {
    return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
  }

  async function generate(newSeed = false) {
    if (newSeed) q.seed = null;
    loading = true;
    error = null;
    try {
      playlist = await api.playlist(q);
      q.seed = playlist.seed;
      replaceState(`?${toParams(q)}`, {});
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  function reset() {
    q = defaultQuery();
    playlist = null;
    replaceState('?', {});
  }

  async function copy(text: string, what: string) {
    try {
      await navigator.clipboard.writeText(text);
      copied = what;
      setTimeout(() => (copied = null), 1600);
    } catch {
      error = 'Kopieren nicht möglich – bitte manuell markieren.';
    }
  }

  onMount(async () => {
    try {
      meta = await api.meta();
    } catch (e) {
      error = `Backend nicht erreichbar: ${(e as Error).message}`;
      return;
    }
    const params = new URLSearchParams(location.search);
    if ([...params.keys()].length) {
      q = fromParams(params);
      generate();
    }
  });

  const shareUrl = $derived(playlist ? `${location.origin}${location.pathname}?${toParams(q)}` : '');
  const regionsSelected = $derived(q.regions.length ? q.regions : (meta?.regions.map((r) => r.code) ?? []));
</script>

<svelte:head>
  <title>{playlist ? `${playlist.name} · ` : ''}Playlist Generator</title>
</svelte:head>

<header>
  <div class="wrap">
    <a class="brand" href="/" onclick={(e) => { e.preventDefault(); reset(); }}>
      <svg viewBox="0 0 64 64" width="28" height="28" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#1f1d2b"/><path d="M24 18v22.5a7.5 7.5 0 1 1-4-6.6V14l24-4v26.5a7.5 7.5 0 1 1-4-6.6V17.6z" fill="#f4b942"/></svg>
      <h1>Playlist Generator</h1>
    </a>
    {#if meta}
      <p class="stats">
        {meta.songs.toLocaleString('de-AT')} Chart-Hits · {meta.artists.toLocaleString('de-AT')} Artists
        {#if meta.imports.length}
          · Stand {new Date(meta.imports.map((i) => i.latest_chart_date ?? '').sort().at(-1) ?? '').toLocaleDateString('de-AT')}
        {/if}
      </p>
    {/if}
  </div>
</header>

<main class="wrap">
  <section class="filters card">
    <h2>Filter</h2>

    {#if meta}
      <div class="field">
        <span class="label">Dekaden</span>
        <div class="chips">
          {#each meta.decades as d (d)}
            <button
              type="button"
              class="chip"
              class:active={q.decades.includes(d)}
              aria-pressed={q.decades.includes(d)}
              onclick={() => (q.decades = toggle(q.decades, d))}>{d.replace('s', 'er')}</button
            >
          {/each}
        </div>
      </div>

      <div class="field">
        <span class="label">Charts</span>
        <div class="regions">
          {#each meta.regions as r (r.code)}
            <label class:disabled={!r.songs} title={r.songs ? '' : 'Noch keine Daten importiert'}>
              <input
                type="checkbox"
                disabled={!r.songs}
                checked={regionsSelected.includes(r.code)}
                onchange={() => {
                  const all = meta!.regions.filter((x) => x.songs).map((x) => x.code);
                  const next = toggle(regionsSelected, r.code);
                  q.regions = next.length === all.length || next.length === 0 ? [] : next;
                }}
              />
              <span>{r.name}</span>
              {#if r.coverage === 'no1' && r.songs}
                <em class="tag" title="Für diese Charts sind nur die Nummer-1-Hits verfügbar">nur Nr. 1</em>
              {/if}
              <small>{r.songs ? r.songs.toLocaleString('de-AT') : 'bald'}</small>
            </label>
          {/each}
        </div>
      </div>
    {/if}

    <div class="field">
      <span class="label">Chart-Platzierung</span>
      <Segmented options={levels} bind:value={q.level} name="Chart-Platzierung" />
    </div>

    <div class="field">
      <span class="label">One-Hit-Wonder</span>
      <Segmented options={ohws} bind:value={q.ohw} name="One-Hit-Wonder" />
      {#if q.ohw !== 'any'}
        <small class="muted">Genau ein Top-40-Hit in den US-/UK-Charts, sonst keiner.</small>
      {/if}
    </div>

    <div class="field">
      <span class="label">Artist-Typ</span>
      <Segmented options={types} bind:value={q.artist_type} name="Artist-Typ" />
    </div>

    {#if meta?.genres.length}
      <div class="field">
        <span class="label">Genre</span>
        <div class="chips">
          {#each meta.genres as g (g.slug)}
            <button
              type="button"
              class="chip"
              class:active={q.genres.includes(g.slug)}
              aria-pressed={q.genres.includes(g.slug)}
              onclick={() => (q.genres = toggle(q.genres, g.slug))}>{g.name}</button
            >
          {/each}
        </div>
      </div>
    {/if}

    <div class="field">
      <span class="label">Bestimmte Artists</span>
      <ArtistPicker bind:selected={q.artists} />
    </div>

    <div class="row">
      <div class="field">
        <label class="label" for="count">Anzahl Songs: <strong>{q.count}</strong></label>
        <input id="count" type="range" min="5" max="200" step="5" bind:value={q.count} />
      </div>
      <div class="field small">
        <label class="label" for="mpa">Max. pro Artist</label>
        <input id="mpa" type="number" min="1" max="200" bind:value={q.max_per_artist} />
      </div>
    </div>

    <div class="field">
      <label class="label" for="sort">Sortierung</label>
      <select id="sort" bind:value={q.sort}>
        {#each sorts as s (s.value)}
          <option value={s.value}>{s.label}</option>
        {/each}
      </select>
    </div>

    <div class="actions">
      <button class="primary" type="button" disabled={loading || !meta} onclick={() => generate(true)}>
        {loading ? 'Generiere …' : playlist ? 'Neu mischen' : 'Playlist generieren'}
      </button>
      <button class="ghost" type="button" onclick={reset}>Zurücksetzen</button>
    </div>
  </section>

  <section class="result">
    {#if error}
      <div class="card error">{error}</div>
    {/if}

    {#if playlist}
      <div class="card">
        <div class="result-head">
          <div>
            <h2>{playlist.name}</h2>
            <p class="muted">
              {playlist.tracks.length} von {playlist.total_matching.toLocaleString('de-AT')} passenden Songs
              · Seed {playlist.seed}
            </p>
          </div>
          <div class="toolbar">
            <button type="button" onclick={() => copy(playlistText(playlist!), 'list')}>
              {copied === 'list' ? '✓ Kopiert' : 'Kopieren'}
            </button>
            <button type="button" onclick={() => copy(shareUrl, 'link')}>
              {copied === 'link' ? '✓ Kopiert' : 'Link teilen'}
            </button>
            <a class="btn" href={api.downloadUrl(q, 'txt')} download>.txt</a>
            <a class="btn" href={api.downloadUrl(q, 'csv')} download>.csv</a>
            <a class="btn" href={api.downloadUrl(q, 'm3u')} download>.m3u</a>
          </div>
        </div>

        {#if playlist.tracks.length === 0}
          <p class="empty">Keine Songs gefunden – Filter etwas lockern.</p>
        {:else}
          <ol class="tracks">
            {#each playlist.tracks as t (t.position)}
              <li>
                <span class="pos">{t.position}</span>
                <span class="track">
                  <span class="title">{t.title}</span>
                  <span class="artist">{t.artist}</span>
                </span>
                <span class="year">{t.year}</span>
                <span class="peaks">
                  {#each t.charts as c (c.region)}
                    <span class="peak" class:one={c.peak === 1} title="{c.region}: Platz {c.peak}, {c.weeks} Wochen"
                      >{c.region} #{c.peak}</span
                    >
                  {/each}
                </span>
              </li>
            {/each}
          </ol>
        {/if}
      </div>
    {:else if !error}
      <div class="card hint">
        <h2>Deine Playlist aus echten Chart-Hits</h2>
        <p>
          Wähle links Dekaden, Chart-Platzierung, One-Hit-Wonder, Genre oder bestimmte Artists –
          und bekomme eine Trackliste zum Kopieren oder Herunterladen. Jede Liste hat einen Seed,
          über den sich der Link exakt reproduzieren lässt.
        </p>
        <p class="muted">
          Datenbasis: Billboard Hot 100 (seit 1958) und UK Official Singles Chart (seit 1952)
          komplett, dazu alle Nummer-1-Hits aus Österreich und Deutschland. Genres und
          Artist-Typen stammen von MusicBrainz.
        </p>
      </div>
    {/if}
  </section>
</main>

<footer class="wrap muted">
  <a href="https://github.com/andrus0/playlist-generator">Quellcode auf GitHub</a> ·
  <a href="/api/docs">API</a> · Daten: Billboard, Official Charts Company,
  <a href="https://de.wikipedia.org/wiki/Liste_der_Nummer-eins-Hits_in_%C3%96sterreich">Wikipedia</a> (CC BY-SA),
  <a href="https://musicbrainz.org">MusicBrainz</a>
</footer>

<style>
  .wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 20px;
  }
  header {
    padding: 22px 0 6px;
  }
  header .wrap {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: inherit;
    text-decoration: none;
  }
  .brand h1 {
    font-size: 1.35rem;
    letter-spacing: -0.01em;
  }
  .stats,
  .muted {
    color: var(--muted);
    font-size: 0.9rem;
    margin: 0;
  }
  main {
    display: grid;
    grid-template-columns: minmax(300px, 380px) 1fr;
    gap: 20px;
    padding-top: 16px;
    padding-bottom: 32px;
    align-items: start;
  }
  @media (max-width: 800px) {
    main {
      grid-template-columns: 1fr;
    }
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
  }
  .filters {
    display: grid;
    gap: 18px;
    position: sticky;
    top: 16px;
  }
  @media (max-width: 800px) {
    .filters {
      position: static;
    }
  }
  .filters h2,
  .result h2 {
    font-size: 1.05rem;
  }
  .field {
    display: grid;
    gap: 8px;
  }
  .label {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 999px;
    padding: 5px 12px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.15s;
  }
  .chip:hover {
    border-color: var(--accent);
  }
  .chip.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-text);
    font-weight: 600;
  }
  .regions {
    display: grid;
    gap: 6px;
  }
  .regions label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.92rem;
    cursor: pointer;
  }
  .regions label.disabled {
    color: var(--muted);
    cursor: not-allowed;
  }
  .regions small {
    margin-left: auto;
    color: var(--muted);
  }
  .tag {
    font-style: normal;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--muted);
    white-space: nowrap;
  }
  .regions input {
    accent-color: var(--accent);
  }
  .row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 14px;
    align-items: end;
  }
  .field.small input {
    width: 84px;
  }
  input[type='number'],
  select {
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
  }
  input[type='range'] {
    accent-color: var(--accent);
    width: 100%;
  }
  .actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  .primary {
    flex: 1;
    background: var(--accent);
    color: var(--accent-text);
    border: 0;
    border-radius: 10px;
    padding: 12px 18px;
    font-weight: 700;
    cursor: pointer;
    transition: filter 0.15s;
  }
  .primary:hover:not(:disabled) {
    filter: brightness(1.06);
  }
  .primary:disabled {
    opacity: 0.6;
    cursor: wait;
  }
  .ghost {
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    cursor: pointer;
  }
  .error {
    border-color: var(--danger);
    color: var(--danger);
    margin-bottom: 16px;
  }
  .hint p {
    margin: 10px 0 0;
  }
  .result-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    align-items: flex-start;
    margin-bottom: 14px;
  }
  .toolbar {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .toolbar button,
  .btn {
    border: 1px solid var(--border);
    background: var(--surface-2);
    border-radius: 8px;
    padding: 7px 12px;
    cursor: pointer;
    font-size: 0.88rem;
    color: inherit;
    text-decoration: none;
  }
  .toolbar button:hover,
  .btn:hover {
    border-color: var(--accent);
  }
  .tracks {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .tracks li {
    display: grid;
    grid-template-columns: 2.2em 1fr auto auto;
    gap: 12px;
    align-items: center;
    padding: 9px 6px;
    border-top: 1px solid var(--border);
  }
  .tracks li:hover {
    background: var(--surface-2);
  }
  .pos {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .track {
    display: grid;
    min-width: 0;
  }
  .title {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .artist {
    color: var(--muted);
    font-size: 0.9rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .year {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    font-size: 0.9rem;
  }
  .peaks {
    display: flex;
    gap: 4px;
  }
  .peak {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--muted);
    white-space: nowrap;
  }
  .peak.one {
    background: var(--accent-soft);
    color: var(--accent);
  }
  @media (max-width: 560px) {
    .tracks li {
      grid-template-columns: 2em 1fr auto;
    }
    .peaks {
      display: none;
    }
  }
  .empty {
    color: var(--muted);
    text-align: center;
    padding: 30px 0;
  }
  footer {
    padding: 0 20px 28px;
    font-size: 0.85rem;
  }
</style>
