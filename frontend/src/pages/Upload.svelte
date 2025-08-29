<script>
  import { API_BASE, sessionId, items } from "../lib/stores.js";
  import {
    refreshCatalogStatus,
    catalogStatusText,
    detectedEntry,
    detectedCatalogId,
    upsertCatalogEntry,
  } from "../lib/catalogStore.js";
  import CatalogUpload from "./CatalogUpload.svelte";
  import { get } from "svelte/store";

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

      if (data.session_id) sessionId.set(data.session_id);
      if (data.items) items.set(data.items);

      // Detecta/actualiza catálogo en UI después de subir imágenes
      await refreshCatalogStatus();

      imgSuccess = `Cargadas ${data.count ?? data.items?.length ?? 0} imágenes.`;
    } catch (e) {
      imgError = e?.message || "No se pudieron cargar las imágenes.";
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
  $: editable = {
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

  let metaMsg = "";

  function saveEditableToStore() {
    if (!editable.catalog_id) {
      metaMsg = "⚠️ Debes indicar un ID de catálogo.";
      return;
    }
    upsertCatalogEntry({
      catalog_id: editable.catalog_id,
      catalog_title: editable.catalog_title,
      catalog_author: editable.catalog_author,
      catalog_publication_year:
        editable.catalog_publication_year === "" ? null : Number(editable.catalog_publication_year),
      catalog_publisher: editable.catalog_publisher,
      catalog_place: editable.catalog_place,
      catalog_language: editable.catalog_language,
      catalog_keywords: editable.catalog_keywords,
    });
    metaMsg = "Metadatos guardados en memoria (se usarán al exportar).";
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
        Sesión: <span class="font-mono">{$sessionId || "—"}</span>
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
      aria-label="Arrastra y suelta imágenes o pulsa para seleccionar"
      on:dragover={onDragOver}
      on:dragleave={onDragLeave}
      on:drop={onDrop}
      on:keydown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.querySelector("#fileInput")?.click(); }}
    >
      <div class="text-center py-10">
        <!--<div class="text-4xl mb-2">📄</div>-->
        <div class="text-sm text-gray-600 mb-3">Arrastra tus imágenes aquí</div>
        <div>
          <label class="btn cursor-pointer" for="fileInput">Seleccionar archivos</label>
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
          <div class="mt-3 text-sm text-gray-600">Subiendo…</div>
        {/if}
      </div>
    </div>
  </div>

  <!-- BLOQUE 3: Metadatos del catálogo (editable) -->
  <div class="card">
    <h3 class="font-semibold mb-2">Resumen del catálogo detectado (editable)</h3>

    <div class="grid sm:grid-cols-2 gap-3">
      <div>
        <label class="block text-sm" for="catId">ID catálogo</label>
        <input id="catId" class="input w-full" bind:value={editable.catalog_id} placeholder="BO0624_5445" />
      </div>

      <div>
        <label class="block text-sm" for="catTitle">Título</label>
        <input id="catTitle" class="input w-full" bind:value={editable.catalog_title} placeholder="El arte de la navegación" />
      </div>

      <div>
        <label class="block text-sm" for="catAuthor">Autor</label>
        <input id="catAuthor" class="input w-full" bind:value={editable.catalog_author} placeholder="Juan Perez" />
      </div>

      <div>
        <label class="block text-sm" for="catYear">Año de publicación</label>
        <input id="catYear" type="number" class="input w-full" bind:value={editable.catalog_publication_year} placeholder="1985" />
      </div>

      <div>
        <label class="block text-sm" for="catPublisher">Publisher</label>
        <input id="catPublisher" class="input w-full" bind:value={editable.catalog_publisher} placeholder="Editorial X" />
      </div>

      <div>
        <label class="block text-sm" for="catPlace">Place</label>
        <input id="catPlace" class="input w-full" bind:value={editable.catalog_place} placeholder="Ciudad / País" />
      </div>

      <div>
        <label class="block text-sm" for="catLanguage">Language</label>
        <input id="catLanguage" class="input w-full" bind:value={editable.catalog_language} placeholder="Español" />
      </div>

      <div class="sm:col-span-2">
        <label class="block text-sm" for="catKeywords">Keywords</label>
        <input id="catKeywords" class="input w-full" bind:value={editable.catalog_keywords} placeholder="palabra1, palabra2, ..." />
      </div>
    </div>

    <div class="mt-3 flex gap-2">
      <button class="btn" type="button" on:click={saveEditableToStore}>
        Guardar cambios en memoria
      </button>
      <button class="btn" type="button" on:click={refreshCatalogStatus}>
        Volver a cargar desde servidor
      </button>
    </div>

    {#if metaMsg}
      <p class="text-xs text-gray-600 mt-2">{metaMsg}</p>
    {/if}
  </div>
</div>
