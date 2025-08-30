<script>
  // Páginas
  import Upload from "./pages/Upload.svelte";
  import Gallery from "./pages/Gallery.svelte";
  import Viewer from "./pages/Viewer.svelte";
  import ExportPage from "./pages/Export.svelte";

  // Navegación + sesión base
  import { currentPage, pages, sessionId, API_BASE } from "./lib/stores.js";

  // Label de sesión desde backend (con guardas)
  import * as SessionLabel from "./lib/storesSessionLabel.js";
  const sessionLabel = SessionLabel.sessionLabel;
  const fetchSessionLabel = SessionLabel.fetchSessionLabel;

  // ID de catálogo detectado (si hay CSV/imagenes)
  import { detectedCatalogId } from "./lib/catalogStore.js";

  // Formateador “bonito”
  import { niceSession } from "./lib/utils/niceSession.js";

  // CSS global
  import "./app.css";

  // Trae etiqueta desde backend cuando hay sessionId
  $: if ($sessionId && typeof fetchSessionLabel === "function") {
    Promise.resolve(fetchSessionLabel($API_BASE, $sessionId)).catch(() => {});
  }

  // Nombre final a mostrar
  $: displayName = niceSession($sessionId, $sessionLabel, $detectedCatalogId);

  // Renombrar sesión (guarda en backend y refresca store)
  async function renameSession() {
    const name = window.prompt("Nuevo nombre de sesión:", displayName || "");
    if (name == null) return; // cancelado
    const label = name.trim();
    try {
      const resp = await fetch(`${$API_BASE}/session_label_set`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: $sessionId, label })
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        alert(data.error || "No se pudo guardar el nombre");
        return;
      }
      SessionLabel.sessionLabel.set(data.label || label);
    } catch (e) {
      console.error(e);
    }
  }
</script>

<div class="max-w-7xl mx-auto p-4 space-y-4">
  <header class="flex flex-wrap items-center justify-between gap-3 card">
    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-semibold">Archives Renamer</h1>
    </div>
    <nav class="flex gap-2">
      {#each pages as p}
        <button
          class="btn"
          aria-current={$currentPage === p ? "page" : undefined}
          on:click={() => currentPage.set(p)}
        >
          {p}
        </button>
      {/each}
    </nav>
    <div class="text-sm text-gray-600 flex items-center gap-2">
        Sesión: {displayName}
        <button
          class="btn btn-outline"
          type="button"
          on:click={renameSession}
          title="Renombrar sesión"
          aria-label="Renombrar sesión"
        >
          ✏️
        </button>
      </div>
  </header>

  {#if $currentPage === "Upload"}
    <Upload />
  {:else if $currentPage === "Galería"}
    <Gallery />
  {:else if $currentPage === "Visor"}
    <Viewer />
  {:else if $currentPage === "Exportar"}
    <ExportPage />
  {/if}
</div>
