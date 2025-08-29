<script>
  import { sessionId, API_BASE } from "../lib/stores.js";
  import {
    uploadCatalogCSV,
    refreshCatalogStatus,
    csvLoaded,
    catalogStatusText,
  } from "../lib/catalogStore.js";

  let csvFile = null;
  let csvUploading = false;
  let csvError = "";
  let csvSuccess = "";

  async function handleCsvUpload() {
    csvError = "";
    csvSuccess = "";
    if (!csvFile) { csvError = "Selecciona un archivo CSV."; return; }
    try {
      csvUploading = true;
      const res = await uploadCatalogCSV(csvFile); // usa session_id actual si existe
      csvSuccess =
        `CSV cargado${res?.loaded ? ` (entradas: ${res.loaded})` : ""}` +
        `${res?.detected_id ? ` — detectado: ${res.detected_id}` : ""}.`;
      await refreshCatalogStatus();
    } catch (e) {
      csvError = e?.message || "Error al subir el CSV.";
    } finally {
      csvUploading = false;
    }
  }

  async function handleCsvRefresh() {
    csvError = "";
    csvSuccess = "";
    try {
      await refreshCatalogStatus();
      csvSuccess = "Estado actualizado.";
    } catch {
      csvError = "No se pudo actualizar el estado.";
    }
  }
</script>

<div class="card">
  <div class="flex items-center justify-between">
    <h2 class="text-lg font-semibold">Catálogo maestro (CSV opcional)</h2>
    <div class="text-sm text-gray-600">
      Sesión: <span class="font-mono">{$sessionId || "—"}</span>
    </div>
  </div>

  <!-- Selector + botón -->
  <div class="mt-3 flex flex-col sm:flex-row gap-3 items-start sm:items-end">
    <div class="flex-1">
      <label class="block text-sm" for="csvFile">Archivo CSV</label>
      <input
        id="csvFile"
        type="file"
        accept=".csv,text/csv"
        class="input w-full"
        on:change={(e) => { csvFile = e.currentTarget.files?.[0] || null; }}
      />
    </div>

    <button
      class="btn"
      type="button"
      on:click={handleCsvUpload}
      disabled={csvUploading || !csvFile}
      aria-busy={csvUploading ? "true" : "false"}
    >
      {csvUploading ? "Cargando..." : "Cargar CSV"}
    </button>
  </div>

  <!-- Desplegable de formato -->
  <details class="mt-3">
    <summary class="cursor-pointer text-sm text-gray-700">
      Formato admitido (cabeceras flexibles)
    </summary>
    <div class="mt-2 text-sm text-gray-600 space-y-1">
      <p>Cabeceras reconocidas (mezclables ES/EN):</p>
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

  <!-- Estado CSV (nueva posición dentro del mismo card) -->
  <div class="mt-4 border-t pt-3">
    <div class="flex flex-wrap items-center gap-2">
      <span class="badge">{ $csvLoaded ? "CSV cargado" : "CSV no cargado" }</span>
      <span class="text-sm text-gray-700">{$catalogStatusText}</span>
      <button class="btn ml-auto" type="button" on:click={handleCsvRefresh}>Refrescar estado</button>
    </div>

    {#if csvError}
      <div class="mt-3 text-sm text-red-600">{csvError}</div>
    {/if}
    {#if csvSuccess}
      <div class="mt-3 text-sm text-green-700">{csvSuccess}</div>
    {/if}
  </div>
</div>
