<script>
  // ===== Estado global y APIs existentes =====
  import { items, API_BASE, sessionId } from "../lib/stores.js";
  import { refreshCatalogStatus, detectedEntry, detectedCatalogId, csvLoaded } from "../lib/catalogStore.js";
  import { tick } from "svelte";

  // ===== Estado local =====
  let loading = false;
  let error = "";

  // Cambios pendientes por ítem (id -> {campos})
  let edited = new Map();

  // Formulario de metadatos de catálogo (editable en la columna izquierda)
  // Se inicia con los valores detectados (si existe) o vacíos.
  let cat = {
    id_catalogo: "",
    title: "",
    publisher: "",
    place: "",
    year: "",
    language: "",
    keywords: ""
  };

  // Inicializa/actualiza el formulario cat desde stores detectados
  function initCatalogForm() {
    const entry = $detectedEntry || null;
    cat.id_catalogo = $detectedCatalogId || cat.id_catalogo || "";
    cat.title      = entry?.catalog_title || cat.title || "";
    // Estos campos son opcionales: publisher, place, language, keywords
    if (!cat.year && entry?.catalog_publication_year != null) {
      cat.year = String(entry.catalog_publication_year);
    }
  }

  // Llamamos cuando entra la página y antes de previsualizar/exportar
  refreshCatalogStatus().then(initCatalogForm).catch(()=>{});

  // Actualiza un campo del formulario
  function onCatChange(field, value) {
    cat = { ...cat, [field]: value };
  }

  // Campos de página por ítem
  const types = [
    "portada","contraportada","guardas","velinas","frontispicio",
    "texto","ilustración","inserto","página blanca","referencia","sin-tipo"
  ];

  function onEdit(id, field, value) {
    const cur = edited.get(id) || {};
    cur[field] = value;
    edited.set(id, cur);
  }

  function resetEdits() {
    edited.clear();
  }

  // Aplica TODOS los cambios por ítem (usa /validate)
  async function applyChanges() {
    if (edited.size === 0) return;
    loading = true; error = "";
    try {
      const updates = [];
      for (const [id, fields] of edited.entries()) {
        const payload = { id };
        // 👉 incluye 'keywords' también
        ["type","validated","page_number","number_scheme","extra","ghost_number","graphic","keywords"].forEach(k => {
          if (k in fields) payload[k] = fields[k];
        });
        updates.push(payload);
      }
      const resp = await fetch(`${$API_BASE}/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: $sessionId, updates })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Validate failed");
      items.set(data.items);

      await refreshNames();
      resetEdits();
    } catch (e) {
      error = e.message || "Could not apply changes.";
    } finally {
      loading = false;
    }
  }

  // Pide al backend recalcular new_filename
  async function refreshNames() {
    const resp = await fetch(`${$API_BASE}/preview?session_id=${$sessionId}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Preview failed");
    items.set(data.items);
  }

  // ===== Helpers de catálogo para export =====
  function buildCatalogOverride() {
    return {
      catalog_id: (cat.id_catalogo || "").trim() || null,
      catalog_title: (cat.title || "").trim() || "",
      catalog_publisher: (cat.publisher || "").trim() || "",
      catalog_place: (cat.place || "").trim() || "",
      catalog_publication_year: cat.year ? parseInt(cat.year, 10) : null,
      catalog_language: (cat.language || "").trim() || "",
      catalog_keywords: (cat.keywords || "").trim() || ""
    };
  }

  // ====== EXPORTACIÓN ======
  // Exporta con metadatos de catálogo (cat) aunque no haya CSV (usa /export)
  async function confirmAndExportWithCatalog() {
    loading = true; error = "";
    try {
      const body = {
        session_id: $sessionId,
        catalog_override: buildCatalogOverride()
      };
      const resp = await fetch(`${$API_BASE}/export`, {
        method: "POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify(body)
      });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || "Export failed");
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `export_${$sessionId}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      error = e.message || "Export failed";
    } finally {
      loading = false;
    }
  }

  // ====== PREVIEW POP-UP ======
  let showPreview = false;
  let previewRows = [];
  let previewHeader = null; // objeto de cabecera del catálogo devuelto por /export_preview

  async function openPreview() {
    loading = true; error = "";
    try {
      // Asegurar nombres al día y estado de catálogo
      await fetch(`${$API_BASE}/preview?session_id=${$sessionId}`);
      await refreshCatalogStatus();
      initCatalogForm();

      // Pedir previsualización real al backend (incluye cabecera + páginas)
      const body = {
        session_id: $sessionId,
        catalog_override: buildCatalogOverride()
      };
      const resp = await fetch(`${$API_BASE}/export_preview`, {
        method: "POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Failed to build preview.");

      // Cabecera (primer objeto)
      previewHeader = data.metadata && data.metadata.length ? data.metadata[0] : null;

      // Filas por página (del backend), unimos con thumb por original_filename
      const byOriginal = new Map($items.map(it => [it.original_filename, it]));
      previewRows = (data.metadata || []).slice(1).map(row => {
        const it = byOriginal.get(row.original_filename);
        return {
          ...row,
          thumb: it ? `${$API_BASE}/thumb/${$sessionId}/${it.id}` : null
        };
      });

      showPreview = true;
    } catch (e) {
      error = e.message || "Failed to build preview.";
    } finally {
      loading = false;
    }
  }
</script>

<!-- ================== Header acciones ================== -->
<div class="sticky top-0 z-20 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 border-b">
  <div class="max-w-[1600px] mx-auto p-3 flex flex-wrap gap-2 items-center">
    <button class="btn" on:click={openPreview} disabled={loading}>
      {loading ? "Preparing preview..." : "Export (Preview first)"}
    </button>
    <button class="btn" on:click={applyChanges} disabled={loading || edited.size===0}>
      Apply all changes ({edited.size})
    </button>
    <button class="btn" on:click={refreshNames} disabled={loading}>
      Refresh names
    </button>
    <button class="btn" on:click={confirmAndExportWithCatalog} disabled={loading || $items.length===0}>
      Confirm & Export (with catalog)
    </button>
    {#if error}<div class="text-sm text-red-600 ml-auto">{error}</div>{/if}
  </div>
</div>

<!-- ================== Layout 2 columnas ================== -->
<div class="max-w-[1600px] mx-auto p-3 grid grid-cols-1 lg:grid-cols-5 gap-5">
  <!-- Columna izquierda: METADATOS DE CATÁLOGO (editable) -->
  <aside class="lg:col-span-2">
    <div class="card sticky top-[76px] space-y-3">
      <h3 class="font-semibold">Catalog metadata</h3>
      <div class="text-xs text-gray-600">
        {$csvLoaded ? "Loaded from CSV (you can override):" : "CSV not loaded (optional). Fill manually:"}
      </div>

      <div class="grid grid-cols-1 gap-3">
        <div>
          <label class="block text-sm mb-1" for="cat_id">id_catalogo</label>
          <input id="cat_id" class="input w-full" type="text"
                 bind:value={cat.id_catalogo}
                 on:input={(e)=> onCatChange("id_catalogo", e.target.value)} />
          <div class="text-[11px] text-gray-500 mt-1">
            {#if $detectedCatalogId}Detected: {$detectedCatalogId}{/if}
          </div>
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_title">title</label>
          <input id="cat_title" class="input w-full" type="text"
                 bind:value={cat.title}
                 on:input={(e)=> onCatChange("title", e.target.value)} />
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_publisher">publisher</label>
          <input id="cat_publisher" class="input w-full" type="text"
                 bind:value={cat.publisher}
                 on:input={(e)=> onCatChange("publisher", e.target.value)} />
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_place">place</label>
          <input id="cat_place" class="input w-full" type="text"
                 bind:value={cat.place}
                 on:input={(e)=> onCatChange("place", e.target.value)} />
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_year">year</label>
          <input id="cat_year" class="input w-full" type="number" min="0"
                 bind:value={cat.year}
                 on:input={(e)=> onCatChange("year", e.target.value)} />
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_language">language</label>
          <input id="cat_language" class="input w-full" type="text"
                 bind:value={cat.language}
                 on:input={(e)=> onCatChange("language", e.target.value)} />
        </div>

        <div>
          <label class="block text-sm mb-1" for="cat_keywords">keywords</label>
          <input id="cat_keywords" class="input w-full" type="text"
                 placeholder="comma,separated,terms"
                 bind:value={cat.keywords}
                 on:input={(e)=> onCatChange("keywords", e.target.value)} />
        </div>

        <div class="text-xs text-gray-500">
          Estos metadatos se incluirán en <code>metadata.json</code> al exportar.
        </div>
      </div>
    </div>
  </aside>

  <!-- Columna derecha: Original + Nuevo nombre + Edición (centrada visualmente por grid) -->
  <section class="lg:col-span-3">
    <div class="card h-[90vh] overflow-auto">
      <h3 class="font-semibold mb-2 text-center">Names & per-page edits</h3>

      <div class="space-y-3">
        {#each $items as it}
          <div class="border rounded-xl p-3">
            <div class="flex items-start gap-3">
              <img class="w-20 h-20 object-cover rounded-md border"
                   src={`${$API_BASE}/thumb/${$sessionId}/${it.id}`}
                   alt={it.original_filename} />
              <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-600 truncate">Original</div>
                <div class="font-medium truncate">{it.original_filename}</div>

                <div class="mt-2 text-xs text-gray-600">New name (auto)</div>
                <div class="font-medium truncate">{it.new_filename || "—"}</div>
              </div>
            </div>

            <!-- Controles por ítem -->
            <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
              <div>
                <label class="block text-sm mb-1">Type</label>
                <select class="input w-full"
                        value={it.type || ""}
                        on:change={(e)=> onEdit(it.id, "type", e.target.value || null)}>
                  <option value="">—</option>
                  {#each types as t}<option value={t} selected={it.type===t}>{t}</option>{/each}
                </select>
              </div>

              <div>
                <label class="block text-sm mb-1">Page number</label>
                <input class="input w-full" type="number"
                       value={it.page_number ?? ""}
                       on:change={(e)=> {
                         const v = e.target.value.trim();
                         onEdit(it.id, "page_number", v==="" ? null : parseInt(v,10));
                       }} />
              </div>

              <div>
                <label class="block text-sm mb-1">Scheme</label>
                <select class="input w-full"
                        value={it.number_scheme || "arabic"}
                        on:change={(e)=> onEdit(it.id, "number_scheme", e.target.value)}>
                  <option value="arabic">arabic</option>
                  <option value="roman">roman</option>
                </select>
              </div>

              <div>
                <label class="block text-sm mb-1">Extra (bis, a, v)</label>
                <input class="input w-full" type="text"
                       value={it.extra || ""}
                       on:change={(e)=> onEdit(it.id, "extra", e.target.value)} />
              </div>

              <div>
                <label class="block text-sm mb-1">Keywords</label>
                <input class="input w-full" type="text"
                       value={it.keywords || ""}
                       on:change={(e)=> onEdit(it.id, "keywords", e.target.value)} />
              </div>

              <div class="flex items-center gap-2">
                <input id={"ghost_"+it.id} type="checkbox"
                       checked={!!it.ghost_number}
                       on:change={(e)=> onEdit(it.id, "ghost_number", e.target.checked)} />
                <label for={"ghost_"+it.id}>Ghost number</label>
              </div>

              <div class="flex items-center gap-2">
                <input id={"valid_"+it.id} type="checkbox"
                       checked={!!it.validated}
                       on:change={(e)=> onEdit(it.id, "validated", e.target.checked)} />
                <label for={"valid_"+it.id}>Validated</label>
              </div>

              <div class="flex items-center gap-2">
                <input id={"graphic_"+it.id} type="checkbox"
                       checked={!!it.graphic}
                       on:change={(e)=> onEdit(it.id, "graphic", e.target.checked)} />
                <label for={"graphic_"+it.id}>Graphic</label>
              </div>
            </div>

            <!-- Acciones por ítem -->
            <div class="mt-3 flex gap-2">
              <button class="btn"
                      on:click={async () => {
                        const fields = edited.get(it.id);
                        if (!fields) return;
                        const resp = await fetch(`${$API_BASE}/validate`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ session_id: $sessionId, updates: [{ id: it.id, ...fields }] })
                        });
                        const data = await resp.json();
                        if (!resp.ok) { alert(data.error || "Validate failed"); return; }
                        items.set(data.items);
                        await refreshNames();
                        edited.delete(it.id);
                      }}>
                Apply this item
              </button>

              <button class="btn" on:click={refreshNames}>
                Refresh name
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>
</div>

<!-- ================== POP-UP de previsualización ================== -->
{#if showPreview}
  <div class="fixed inset-0 bg-black/40 z-30 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-xl max-w-6xl w-full max-h-[85vh] overflow-hidden flex flex-col">
      <div class="p-4 border-b flex items-center justify-between">
        <h3 class="font-semibold">Export Preview</h3>
        <div class="text-sm text-gray-600">
          Catalog:
          {#if cat.title}
            {cat.title}{#if cat.publisher} — {cat.publisher}{/if}
            {#if cat.year} ({cat.year}){/if}
          {:else} — {/if}
        </div>
        <button class="btn" on:click={()=> showPreview=false}>Close</button>
      </div>

      <div class="p-4 overflow-auto">
        <!-- Resumen de metadatos de catálogo (de backend si está, si no lo que hay en form) -->
        <div class="mb-4 text-sm grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-1">
          <div><span class="text-gray-500">id_catalogo:</span> {previewHeader?.catalog_id ?? (cat.id_catalogo || "—")}</div>
          <div><span class="text-gray-500">title:</span> {previewHeader?.catalog_title ?? (cat.title || "—")}</div>
          <div><span class="text-gray-500">publisher:</span> {previewHeader?.catalog_publisher ?? (cat.publisher || "—")}</div>
          <div><span class="text-gray-500">place:</span> {previewHeader?.catalog_place ?? (cat.place || "—")}</div>
          <div><span class="text-gray-500">year:</span> {previewHeader?.catalog_publication_year ?? (cat.year || "—")}</div>
          <div><span class="text-gray-500">language:</span> {previewHeader?.catalog_language ?? (cat.language || "—")}</div>
          <div class="sm:col-span-2 lg:col-span-3"><span class="text-gray-500">keywords:</span> {previewHeader?.catalog_keywords ?? (cat.keywords || "—")}</div>
        </div>

        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-white">
            <tr class="text-left border-b">
              <th class="py-2 pr-3">Thumb</th>
              <th class="py-2 pr-3">Original</th>
              <th class="py-2 pr-3">New name</th>
              <th class="py-2 pr-3">Type</th>
              <th class="py-2 pr-3">Validated</th>
              <th class="py-2 pr-3">Page</th>
            </tr>
          </thead>
          <tbody>
            {#each previewRows as r}
              <tr class="border-b">
                <td class="py-2 pr-3">
                  {#if r.thumb}
                    <img src={r.thumb} alt={r.original_filename} class="w-14 h-14 object-cover rounded-md border" />
                  {:else}
                    —
                  {/if}
                </td>
                <td class="py-2 pr-3">{r.original_filename}</td>
                <td class="py-2 pr-3">{r.new_filename}</td>
                <td class="py-2 pr-3">{r.type || "—"}</td>
                <td class="py-2 pr-3">{r.validated ? "✔" : "⏳"}</td>
                <td class="py-2 pr-3">{r.page_number ?? "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="p-4 border-t flex gap-2 justify-end">
        <button class="btn" on:click={()=> showPreview=false}>Close</button>
      </div>
    </div>
  </div>
{/if}
