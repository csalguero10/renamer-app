<script>
    import { onMount } from "svelte";
    import { sessionId, API_BASE } from "../lib/stores.js";
    import {
        uploadCatalogCSV,
        refreshCatalogStatus,
        csvLoaded,
        catalogStatusText,
        detectedCatalogId,
    } from "../lib/catalogStore.js";

    // nombre de sesión bonito
    import {
        sessionLabel,
        fetchSessionLabel,
    } from "../lib/storesSessionLabel.js";
    import { niceSession } from "../lib/utils/niceSession.js";

    let csvFile = null;
    let csvUploading = false;
    let csvError = "";
    let csvSuccess = "";

    // nombre a mostrar (reactivo)
    $: displaySession = niceSession(
        $sessionId,
        $sessionLabel,
        $detectedCatalogId
    );

    onMount(() => {
        if ($sessionId) fetchSessionLabel($API_BASE, $sessionId);
    });

    // si cambia la sesión, vuelve a pedir el label
    $: if ($sessionId) {
        fetchSessionLabel($API_BASE, $sessionId);
    }

    async function handleCsvUpload() {
        csvError = "";
        csvSuccess = "";
        if (!csvFile) {
        csvError = "Please select a CSV file.";
        return;
        }
        try {
        csvUploading = true;
        const res = await uploadCatalogCSV(csvFile); // usa session_id actual si existe
        csvSuccess =
            `CSV loaded${res?.loaded ? ` (entries: ${res.loaded})` : ""}` +
            `${res?.detected_id ? ` — detected: ${res.detected_id}` : ""}.`;
        await refreshCatalogStatus();
        // refresca el label por si el backend lo creó en esta sesión
        if ($sessionId) await fetchSessionLabel($API_BASE, $sessionId);
        } catch (e) {
        csvError = e?.message || "Error uploading CSV.";
        } finally {
        csvUploading = false;
        }
    }

    async function handleCsvRefresh() {
        csvError = "";
        csvSuccess = "";
        try {
        await refreshCatalogStatus();
        csvSuccess = "Status updated.";
        if ($sessionId) await fetchSessionLabel($API_BASE, $sessionId);
        } catch {
        csvError = "Could not update status.";
        }
    }
    </script>

    <div class="card">
    <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Catalog (optional CSV)</h2>
        <div class="text-sm text-gray-600">
        Session: <span class="font-mono">{displaySession || "—"}</span>
        </div>
    </div>

    <!-- Selector + botón -->
    <div class="mt-3 flex flex-col sm:flex-row gap-3 items-start sm:items-end">
        <div class="flex-1">
        <label class="block text-sm" for="csvFile">CSV Archive</label>
        <input
            id="csvFile"
            type="file"
            accept=".csv,text/csv"
            class="input w-full"
            on:change={(e) => {
            csvFile = e.currentTarget.files?.[0] || null;
            }}
        />
        </div>

        <button
        class="btn"
        type="button"
        on:click={handleCsvUpload}
        disabled={csvUploading || !csvFile}
        aria-busy={csvUploading ? "true" : "false"}
        >
        {csvUploading ? "Loading..." : "Upload CSV"}
        </button>
    </div>

    <!-- Desplegable de formato -->
    <details class="mt-3">
        <summary class="cursor-pointer text-sm text-gray-700">
        Accepted format (flexible headers)
        </summary>
        <div class="mt-2 text-sm text-gray-600 space-y-1">
        <p>Recognized headers (mixable ES/EN):</p>
        <ul class="list-disc ml-6">
            <li>
            <code>id_catalogo</code>, <code>catalog_id</code>, <code>id</code>
            </li>
            <li><code>titulo</code>, <code>title</code></li>
            <li><code>autor</code>, <code>author</code></li>
            <li>
            <code>anio_publicacion</code>, <code>año_publicacion</code>,
            <code>publication_year</code>, <code>year</code>
            </li>
            <li><code>publisher</code>, <code>editorial</code></li>
            <li><code>place</code>, <code>lugar</code></li>
            <li><code>language</code>, <code>idioma</code></li>
            <li><code>keywords</code>, <code>palabras_clave</code></li>
        </ul>
        </div>
    </details>

    <!-- Estado CSV (dentro del mismo card) -->
    <div class="mt-4 border-t pt-3">
        <div class="flex flex-wrap items-center gap-2">
        <span class="badge">{$csvLoaded ? "CSV loaded" : "CSV not loaded"}</span>
        <span class="text-sm text-gray-700">{$catalogStatusText}</span>
        <button class="btn ml-auto" type="button" on:click={handleCsvRefresh}
            >Refresh status</button
        >
        </div>

        {#if csvError}
        <div class="mt-3 text-sm text-red-600">{csvError}</div>
        {/if}
        {#if csvSuccess}
        <div class="mt-3 text-sm text-green-700">{csvSuccess}</div>
        {/if}
    </div>
</div>
