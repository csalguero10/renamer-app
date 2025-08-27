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
