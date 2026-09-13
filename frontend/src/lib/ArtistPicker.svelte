<script lang="ts">
  import { api, type ArtistHit } from './api';

  let { selected = $bindable() }: { selected: string[] } = $props();
  let query = $state('');
  let hits = $state<ArtistHit[]>([]);
  let open = $state(false);
  let timer: ReturnType<typeof setTimeout>;

  function search() {
    clearTimeout(timer);
    if (query.trim().length < 2) {
      hits = [];
      return;
    }
    timer = setTimeout(async () => {
      try {
        hits = (await api.artists(query.trim())).filter((h) => !selected.includes(h.name));
        open = true;
      } catch {
        hits = [];
      }
    }, 180);
  }

  function add(name: string) {
    if (!selected.includes(name)) selected = [...selected, name];
    query = '';
    hits = [];
    open = false;
  }

  function remove(name: string) {
    selected = selected.filter((s) => s !== name);
  }

  function onkey(e: KeyboardEvent) {
    if (e.key === 'Enter' && hits.length) {
      e.preventDefault();
      add(hits[0].name);
    } else if (e.key === 'Escape') {
      open = false;
    }
  }
</script>

<div class="picker">
  {#if selected.length}
    <div class="chips">
      {#each selected as name (name)}
        <span class="chip"
          >{name}
          <button type="button" aria-label="{name} entfernen" onclick={() => remove(name)}>×</button></span
        >
      {/each}
    </div>
  {/if}
  <div class="input-wrap">
    <input
      type="search"
      placeholder="Artist suchen …"
      bind:value={query}
      oninput={search}
      onkeydown={onkey}
      onfocus={() => hits.length && (open = true)}
      onblur={() => setTimeout(() => (open = false), 150)}
      autocomplete="off"
    />
    {#if open && hits.length}
      <ul class="dropdown" role="listbox">
        {#each hits as h (h.id)}
          <li>
            <button type="button" onmousedown={() => add(h.name)}>
              <span>{h.name}</span>
              <small>{h.songs} {h.songs === 1 ? 'Song' : 'Songs'}</small>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .picker {
    display: grid;
    gap: 8px;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--accent-soft);
    border-radius: 999px;
    padding: 3px 6px 3px 10px;
    font-size: 0.9rem;
  }
  .chip button {
    border: 0;
    background: transparent;
    cursor: pointer;
    line-height: 1;
    padding: 2px 5px;
    border-radius: 999px;
    color: var(--muted);
  }
  .chip button:hover {
    color: var(--danger);
  }
  .input-wrap {
    position: relative;
  }
  input {
    width: 100%;
    padding: 9px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    outline: none;
  }
  input:focus {
    border-color: var(--accent);
  }
  .dropdown {
    position: absolute;
    z-index: 10;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    margin: 0;
    padding: 4px;
    list-style: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: var(--shadow);
    max-height: 260px;
    overflow: auto;
  }
  .dropdown button {
    width: 100%;
    display: flex;
    justify-content: space-between;
    gap: 8px;
    border: 0;
    background: transparent;
    text-align: left;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
  }
  .dropdown button:hover {
    background: var(--surface-2);
  }
  small {
    color: var(--muted);
  }
</style>
