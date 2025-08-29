<script>
  import Upload from "./pages/Upload.svelte";
  import Gallery from "./pages/Gallery.svelte";
  import Viewer from "./pages/Viewer.svelte";
  import ExportPage from "./pages/Export.svelte";
  import { currentPage, pages } from "./lib/stores.js";
</script>

<div class="max-w-7xl mx-auto p-4 space-y-4">
  <header class="flex items-center justify-between">
    <h1 class="text-2xl font-semibold">Archives Renamer</h1>
    <nav class="flex gap-2">
      {#each pages as p}
      <button class="btn" on:click={() => currentPage.set(p)}>{p}</button>
      {/each}
    </nav>
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

<style>
  /* ================================
     THEME (global)
     ================================ */
  :global(:root){
    --bg: #F8F9FA;
    --text: #1F2937;        /* gris oscuro legible */
    --muted: #6B7280;       /* gris medio */
    --border: #E5E7EB; 
    
    --primary: #586bc0;       /* base (violet-700) */
    --primary-700: #9b98f1;   /* hover/active (violet-800) */
    --primary-50: #F5F3FF;    /* tint suave para fondos/outline */
    --ring: rgba(50, 46, 124, 0.22); /* focus ring */
    --success: #63ddb4;/* gris clarísimo para bordes */

  }

  /* Inter de Google Fonts (con fallback seguro) */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  :global(html), :global(body){
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  :global(h1, h2, h3){
    letter-spacing: -0.01em; /* Jerarquía con leve tracking negativo */
    color: var(--text);
  }

  /* Encabezado: look más nítido sin cambiar estructura */
  :global(header){
    padding: .75rem 1rem;
    border-radius: 16px;
    background: #FFFFFF;
    box-shadow: 0 10px 24px rgba(15,23,42,.05), 0 2px 6px rgba(15,23,42,.03);
    border: 1px solid rgba(229,231,235,.6);
  }

  /* ================================
     COMPONENTES BASE (global)
     ================================ */

  /* Tarjetas/Contenedores */
  :global(.card){
    background: #FFFFFF;
    border-radius: 16px;             /* soft corners */
    padding: 1rem;                   /* respiración consistente */
    box-shadow: 0 10px 24px rgba(15,23,42,.05), 0 2px 6px rgba(15,23,42,.03);
    border: 1px solid rgba(229,231,235,.6); /* sutil: se percibe limpio */
  }

  /* Botón primario por defecto */
  :global(.btn){
    appearance: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: .5rem;
    padding: .55rem 1rem;
    border-radius: 10px;             /* más redondeado */
    border: 1px solid transparent;
    background: var(--primary);
    color: #fff;
    font-weight: 600;
    line-height: 1.1;
    transition: transform .12s ease, box-shadow .15s ease, background-color .15s ease, border-color .15s ease, opacity .15s ease;
    box-shadow: 0 8px 16px rgba(79,70,229,.18), 0 2px 4px rgba(79,70,229,.10);
    cursor: pointer;
    user-select: none;
  }
  :global(.btn:hover){
    background: var(--primary-700);
    box-shadow: 0 10px 22px rgba(79,70,229,.22), 0 3px 6px rgba(79,70,229,.12);
    transform: translateY(-1px);
  }
  :global(.btn:active){
    transform: translateY(0);
    box-shadow: 0 6px 12px rgba(79,70,229,.18), 0 2px 4px rgba(79,70,229,.10);
  }
  :global(.btn:focus-visible){
    outline: none;
    box-shadow: 0 0 0 4px var(--ring), 0 8px 16px rgba(79,70,229,.18);
  }
  :global(.btn[disabled]){
    opacity: .55;
    cursor: not-allowed;
    box-shadow: none;
  }

  /* Variante secundaria (por si la usas en otros lugares) */
  :global(.btn-outline){
    background: transparent;
    color: var(--primary);
    border: 1px solid var(--primary);
    box-shadow: none;
  }
  :global(.btn-outline:hover){
    background: var(--primary-50);
    box-shadow: 0 6px 14px rgba(79,70,229,.12);
  }

  /* Entradas y selects */
  :global(.input){
    width: 100%;
    background: #fff;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: .56rem .75rem;
    line-height: 1.2;
    transition: box-shadow .15s ease, border-color .15s ease, background-color .15s ease;
    box-shadow: inset 0 1px 2px rgba(15,23,42,.03);
  }
  :global(.input::placeholder){
    color: #9CA3AF;
  }
  :global(.input:focus){
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 4px var(--ring), inset 0 1px 2px rgba(15,23,42,.03);
  }
  :global(select.input){
    background-image: linear-gradient(45deg,transparent 50%,var(--muted) 50%), linear-gradient(135deg,var(--muted) 50%,transparent 50%), linear-gradient(to right,#fff,#fff);
    background-position: calc(100% - 18px) calc(1em + 2px), calc(100% - 13px) calc(1em + 2px), 100% 0;
    background-size: 5px 5px, 5px 5px, 2.5em 2.5em;
    background-repeat: no-repeat;
    padding-right: 2.25rem;
  }

  /* Chips/Insignias */
  :global(.badge){
    display: inline-flex;
    align-items: center;
    padding: .18rem .5rem;
    border-radius: 9999px;
    background: rgba(79,70,229,.10);
    color: var(--primary);
    font-weight: 600;
    font-size: .75rem;
    border: 1px solid rgba(79,70,229,.18);
  }

  /* Separadores y texto secundario */
  :global(hr){ border-color: var(--border); }
  :global(.text-muted), :global(.text-gray-600){ color: var(--muted) !important; }

  /* Imágenes dentro de tarjetas/miniaturas: bordes suaves */
  :global(img){
    border-radius: 10px;
  }

  /* Scrollbars sutiles (WebKit) sin cambiar estructura */
  :global(*::-webkit-scrollbar){
    height: 8px; width: 8px;
  }
  :global(*::-webkit-scrollbar-track){
    background: #eef0f3;
    border-radius: 10px;
  }
  :global(*::-webkit-scrollbar-thumb){
    background: #cfd6de;
    border-radius: 10px;
  }
  :global(*::-webkit-scrollbar-thumb:hover){
    background: #b8c0cb;
  }
</style>
