<script>
  import { API_BASE, sessionId, items, currentPage } from "../lib/stores.js";

  let dragging = false;
  let localFiles = [];

  function handleDragOver(e) {
    e.preventDefault();
    dragging = true;
  }
  function handleDragLeave(e) {
    e.preventDefault();
    dragging = false;
  }
  function handleDrop(e) {
    e.preventDefault();
    dragging = false;
    const files = [...e.dataTransfer.files];
    localFiles = files;
  }
  function handleInput(e) {
    localFiles = [...e.target.files];
  }

  async function uploadNow() {
    const base = $API_BASE;
    const form = new FormData();
    localFiles.forEach(f => form.append("files", f));
    const resp = await fetch(`${base}/upload`, { method: "POST", body: form });
    const data = await resp.json();
    sessionId.set(data.session_id);
    items.set(data.items);
    currentPage.set("Galería");
  }
</script>

<div class="card">
  <h2 class="text-xl font-medium mb-2">1. Carga de imágenes</h2>
  <div 
    class="border-2 border-dashed rounded-2xl p-8 text-center bg-white"
    class:bg-gray-100={dragging}
    role="button"
    aria-label="Zona para arrastrar y soltar archivos"
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop={handleDrop}
  >
    <p class="mb-2">Arrastra y suelta aquí, o elige archivos</p>
    <label for="fileInput" class="sr-only">Seleccionar archivos</label>
    <input id="fileInput" type="file" multiple accept=".jpg,.jpeg,.png,.tif,.tiff" on:change={handleInput} />
  </div>

  {#if localFiles.length}
    <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
      {#each localFiles as f}
        <div class="card">
          <div class="text-sm truncate">{f.name}</div>
        </div>
      {/each}
    </div>
    <div class="mt-3">
      <button class="btn" on:click={uploadNow}>Subir y continuar →</button>
    </div>
  {/if}
</div>
