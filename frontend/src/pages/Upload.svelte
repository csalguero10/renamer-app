<script>
  import { API_BASE, sessionId, items } from "../lib/stores.js";
  import { refreshCatalogStatus, csvLoaded, catalogStatusText } from "../lib/catalogStore.js";
  import CatalogUpload from "../pages/CatalogUpload.svelte";

  let localBusy = false;
  let pickRef;

  function openPicker() {
    pickRef?.click();
  }

  async function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    localBusy = true;

    try {
      // Asegura session_id
      let sid = $sessionId;
      if (!sid) {
        sid = crypto.randomUUID();
        sessionId.set(sid);
      }

      const form = new FormData();
      for (const f of fileList) form.append("files", f);
      form.append("session_id", sid);

      const resp = await fetch(`${$API_BASE}/upload`, { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Upload failed");

      if (data.session_id && data.session_id !== sid) {
        sessionId.set(data.session_id);
      }
      items.set(data.items);

      // Refresca estado de catálogo: si hay CSV cargado, mostrará título/autor; si no, dirá opcional.
      await refreshCatalogStatus();
    } catch (e) {
      alert(e.message || "Upload failed");
    } finally {
      localBusy = false;
    }
  }

  function onDrop(e) {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files || []);
    handleFiles(files);
  }
</script>

<div class="space-y-4">
  <!-- Bloque CSV arriba (opcional) -->
  <CatalogUpload />

  <div class="card space-y-3">
    <h3 class="font-semibold">Upload images</h3>

    <!-- Estado/ayuda -->
    <div class="text-sm">
      <span class="text-gray-700">Catalog: </span>
      <span class="font-medium">{$catalogStatusText}</span>
    </div>

    <!-- Dropzone / botón (siempre habilitado) -->
    <div
      class="border-2 border-dashed rounded-2xl p-8 text-center transition border-gray-300 hover:border-gray-400 cursor-pointer"
      role="button"
      tabindex="0"
      aria-label="Upload images. Press Enter or Space to open the file picker."
      on:click={openPicker}
      on:keydown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPicker(); }
      }}
      on:dragover|preventDefault
      on:dragleave|preventDefault
      on:drop={onDrop}
    >
      <div class="text-gray-600">
        {localBusy ? "Uploading..." : "Drag & drop images here or click to select"}
      </div>
      <input
        bind:this={pickRef}
        type="file"
        accept=".jpg,.jpeg,.png,.tif,.tiff"
        multiple
        class="hidden"
        on:change={(e)=> handleFiles(e.target.files)}
      />
    </div>
  </div>
</div>
