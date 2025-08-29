<script>
  import { API_BASE, sessionId } from "../lib/stores.js";
  import {
    catalogMap,
    detectedCatalogId,
    detectedEntry,
    csvLoaded,
    catalogStatusText,
    uploadCatalogCSV,
    refreshCatalogStatus,
    upsertCatalogEntry
  } from "../lib/catalogStore.js";
  import { get } from "svelte/store";

  let file = null;
  let uploading = false;
  let errorMsg = "";
  let successMsg = "";

  // Modelo editable (por si el usuario quiere corregir campos aquí mismo).
  // Si hay detectedEntry, se pre-llena automáticamente.
  $: editable = {
    catalog_id: $detectedEntry?.catalog_id || $detectedCatalogId || "",
    catalog_title: $detectedEntry?.catalog_title || "",
    catalog_author: $detectedEntry?.catalog_author || "",
    catalog_publication_year: $detectedEntry?.catalog_publication_year ?? "",
    catalog_publisher: $detectedEntry?.catalog_publisher || "",
    catalog_place: $detectedEntry?.catalog_place || "",
    catalog_language: $detectedEntry?.catalog_language || "",
    catalog_keywords: $detectedEntry?.catalog_keywords || "",
  };

  async function handleUpload() {
    errorMsg = "";
    successMsg = "";
    if (!file) { errorMsg = "Selecciona un archivo CSV."; return; }
    try {
      uploading = true;
      const res = await uploadCatalogCSV(file);
      successMsg = `CSV cargado. Entradas: ${res.loaded ?? "?"}.` + (res.detected_id ? ` (ID detectado: ${res.detected_id})` : "");
      await refreshCatalogStatus();
    } catch (e) {
      errorMsg = e?.message || "Error al subir el CSV.";
    } finally {
      uploading = false;
    }
  }

  async function handleRefresh() {
    errorMsg = "";
    successMsg = "";
    try {
      await refreshCatalogStatus();
      successMsg = "Estado actualizado.";
    } catch (e) {
      errorMsg = "No se pudo actualizar el estado.";
    }
  }

  function saveEditableToStore() {
    // Guarda el formulario editable en el store de catálogo (no toca backend).
    // Esto permitirá que aparezca en Export como catálogo actual.
    if (!editable.catalog_id) {
      errorMsg = "El campo 'ID catálogo' es obligatorio para guardar cambios.";
      return;
    }
    upsertCatalogEntry({
      catalog_id: editable.catalog_id,
      catalog_title: editable.catalog_title,
      catalog_author: editable.catalog_author,
      catalog_publication_year: editable.catalog_publication_year === "" ? null : Number(editable.catalog_publication_year),
      catalog_publisher: editable.catalog_publisher,
      catalog_place: editable.catalog_place,
      catalog_language: editable.catalog_language,
      catalog_keywords: editable.catalog_keywords,
    });
    successMsg = "Metadatos del catálogo guardados en memoria.";
    errorMsg = "";
  }
</script>

<div class="max-w-[900px] mx-auto p-4 space-y-4">
  <div class="card">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">Catálogo maestro (CSV opcional)</h2>
      <div class="text-sm text-gray-600">
        Sesión: <span class="font-mono">{$sessionId || "—"}</span>
      </div>
    </div>
    <p class="text-sm text-gray-600 mt-1">
      Puedes cargar el CSV en cualquier momento (antes o después de subir imágenes). La app intentará detectar el
      <span class="font-mono">catalog_id</span> a partir de los nombres de archivo (p.ej. <span class="font-mono">BO0624_5445</span>).
    </p>
  </div>

  <!-- Estado -->
  <div class="card">
    <div class="flex items-center gap-2">
      <span class="badge">{ $csvLoaded ? "CSV cargado" : "CSV no cargado" }</span>
      <span class="text-sm text-gray-700">{$catalogStatusText}</span>
    </div>
    <div class="mt-2 flex gap-2">
      <button class="btn" type="button" on:click={handleRefresh}>Refrescar estado</button>
    </div>
  </div>

  <!-- Carga CSV -->
  <div class="card">
    <h3 class="font-semibold mb-2">Subir archivo CSV</h3>

    <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
      <div class="flex-1">
        <label class="block text-sm" for="csvFile">Archivo CSV</label>
        <input
          id="csvFile"
          type="file"
          accept=".csv,text/csv"
          class="input w-full"
          on:change={(e) => { file = e.currentTarget.files?.[0] || null; }}
        />
      </div>

      <button
        class="btn"
        type="button"
        on:click={handleUpload}
        disabled={uploading || !file}
        aria-busy={uploading ? "true" : "false"}
      >
        {uploading ? "Cargando..." : "Cargar CSV"}
      </button>
    </div>

    {#if errorMsg}
      <div class="mt-3 text-sm text-red-600">{errorMsg}</div>
    {/if}
    {#if successMsg}
      <div class="mt-3 text-sm text-green-700">{successMsg}</div>
    {/if}

    <details class="mt-3">
      <summary class="cursor-pointer text-sm text-gray-700">Formato admitido (cabeceras flexibles)</summary>
      <div class="mt-2 text-sm text-gray-600 space-y-1">
        <p>Cabeceras reconocidas (mezclables en ES/EN):</p>
        <ul class="list-disc ml-6">
          <li><code>id_catalogo</code>, <code>catalog_id</code>, <code>id</code></li>
          <li><code>titulo</code>, <code>title</code></li>
          <li><code>autor</code>, <code>author</code></li>
          <li><code>anio_publicacion</code>, <code>año_publicacion</code>, <code>publication_year</code>, <code>year</code></li>
          <li><code>publisher</code>, <code>editorial</code></li>
          <li><code>place</code>, <code>lugar</code></li>
          <li><code>language</code>, <code>idioma</code></li>
          <li><code>keywords</code>, <code>palabras_clave</code></li>
        </ul>
      </div>
    </details>
  </div>

  <!-- Resumen y edición manual de metadatos del catálogo (opcional) -->
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
      <button class="btn" type="button" on:click={handleRefresh}>
        Volver a cargar desde servidor
      </button>
    </div>

    <p class="text-xs text-gray-600 mt-2">
      Estos cambios se guardan <strong>solo en memoria</strong> (frontend). Al exportar, envía estos campos como
      <code>catalog_override</code> para que queden en <code>metadata.json</code>.
    </p>
  </div>
</div>
