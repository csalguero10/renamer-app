<script>
  import { API_BASE, sessionId, items, selection, toggleSelect, clearSelection } from "../lib/stores.js";

  // ---------------- Filtros ----------------
  let filterStatus = "all"; // all | pendiente | validada
  let filterType = "all";

  // Resultado filtrado (se muestra en la grilla principal)
  $: filtered = $items.filter(it => {
    if (filterStatus !== "all") {
      if (filterStatus === "pending" && it.validated) return false;
      if (filterStatus === "validated" && !it.validated) return false;
    }
    if (filterType !== "all" && it.type !== filterType) return false;
    return true;
  });

  // ---------------- Acciones backend ----------------
  let isClassifying = false;
  let classifyError = "";

  async function classify() {
    if (isClassifying) return;
    isClassifying = true;
    classifyError = "";
    try {
      const resp = await fetch(`${$API_BASE}/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: $sessionId })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Error classifying");
      items.set(data.items);
    } catch (e) {
      classifyError = e.message || "Could not classify.";
    } finally {
      isClassifying = false;
    }
  }

  async function refreshPreview() {
    const resp = await fetch(`${$API_BASE}/preview?session_id=${$sessionId}`);
    const data = await resp.json();
    items.set(data.items);
  }

  // Aplica cambios masivos (tipo/validación) o numeración
  async function bulkAssign({
    type = null, validated = null, start = null, step = 1, scheme = "arabic", extra = "", ghost = false
  } = {}) {
    const ids = Array.from($selection);
    if (!ids.length) return;

    const updates = [];
    if (type !== null || validated !== null) {
      ids.forEach(id => updates.push({ id, ...(type !== null ? { type } : {}), ...(validated !== null ? { validated } : {}) }));
    }

    const payload = {
      session_id: $sessionId,
      updates,
      bulk_numbering: (start !== null) ? { ids, start, step, scheme, extra, ghost } : null
    };

    const resp = await fetch(`${$API_BASE}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    items.set(data.items);
    // Limpia selección y ancla después de aplicar
    clearSelection();
    anchorIndex = null;
  }

  // ---------------- Seleccionar todo/ nada ----------------
  function toggleSelectAll() {
    const allSelected = filtered.length > 0 && filtered.every(it => $selection.has(it.id));
    if (allSelected) {
      clearSelection();
      anchorIndex = null;
    } else {
      filtered.forEach(it => { if (!$selection.has(it.id)) toggleSelect(it.id); });
      anchorIndex = 0;
    }
  }
// cambiar a inglés
  const types = [
    "cover","back cover","endpapers","flyleaves","frontispiece",
    "text","illustration","insert","blank page","reference","no-type"
  ];

  // ---------------- Lightbox (vista grande) ----------------
  let showLightbox = false;
  let lightboxIndex = 0;

  // La lista del lightbox: si hay selección, sólo seleccionados (en orden de 'filtered'); si no, todo 'filtered'
  $: selectedIds = Array.from($selection);
  $: lightboxList = (selectedIds.length
    ? filtered.filter(it => selectedIds.includes(it.id))
    : filtered);

  function openLightbox(startId = null) {
    if (!lightboxList.length) return;
    if (startId) {
      const idx = lightboxList.findIndex(it => it.id === startId);
      lightboxIndex = idx >= 0 ? idx : 0;
    } else {
      lightboxIndex = 0;
    }
    showLightbox = true;
  }
  const closeLightbox = () => (showLightbox = false);
  function prevLightbox() {
    if (!lightboxList.length) return;
    lightboxIndex = (lightboxIndex - 1 + lightboxList.length) % lightboxList.length;
  }
  function nextLightbox() {
    if (!lightboxList.length) return;
    lightboxIndex = (lightboxIndex + 1) % lightboxList.length;
  }

  // Navegación por teclado cuando el lightbox está abierto
  function lightboxKeys(e) {
    if (!showLightbox) return;
    if (e.key === "Escape") { e.preventDefault(); closeLightbox(); }
    if (e.key === "ArrowLeft") { e.preventDefault(); prevLightbox(); }
    if (e.key === "ArrowRight") { e.preventDefault(); nextLightbox(); }
  }

  // ---------------- Selección por rango (Shift+click) ----------------
  let anchorIndex = null; // última miniatura clicada como ancla

  function handleThumbClick(event, index, id) {
    // Si no hay ancla todavía, establecerla en el primer click
    if (anchorIndex === null) anchorIndex = index;

    // Shift + click: selecciona el rango [anchorIndex, index]
    if (event.shiftKey && filtered.length) {
      const start = Math.min(anchorIndex, index);
      const end = Math.max(anchorIndex, index);
      for (let i = start; i <= end; i++) {
        const tid = filtered[i].id;
        if (!$selection.has(tid)) toggleSelect(tid);
      }
      anchorIndex = index;
      return;
    }

    // Cmd/Ctrl + click: alterna sin afectar otras
    if (event.metaKey || event.ctrlKey) {
      toggleSelect(id);
      anchorIndex = index;
      return;
    }

    // Click simple: alterna
    toggleSelect(id);
    anchorIndex = index;
  }

  // Si se limpia toda la selección, resetea el ancla
  $: if ($selection.size === 0) {
    anchorIndex = null;
  }

  // ============ LÓGICA DINÁMICA DEL DESPLEGABLE "ASIGNAR TIPO" ============
  // Lista de seleccionados visible (sobre el conjunto filtrado actual)
  $: selectedList = filtered.filter(it => $selection.has(it.id));

  // Determina el valor visible del select: "blank" | "__mixed" | "<tipo>"
  function computeUiBulkType(list) {
    if (!list || list.length === 0) return "blank"; // Sin selección
    const set = new Set(
      list.map(it => it?.type).filter(t => typeof t === "string" && t.trim().length > 0)
    );
    if (set.size === 0) return "blank";       // No hay tipos asignados aún
    if (set.size === 1) return Array.from(set)[0]; // Mismo tipo en toda la selección
    return "__mixed";                          // Mezcla de tipos
  }

  let uiBulkType = "blank";
  let lastBulkSig = "";

  // Recalcula automáticamente cuando cambia selección o tipo de los seleccionados
  $: {
    const sig = JSON.stringify(selectedList.map(it => it.id).sort())
             + "|" + JSON.stringify(selectedList.map(it => it.type));
    if (sig !== lastBulkSig) {
      uiBulkType = computeUiBulkType(selectedList);
      lastBulkSig = sig;
    }
  }

  // ============ PASO 2: Único botón "Aplicar cambios" (condicional) ============
  async function applyUnifiedChanges() {
    const ids = Array.from($selection);
    if (!ids.length) return;

    // Lee controles
    const rawType = document.getElementById('bulkType').value;
    const type = (rawType === "blank" || rawType === "__mixed") ? null : (rawType || null);

    const valSel = document.getElementById('bulkVal').value;
    const validated = valSel === "" ? null : (valSel === "true");

    const keywords = (document.getElementById('bulkKeywords').value || "").trim();
    const graphic = document.getElementById('bulkGraphic').checked;

    const startRaw = document.getElementById('bulkStart').value;
    const stepRaw = document.getElementById('bulkStep').value;
    const scheme = document.getElementById('bulkScheme').value;
    const extra = document.getElementById('bulkExtra').value || "";
    const ghost = document.getElementById('bulkGhost').checked;

    // Construye updates por ítem
    const updates = ids.map(id => {
      const u = { id };
      if (type !== null) u.type = type;
      if (validated !== null) u.validated = validated;
      u.graphic = graphic;
      if (keywords !== "") u.keywords = keywords;
      return u;
    });

    // Sólo numeración si hay "inicio" rellenado
    let bulk_numbering = null;
    if (startRaw !== "" && startRaw != null) {
      const start = parseInt(startRaw, 10);
      const step = parseInt(stepRaw || "1", 10);
      bulk_numbering = { ids, start, step, scheme, extra, ghost };
    }

    const payload = {
      session_id: $sessionId,
      updates,
      bulk_numbering
    };

    const resp = await fetch(`${$API_BASE}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (!resp.ok) {
      alert(data.error || "No se pudieron aplicar los cambios.");
      return;
    }
    items.set(data.items);
    clearSelection();
    anchorIndex = null;
  }
</script>

<svelte:window on:keydown={lightboxKeys} />

<!-- =========================================
     PANEL STICKY (PASO 1 y PASO 3)
     ========================================= -->
<div class="sticky top-0 z-20 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 border-b">
  <div class="max-w-[1600px] mx-auto p-3 space-y-3">

    <!-- ============ PASO 1: CLASIFICAR Y FILTRAR ============ -->
    <div class="card py-2">
      <div class="flex items-center justify-between">
        <h3 class="font-semibold">Step 1: Classify and Filter</h3>
        <div class="text-sm text-gray-600">
            Selected: <span class="font-semibold">{$selection.size}</span>
        </div>
      </div>

      <div class="mt-2 flex flex-wrap items-end gap-3">
        <!-- Acción principal -->
        <div class="flex items-center gap-3">
          <button class="btn" type="button" on:click={classify} disabled={isClassifying} aria-busy={isClassifying}>
            {isClassifying ? "Classifying..." : "Automatic classification"}
          </button>

          {#if isClassifying}
            <!-- Indicador al lado del botón -->
            <div class="flex items-center gap-2 text-sm text-gray-600" role="status" aria-live="polite">
              <span class="inline-block w-4 h-4 rounded-full border-2 border-gray-300 border-t-gray-600 animate-spin"></span>
              Procesando…
            </div>
          {/if}

          {#if classifyError}
            <div class="text-sm text-red-600">{classifyError}</div>
          {/if}
        </div>

        <!-- Derecha: seleccionar/limpiar + filtros -->
        <div class="ml-auto flex flex-wrap items-end gap-2">
          <button class="btn" type="button" on:click={toggleSelectAll} disabled={isClassifying}>
            {filtered.length>0 && filtered.every(it => $selection.has(it.id)) ? "Deselect all" : "Select all"}
          </button>

          <button class="btn btn-outline" type="button" on:click={clearSelection} disabled={isClassifying}>
            Clear selection
          </button>

          <div>
            <label class="block text-sm" for="filterStatus">Status</label>
            <select id="filterStatus" class="input" bind:value={filterStatus} disabled={isClassifying}>
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="validated">Validated</option>
            </select>
          </div>

          <div>
            <label class="block text-sm" for="filterType">Type</label>
            <select id="filterType" class="input" bind:value={filterType} disabled={isClassifying}>
              <option value="all">All</option>
              {#each types as t}<option value={t}>{t}</option>{/each}
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ PASO 3: REVISAR Y EXPORTAR ============ -->
    <div class="card py-2">
      <div class="flex items-center gap-2">
        <h3 class="font-semibold">Review and Extratools</h3>
        <div class="ml-auto flex items-center gap-2">
          <button class="btn btn-outline" type="button" on:click={refreshPreview}>
            Preview filenames
          </button>
          <button
            class="btn"
            type="button"
            on:click={() => openLightbox()}
            aria-label="Abrir vista grande"
            title="Abrir vista grande"
            disabled={filtered.length === 0}
          >
            View large
          </button>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- =========================================
     LAYOUT: MINIATURAS (scroll) + SIDEBAR PASO 2 (estático)
     ========================================= -->
<div class="max-w-[1600px] mx-auto p-3 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_380px] gap-4
            h-[calc(100vh-110px)] overflow-hidden">
  <!-- ===== MAIN: miniaturas con scroll propio ===== -->
  <section class="h-full overflow-auto pr-2">
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-4 gap-3">
      {#each filtered as it, i}
        <div
          class={`relative card cursor-pointer transition
            ${$selection.has(it.id)
              ? 'border-2 border-orange-500 bg-orange-50/70 shadow-lg'
              : 'border border-gray-200 hover:border-gray-300'}
            focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-orange-500`}
          role="button"
          tabindex="0"
          on:click={(e) => handleThumbClick(e, i, it.id)}
          on:dblclick={() => openLightbox(it.id)}
          on:keydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleThumbClick(e, i, it.id);
            }
          }}
          aria-pressed={$selection.has(it.id)}
          aria-label={`Seleccionar ${it.original_filename}`}
          title="Click para seleccionar; Shift+Click para rango; Doble click para ver grande"
        >
          {#if $selection.has(it.id)}
            <span class="absolute top-1 right-1 text-[10px] px-1.5 py-0.5 rounded-md bg-orange-500 text-white shadow">
              Seleccionada
            </span>
          {/if}

          <img class="w-full h-48 object-cover rounded-xl"
               src={`${$API_BASE}/thumb/${$sessionId}/${it.id}`} alt={it.original_filename} />
          <div class="mt-2">
            <div class="text-xs text-gray-600 truncate">{it.original_filename}</div>
            <div class="text-sm font-medium truncate">{it.new_filename || '—'}</div>
            <div class="flex gap-1 text-xs mt-1">
              <span class="badge">{it.type || 'sin-tipo'}</span>
              {#if it.page_number !== null && it.page_number !== false}
                <span class="badge">nº {it.page_number}</span>
              {/if}
              <span class="badge">{it.validated ? '✔' : '⏳'}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- ===== SIDEBAR: PASO 2 (filas + botón unificado) ===== -->
  <aside class="hidden lg:block">
    <div class="card h-full overflow-auto">
      <h3 class="font-semibold">Step 2: Assign Metadata</h3>

      <!-- Fila 1: tipo + validación -->
      <div class="mt-3 grid grid-cols-2 gap-3">
        <div>
            <label class="block text-sm" for="bulkType">Assign type</label>
          <select id="bulkType" class="input" bind:value={uiBulkType}>
            <option value="blank">—</option>
            <option value="__mixed" disabled>Mixed types</option>
            {#each types as t}<option value={t}>{t}</option>{/each}
          </select>
            <div class="text-[11px] text-gray-500 mt-1">
            {#if uiBulkType === 'blank'}No selection or no type assigned.{/if}
            {#if uiBulkType === '__mixed'}Mixed type selection.{/if}
            </div>
        </div>

        <div>
            <label class="block text-sm" for="bulkVal">Validation</label>
            <select id="bulkVal" class="input">
            <option value="">—</option>
            <option value="true">Mark as validated</option>
            <option value="false">Mark as pending</option>
          </select>
        </div>
      </div>

      <!-- Fila 2: inicio + intervalo -->
      <div class="mt-3 grid grid-cols-2 gap-3 items-start">
        <div>
            <label class="block text-sm" for="bulkStart">Numbering: start</label>
          <input id="bulkStart" type="number" class="input" placeholder="1" aria-describedby="help-start" />
            <div id="help-start" class="mt-1 text-[11px] text-gray-500">Only if applicable</div>
        </div>

        <div>
            <label class="block text-sm" for="bulkStep">Step</label>
          <input id="bulkStep" type="number" class="input" placeholder="1" value="1" />
        </div>
      </div>


      <!-- Fila 3: esquema + extra -->
      <div class="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label class="block text-sm" for="bulkScheme">Scheme</label>
          <select id="bulkScheme" class="input">
            <option value="arabic">Arabic</option>
            <option value="roman">Roman</option>
          </select>
        </div>
        <div>
          <label class="block text-sm" for="bulkExtra">Extra (bis, a, v)</label>
          <input id="bulkExtra" type="text" class="input" placeholder="bis" />
        </div>
      </div>

      <!-- Fila 4: ghost + graphic -->
      <div class="mt-3 grid grid-cols-2 gap-3">
        <label class="flex items-center gap-2">
          <input id="bulkGhost" type="checkbox" />
          <span>Ghost number</span>
        </label>
        <label class="flex items-center gap-2">
          <input id="bulkGraphic" type="checkbox" />
          <span>Is there a graphic?</span>
        </label>
      </div>

      <!-- Fila 5: keywords full-width -->
      <div class="mt-3">
        <label class="block text-sm" for="bulkKeywords">Keywords (optional)</label>
        <input id="bulkKeywords" type="text" class="input" placeholder="word1, word2, ..." />
      </div>

      <!-- Fila 6: separador + botón unificado -->
      <hr class="my-4" />
      <button class="btn w-full" type="button" on:click={applyUnifiedChanges}>
        Apply changes
      </button>

      <!-- Fila 7: Validar selección (secundario) -->
      <div class="mt-2">
        <button
          class="btn btn-outline w-full"
          type="button"
          on:click={() => {
            bulkAssign({ validated: true }).then(() => {
              clearSelection();
              anchorIndex = null;
            });
          }}>
            Validate selection
        </button>
      </div>
    </div>
  </aside>
</div>

<!-- ==========================
     LIGHTBOX / VISTA GRANDE
     ========================== -->
{#if showLightbox && lightboxList.length}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-black/80 z-0"
      aria-label="Cerrar (clic fuera)"
      title="Cerrar (clic fuera)"
      on:click={closeLightbox}
    ></button>

    <div class="relative z-10 w-full h-full flex items-center justify-center">
      <img
        src={`${$API_BASE}/file_preview/${$sessionId}/${lightboxList[lightboxIndex].id}?w=2400`}
        alt={lightboxList[lightboxIndex].original_filename}
        class="max-w-[95vw] max-h-[90vh] object-contain rounded-xl shadow-2xl"
        draggable="false"
      />
      <button
        class="absolute top-3 right-3 btn"
        type="button"
        on:click={closeLightbox}
        aria-label="Cerrar vista grande"
        title="Cerrar"
      >✕</button>
      <button
        class="absolute left-3 top-1/2 -translate-y-1/2 btn"
        type="button"
        on:click={prevLightbox}
        aria-label="Anterior"
        title="Anterior"
      >←</button>
      <button
        class="absolute right-3 top-1/2 -translate-y-1/2 btn"
        type="button"
        on:click={nextLightbox}
        aria-label="Siguiente"
        title="Siguiente"
      >→</button>
      <div class="absolute bottom-3 left-1/2 -translate-x-1/2 text-white text-xs bg-black/50 px-3 py-1 rounded-full">
        {lightboxIndex + 1} / {lightboxList.length}
      </div>
    </div>
  </div>
{/if}
