<script>
  import { get } from "svelte/store";

  // Estado global
  import { API_BASE, sessionId, items } from "../lib/stores.js";

  // Catálogo (estado y helpers)
  import {
    refreshCatalogStatus,
    catalogStatusText,
    detectedEntry,
    detectedCatalogId,
    upsertCatalogEntry,
    csvLoaded
  } from "../lib/catalogStore.js";

  // Componente de CSV (Bloque 1)
  import CatalogUpload from "./CatalogUpload.svelte";

  // Etiqueta de sesión corta
  import { sessionLabel, fetchSessionLabel } from "../lib/storesSessionLabel.js";
  import { niceSession } from "../lib/utils/niceSession.js";

  // ===== Imágenes (Bloque 2) =====
  let dropping = false;
  let uploading = false;
  let imgError = "";
  let imgSuccess = "";

  async function doUpload(files) {
    if (!files || !files.length) return;
    imgError = "";
    imgSuccess = "";
    uploading = true;

    try {
      const form = new FormData();
      form.append("session_id", get(sessionId) || "");
      for (const f of files) form.append("files", f);

      const resp = await fetch(`${get(API_BASE)}/upload`, { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.error || "Upload failed");

      if (data.session_id) {
        sessionId.set(data.session_id);
        fetchSessionLabel(get(API_BASE), data.session_id);
      }
      if (data.items) items.set(data.items);

      await refreshCatalogStatus();
      imgSuccess = `Uploaded ${data.count ?? data.items?.length ?? 0} images.`;
        } catch (e) {
      imgError = e?.message || "Images could not be uploaded.";
    } finally {
      uploading = false;
    }
  }

  function onDragOver(e) { e.preventDefault(); dropping = true; }
  function onDragLeave(e) { e.preventDefault(); dropping = false; }
  function onDrop(e) {
    e.preventDefault();
    dropping = false;
    const files = Array.from(e.dataTransfer?.files || []);
    doUpload(files);
  }

  // ===== Metadatos del catálogo (Bloque 3) =====
  let editable = {
    catalog_id: "",
    catalog_title: "",
    catalog_author: "",
    catalog_publication_year: "",
    catalog_publisher: "",
    catalog_place: "",
    catalog_language: "",
    catalog_keywords: "",
  };

  // Modo edición / lectura
  let isEditing = false; // cambia a true si quieres iniciar editable
  let _snapshot = null;  // para cancelar cambios

  // Sembrar SOLO cuando NO se edita (evita que se pise lo que escribes)
  $: if (!isEditing) {
    editable = {
      catalog_id: $detectedEntry?.catalog_id || $detectedCatalogId || "",
      catalog_title: $detectedEntry?.catalog_title || "",
      catalog_author: $detectedEntry?.catalog_author || "",
      catalog_publication_year:
        $detectedEntry?.catalog_publication_year ?? "",
      catalog_publisher: $detectedEntry?.catalog_publisher || "",
      catalog_place: $detectedEntry?.catalog_place || "",
      catalog_language: $detectedEntry?.catalog_language || "",
      catalog_keywords: $detectedEntry?.catalog_keywords || "",
    };
  }

  function startEditing() {
    _snapshot = JSON.parse(JSON.stringify(editable));
    isEditing = true;
  }

  function cancelEditing() {
    if (_snapshot) editable = _snapshot;
    isEditing = false;
  }

  function saveEditableToStore() {
  upsertCatalogEntry({
    catalog_id: editable.catalog_id, // ID no editable
    catalog_title: editable.catalog_title,
    catalog_author: editable.catalog_author,
    catalog_publication_year:
      editable.catalog_publication_year === "" ? null : Number(editable.catalog_publication_year),
    catalog_publisher: editable.catalog_publisher,
    catalog_place: editable.catalog_place,
    catalog_language: editable.catalog_language,
    catalog_keywords: editable.catalog_keywords,
  });
  isEditing = false;
  // Opcional: refrescar texto/derivados que dependan del backend (no pisa overrides)
  refreshCatalogStatus().catch(()=>{});
}

</script>

<!-- CONTENEDOR GLOBAL, orden secuencial -->
<div class="max-w-[900px] mx-auto p-4 space-y-6">

  <!-- BLOQUE 1: CSV (componente) -->
  <CatalogUpload />

  <!-- BLOQUE 2: Carga de imágenes (centrado) -->
  <div class="card">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">Upload images</h2>
      <div class="text-sm text-gray-600">
        Sesión:
        <span class="font-mono">
          {niceSession($sessionId, $sessionLabel) || "—"}
        </span>
      </div>
    </div>

    <div class="mt-2 text-sm text-gray-700">
      Catalog: {$catalogStatusText}
    </div>

    {#if imgError}
      <div class="mt-2 text-sm text-red-600">{imgError}</div>
    {/if}
    {#if imgSuccess}
      <div class="mt-2 text-sm text-green-700">{imgSuccess}</div>
    {/if}

    <div
      class={`mt-4 card border-dashed border-2 ${dropping ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}`}
      role="button"
      tabindex="0"
      aria-label="Drag and drop images or click to select"
      on:dragover={onDragOver}
      on:dragleave={onDragLeave}
      on:drop={onDrop}
      on:keydown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.querySelector("#fileInput")?.click(); }}
    >
      <div class="text-center py-10">
        <div class="text-sm text-gray-600 mb-3">Drag your images here</div>
        <div>
          <label class="btn cursor-pointer" for="fileInput">Select files</label>
          <input
            id="fileInput"
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.tif,.tiff"
            class="sr-only"
            on:change={(e) => doUpload(Array.from(e.currentTarget.files || []))}
          />
        </div>
        {#if uploading}
          <div class="mt-3 text-sm text-gray-600">Uploading…</div>
        {/if}
      </div>
    </div>
  </div>

  <!-- BLOQUE 3: Metadatos del catálogo (modo lectura/edición) -->
  <div class="card">
    <div class="flex items-center justify-between">
      <h3 class="font-semibold">Detected catalog summary (editable)</h3>

      {#if !isEditing}
        <button class="btn btn-outline" type="button" on:click={startEditing}>Edit</button>
      {:else}
        <div class="ml-auto flex gap-2">
          <button class="btn btn-outline" type="button" on:click={cancelEditing}>Cancel</button>
          <button class="btn" type="button" on:click={saveEditableToStore}>Save changes</button>
        </div>
      {/if}
    </div>

    <div class="grid sm:grid-cols-2 gap-3 mt-2">
      <div>
        <label class="block text-sm" for="catId">ID catalog</label>
        <!-- SIEMPRE deshabilitado -->
        <input id="catId" class="input w-full" bind:value={editable.catalog_id} disabled placeholder="BO0624_5445" />
      </div>

      <div>
        <label class="block text-sm" for="catTitle">Title</label>
        <input id="catTitle" class="input w-full" bind:value={editable.catalog_title} placeholder="El arte de la navegación" readonly={!isEditing} />
      </div>

      <div>
        <label class="block text-sm" for="catAuthor">Author</label>
        <input id="catAuthor" class="input w-full" bind:value={editable.catalog_author} placeholder="Juan Perez" readonly={!isEditing} />
      </div>

      <div>
        <label class="block text-sm" for="catYear">Publication year</label>
        <input id="catYear" type="number" class="input w-full" bind:value={editable.catalog_publication_year} placeholder="1985" readonly={!isEditing} />
      </div>

      <div>
        <label class="block text-sm" for="catPublisher">Publisher</label>
        <input id="catPublisher" class="input w-full" bind:value={editable.catalog_publisher} placeholder="Editorial X" readonly={!isEditing} />
      </div>

      <div>
        <label class="block text-sm" for="catPlace">Place</label>
        <input id="catPlace" class="input w-full" bind:value={editable.catalog_place} placeholder="Ciudad / País" readonly={!isEditing} />
      </div>

      <div>
        <label class="block text-sm" for="catLanguage">Language</label>
        <input id="catLanguage" class="input w-full" bind:value={editable.catalog_language} placeholder="Español" readonly={!isEditing} />
      </div>

      <div class="sm:col-span-2">
        <label class="block text-sm" for="catKeywords">Keywords</label>
        <input id="catKeywords" class="input w-full" bind:value={editable.catalog_keywords} placeholder="palabra1, palabra2, ..." readonly={!isEditing} />
      </div>
    </div>
  </div>
</div>
