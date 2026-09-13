<script lang="ts" generics="T extends string">
  let {
    options,
    value = $bindable(),
    name
  }: { options: readonly { value: T; label: string; hint?: string }[]; value: T; name: string } = $props();
</script>

<div class="seg" role="radiogroup" aria-label={name}>
  {#each options as o (o.value)}
    <button
      type="button"
      role="radio"
      aria-checked={value === o.value}
      class:active={value === o.value}
      title={o.hint}
      onclick={() => (value = o.value)}>{o.label}</button
    >
  {/each}
</div>

<style>
  .seg {
    display: inline-flex;
    flex-wrap: wrap;
    background: var(--surface-2);
    border-radius: 999px;
    padding: 3px;
    gap: 2px;
  }
  button {
    border: 0;
    background: transparent;
    padding: 6px 14px;
    border-radius: 999px;
    cursor: pointer;
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 500;
    transition: background 0.15s, color 0.15s;
  }
  button:hover {
    color: var(--text);
  }
  button.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  }
</style>
