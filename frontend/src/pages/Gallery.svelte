<script>
  import { API_BASE, sessionId, items, selection, toggleSelect, clearSelection, currentPage } from "../lib/stores.js";

  let filterStatus = "all"; // all | pendiente | validada
  let filterType = "all";

  // Filtrado de miniaturas
  $: filtered = $items.filter(it => {
    if (filterStatus !== "all") {
      if (filterStatus === "pendiente" && it.validated) return false;
      if (filterStatus === "validada" && !it.validated) return false;
    }
    if (filterType !== "all" && it.type !== filterType) return false;
    return true;
  });

  // Clasificación automática
  async function classify() {
    const resp = await fetch(`${$API_BASE}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: $sessionId })
    });
    const data = await resp.json();
    items.set(data.items);
  }

  // Aplicaciones masivas
  async function bulkAssign({
    type=null, validated=null, start=null, step=1, scheme="arabic", extra="", ghost=false
  }={}) {
    const ids = Array.from($selection);
    if (!ids.length) return;
    const updates = [];
    if (type !== null || validated !== null) {
      ids.forEach(id => updates.push({ id, ...(type!==null?{type}:{}), ...(validated!==null?{validated}:{} ) }));
    }
    const payload = {
      session_id: $sessionId,
      updates,
      bulk_numbering: (start!==null) ? { ids, start, step, scheme, extra, ghost } : null
    };
    const resp = await fetch(`${$API_BASE}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    items.set(data.items);
  }

  // Previsualizar nombres
  async function refreshPreview() {
    const resp = await fetch(`${$API_BASE}/preview?session_id=${$sessionId}`);
    const data = await resp.json();
    items.set(data.items);
  }

  // 👉 NUEVO: seleccionar todas/deseleccionar
  function toggleSelectAll() {
    const allSelected = filtered.every(it => $selection.has(it.id));
    if (allSelected) {
      clearSelection();
    } else {
      filtered.forEach(it => {
        if (!$selection.has(it.id)) toggleSelect(it.id);
      });
    }
  }

  const types = [
    "portada","contraportada","guardas","velinas","frontispicio",
    "texto","ilustración","inserto","página blanca","referencia","sin-tipo"
  ];
</script>

<!-- =========================================
     HEADER STICKY: filtros + acciones + edición masiva
     ========================================= -->
<div class="sticky top-0 z-20 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 border-b">
  <div class="max-w-[1600px] mx-auto p-3">
    <!-- Fila 1: filtros y acciones -->
    <div class="flex flex-wrap items-end gap-2">
      <div>
        <label class="block text-sm" for="filterStatus">Estado</label>
        <select id="filterStatus" class="input" bind:value={filterStatus}>
          <option value="all">Todos</option>
          <option value="pendiente">Pendiente</option>
          <option value="validada">Validada</option>
        </select>
      </div>
      <div>
        <label class="block text-sm" for="filterType">Tipo</label>
        <select id="filterType" class="input" bind:value={filterType}>
          <option value="all">Todos</option>
          {#each types as t}<option value={t}>{t}</option>{/each}
        </select>
      </div>

      <!-- acciones -->
      <button class="btn" on:click={classify}>Clasificación automática</button>
      <button class="btn" on:click={refreshPreview}>Previsualizar nombres</button>
      <button class="btn" on:click={clearSelection}>Limpiar selección</button>

      <!-- 👉 nuevo botón seleccionar todas -->
      <button class="btn" on:click={toggleSelectAll}>
        {filtered.every(it => $selection.has(it.id)) ? "Deseleccionar todas" : "Seleccionar todas"}
      </button>

      <div class="ml-auto text-sm text-gray-600">
        Seleccionadas: <span class="font-semibold">{$selection.size}</span>
      </div>
    </div>

    <!-- Fila 2: edición masiva -->
    <div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
      <div>
        <label class="block text-sm" for="bulkType">Asignar tipo</label>
        <select id="bulkType" class="input">
          <option value="">—</option>
          {#each types as t}<option value={t}>{t}</option>{/each}
        </select>
      </div>
      <div>
        <label class="block text-sm" for="bulkVal">Validación</label>
        <select id="bulkVal" class="input">
          <option value="">—</option>
          <option value="true">Marcar validada</option>
          <option value="false">Marcar pendiente</option>
        </select>
      </div>
      <div>
        <label class="block text-sm" for="bulkStart">Numeración: inicio</label>
        <input id="bulkStart" type="number" class="input" placeholder="1" />
      </div>
      <div>
        <label class="block text-sm" for="bulkStep">Intervalo</label>
        <input id="bulkStep" type="number" class="input" placeholder="1" value="1" />
      </div>
      <div>
        <label class="block text-sm" for="bulkScheme">Esquema</label>
        <select id="bulkScheme" class="input">
          <option value="arabic">Arábiga</option>
          <option value="roman">Romana</option>
        </select>
      </div>
      <div>
        <label class="block text-sm" for="bulkExtra">Extra (bis, a, v)</label>
        <input id="bulkExtra" type="text" class="input" placeholder="bis" />
      </div>
      <div class="flex items-center gap-2">
        <input id="bulkGhost" type="checkbox" />
        <label for="bulkGhost">Número fantasma</label>
      </div>

      <div class="sm:col-span-2 flex flex-wrap gap-2 items-end">
        <button class="btn"
          on:click={() => {
            const type = document.getElementById('bulkType').value || null;
            const valSel = document.getElementById('bulkVal').value;
            const validated = valSel === "" ? null : (valSel === "true");
            bulkAssign({ type, validated });
          }}>
          Aplicar
        </button>

        <button class="btn"
          on:click={() => {
            const startRaw = document.getElementById('bulkStart').value;
            if (!startRaw) return;
            const start = parseInt(startRaw, 10);
            const step = parseInt(document.getElementById('bulkStep').value || "1", 10);
            const scheme = document.getElementById('bulkScheme').value;
            const extra = document.getElementById('bulkExtra').value || "";
            const ghost = document.getElementById('bulkGhost').checked;
            bulkAssign({ start, step, scheme, extra, ghost });
          }}>
          Aplicar numeración
        </button>
      </div>
    </div>
  </div>
</div>

<!-- ==========================
     GRID DE MINIATURAS
     ========================== -->
<div class="max-w-[1600px] mx-auto p-3">
  <!-- 👇 ahora 5 columnas en pantallas grandes -->
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-5 gap-3">
    {#each filtered as it}
      <div
        class={`card cursor-pointer ${$selection.has(it.id) ? 'ring-2 ring-blue-500' : ''}`}
        role="button"
        tabindex="0"
        on:click={() => toggleSelect(it.id)}
        on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSelect(it.id); } }}
      >
        <img class="w-full h-48 object-cover rounded-xl" src={`${$API_BASE}/thumb/${$sessionId}/${it.id}`} alt={it.original_filename} />
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
</div>
