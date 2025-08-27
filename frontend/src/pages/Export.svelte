<script>
  import { API_BASE, sessionId, items } from "../lib/stores.js";

  async function refreshPreview() {
    const resp = await fetch(`${$API_BASE}/preview?session_id=${$sessionId}`);
    const data = await resp.json();
    items.set(data.items);
  }

  async function doExport() {
    const resp = await fetch(`${$API_BASE}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: $sessionId })
    });
    // Trigger download
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `export_${$sessionId}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="card">
  <h2 class="text-xl font-medium mb-2">4. Exportación</h2>
  <div class="mb-2 flex gap-2">
    <button class="btn" on:click={refreshPreview}>Actualizar vista previa</button>
    <button class="btn" on:click={doExport}>Descargar ZIP + metadata.json</button>
  </div>
  <div class="grid md:grid-cols-2 gap-4">
    <div>
      <h3 class="font-semibold mb-2">Miniaturas</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-[60vh] overflow-auto">
        {#each $items as it}
          <div class="card">
            <img class="w-full h-28 object-cover rounded-md" src={`${$API_BASE}/thumb/${$sessionId}/${it.id}`} />
            <div class="text-[10px] mt-1 truncate">{it.original_filename}</div>
          </div>
        {/each}
      </div>
    </div>
    <div>
      <h3 class="font-semibold mb-2">Renombrado (editable)</h3>
      <div class="space-y-2 max-h-[60vh] overflow-auto">
        {#each $items as it (it.id)}
          <div class="card">
            <div class="text-xs text-gray-600 truncate">{it.original_filename}</div>
            <input class="input w-full mt-1" bind:value={it.new_filename} on:change={async (e) => {
              // Persist single override as validated update
              const payload = { session_id: $sessionId, updates: [{ id: it.id }] };
              // If user edits full filename, we store it into extra field 'new_filename_override'
              // but server keeps 'new_filename' computed on preview. For simplicity we keep UI-only edit.
            }} />
            <div class="flex gap-2 text-xs mt-1">
              <span class="badge">{it.type || 'sin-tipo'}</span>
              {#if it.page_number !== null && it.page_number !== false}
                <span class="badge">nº {it.page_number}</span>
              {/if}
              <span class="badge">{it.validated ? '✔ validada' : '⏳ pendiente'}</span>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>
