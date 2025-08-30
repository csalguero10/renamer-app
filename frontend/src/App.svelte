<script>
  /* ===== Páginas (alias en MAYÚSCULAS) ===== */
  import UPLOAD from "./pages/Upload.svelte";
  import GALLERY from "./pages/Gallery.svelte";
  import VIEWER from "./pages/Viewer.svelte";
  import EXPORT from "./pages/Export.svelte";

  /* Mapa nombre->componente (CLAVES deben coincidir con tu store `pages`) */
  const COMPONENTS = {
    "Upload":   UPLOAD,
    "Galería":  GALLERY,
    "Visor":    VIEWER,
    "Exportar": EXPORT
  };

  /* Mapa: clave de página -> texto a mostrar (en NAV en mayúsculas) */
  const DISPLAY = {
    "Upload":   "UPLOAD",
    "Galería":  "GALLERY",
    "Visor":    "VIEWER",
    "Exportar": "EXPORT"
  };

  /* ===== Navegación + sesión base ===== */
  import { currentPage, pages, sessionId, API_BASE } from "./lib/stores.js";

  /* Label de sesión desde backend */
  import * as SessionLabel from "./lib/storesSessionLabel.js";
  const sessionLabel = SessionLabel.sessionLabel;
  const fetchSessionLabel = SessionLabel.fetchSessionLabel;

  /* ID de catálogo detectado (si hay CSV/imagenes) */
  import { detectedCatalogId } from "./lib/catalogStore.js";

  /* Formateador “bonito” */
  import { niceSession } from "./lib/utils/niceSession.js";

  /* CSS global */
  import "./app.css";

  /* Trae etiqueta desde backend cuando hay sessionId */
  $: if ($sessionId && typeof fetchSessionLabel === "function") {
    Promise.resolve(fetchSessionLabel($API_BASE, $sessionId)).catch(() => {});
  }

  /* Nombre final a mostrar en el header */
  $: displayName = niceSession($sessionId, $sessionLabel, $detectedCatalogId);

  /* Componente actual (fallback a UPLOAD si no hay coincidencia) */
  $: CurrentComponent = COMPONENTS[$currentPage] || UPLOAD;

  /* Renombrar sesión */
  async function renameSession() {
    const name = window.prompt("Nuevo nombre de sesión:", displayName || "");
    if (name == null) return;
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

<!-- ====== Header ancho completo con menú centrado ====== -->
<div class="top-nav mx-auto">
  <div class="top-nav__inner mx-auto px-4 py-3 grid grid-cols-[auto_1fr_auto] items-center gap-4">

    <!-- Izquierda: logo/título -->
    <div class="brand flex items-center gap-2">
      <!-- Pon tu logo en /public/logo.png -->
      <img src="/logo.png" alt="Archives Renamer" class="brand__logo" />
    </div>

    <!-- Centro: navegación -->
    <nav class="justify-self-center flex items-center gap-3" aria-label="Main">
      {#each pages as p}
        <button
          class={`nav-link ${$currentPage === p ? 'is-active' : ''}`}
          aria-current={$currentPage === p ? 'page' : undefined}
          on:click={() => currentPage.set(p)}
        >
          {DISPLAY[p] ?? p}
        </button>
      {/each}
    </nav>

    <!-- Derecha: sesión + rename -->
    <div class="justify-self-end flex items-center gap-2 text-sm text-gray-700">
      <span>Sesión: {displayName}</span>
      <button
        class="btn-link"
        type="button"
        on:click={renameSession}
        title="Renombrar sesión"
        aria-label="Renombrar sesión"
      >
        Rename
      </button>
    </div>
  </div>
</div>

<!-- ====== Contenedor de páginas (render dinámico) ====== -->
<main class="max-w-7xl mx-auto p-4 space-y-4">
  <svelte:component this={CurrentComponent} />
</main>
