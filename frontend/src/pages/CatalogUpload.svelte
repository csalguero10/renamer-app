    <script>
    import { uploadCatalogCSV, catalogStatusText, refreshCatalogStatus, csvLoaded } from "../lib/catalogStore.js";
    import { onMount } from "svelte";

    let file = null;
    let msg = "";
    let busy = false;

    onMount(() => {
        refreshCatalogStatus().catch(()=>{});
    });

    async function doUpload() {
        if (!file) return;
        busy = true; msg = "";
        try {
        await uploadCatalogCSV(file);
        msg = "CSV loaded successfully.";
        } catch (e) {
        msg = e.message || "Error uploading CSV.";
        } finally {
        busy = false;
        }
    }
    </script>

    <div class="card space-y-2">
    <h3 class="font-semibold">Catalog CSV (optional)</h3>
    <p class="text-sm text-gray-600">
        You can load a master CSV with columns
        <code>id_catalogo, titulo, autor, anio_publicacion</code>.
        It’s optional — you may upload images without it.
    </p>

    <div class="flex gap-2 items-center">
        <input class="input" type="file" accept=".csv" on:change={(e)=> file = e.target.files[0]} />
        <button class="btn" disabled={busy || !file} on:click={doUpload}>
        {busy ? "Uploading..." : "Load CSV"}
        </button>
    </div>

    <div class="text-sm">
        <span class="text-gray-700">Status: </span>
        <span class="font-medium">{$catalogStatusText}</span>
    </div>

    {#if msg}
        <div class="text-xs text-gray-500">{msg}</div>
    {/if}

    {#if $csvLoaded}
        <div class="text-xs text-green-700">CSV loaded. Catalog metadata will be linked if IDs match.</div>
    {:else}
        <div class="text-xs text-gray-600">CSV not loaded — that’s fine, you can proceed.</div>
    {/if}
    </div>
