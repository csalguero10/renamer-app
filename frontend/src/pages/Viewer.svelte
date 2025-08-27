<script>
import { API_BASE, sessionId, items, toggleSelect } from "../lib/stores.js";
import { formatNumber } from "../lib/utils.js";
import { tick } from "svelte";

// ---------------- Estado ----------------
let currentIndex = 0;
$: ordered = $items;
$: current = ordered[currentIndex];

function prev() { if (currentIndex > 0) currentIndex--; }
function next() { if (currentIndex < ordered.length - 1) currentIndex++; }

// Atajos globales
function keyHandler(e) {
  if (e.key === "ArrowLeft") prev();
  if (e.key === "ArrowRight") next();
  if (e.key === " ") { e.preventDefault(); if (current) toggleSelect(current.id); }
  if (e.shiftKey && e.key === "ArrowRight") {
    const start = currentIndex, end = Math.min(ordered.length - 1, currentIndex + 1);
    for (let i = start; i <= end; i++) toggleSelect(ordered[i].id);
    currentIndex = end;
  }
  if (e.shiftKey && e.key === "ArrowLeft") {
    const start = Math.max(0, currentIndex - 1), end = currentIndex;
    for (let i = start; i <= end; i++) toggleSelect(ordered[i].id);
    currentIndex = start;
  }
}

// Guardar metadatos
async function updateItem(fields) {
  const payload = { session_id: $sessionId, updates: [{ id: current.id, ...fields }] };
  const resp = await fetch(`${$API_BASE}/validate`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  const data = await resp.json();
  items.set(data.items);
}

// ------------- Zoom + Pan -------------
let zoom = 1;
const Z_MIN = 0.1, Z_MAX = 6;
let viewportEl, imgEl;
let natW = 0, natH = 0;
let isImageLoaded = false;

let isPanning = false;
let panStartX = 0, panStartY = 0;
let panScrollLeft = 0, panScrollTop = 0;

// ------------- Carrusel de miniaturas -------------
let thumbnailContainer;
let thumbnailElements = {};
let canScrollLeft = false;
let canScrollRight = true;

// Actualizar botones de scroll según posición
function updateScrollButtons() {
  if (!thumbnailContainer) return;
  canScrollLeft = thumbnailContainer.scrollLeft > 0;
  canScrollRight = thumbnailContainer.scrollLeft < 
    (thumbnailContainer.scrollWidth - thumbnailContainer.clientWidth - 10);
}

// Scroll del carrusel
function scrollThumbnailsLeft() {
  if (!thumbnailContainer) return;
  thumbnailContainer.scrollLeft -= 300;
  setTimeout(updateScrollButtons, 100);
}

function scrollThumbnailsRight() {
  if (!thumbnailContainer) return;
  thumbnailContainer.scrollLeft += 300;
  setTimeout(updateScrollButtons, 100);
}

// Asegurar que la miniatura actual sea visible
async function scrollToThumbnail(index) {
  await tick();
  if (!thumbnailContainer || !thumbnailElements[index]) return;
  
  const container = thumbnailContainer;
  const element = thumbnailElements[index];
  const elementRect = element.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  
  // Si el elemento está fuera de vista por la izquierda
  if (elementRect.left < containerRect.left) {
    container.scrollLeft -= (containerRect.left - elementRect.left) + 50;
  }
  // Si el elemento está fuera de vista por la derecha
  else if (elementRect.right > containerRect.right) {
    container.scrollLeft += (elementRect.right - containerRect.right) + 50;
  }
  
  setTimeout(updateScrollButtons, 100);
}

function setZoom(z) { 
  zoom = Math.min(Z_MAX, Math.max(Z_MIN, z)); 
}

async function zoomTo(newZoom, anchorX, anchorY) {
  if (!viewportEl || !isImageLoaded) return;
  const oldZoom = zoom;
  const contentX = viewportEl.scrollLeft + anchorX;
  const contentY = viewportEl.scrollTop + anchorY;
  setZoom(newZoom);
  await tick();
  const scale = zoom / oldZoom;
  viewportEl.scrollLeft = contentX * scale - anchorX;
  viewportEl.scrollTop = contentY * scale - anchorY;
}

function zoomIn() { 
  if (!viewportEl || !isImageLoaded) return;
  zoomTo(zoom * 1.2, viewportEl.clientWidth/2, viewportEl.clientHeight/2); 
}

function zoomOut() { 
  if (!viewportEl || !isImageLoaded) return;
  zoomTo(zoom / 1.2, viewportEl.clientWidth/2, viewportEl.clientHeight/2); 
}

// Ajustar imagen completa al contenedor
async function fitToView() {
  if (!viewportEl || !imgEl || !natW || !natH) return;
  
  await tick();
  
  // Obtener dimensiones del viewport sin padding
  const cs = getComputedStyle(viewportEl);
  const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  const availW = Math.max(0, viewportEl.clientWidth - padX);
  const availH = Math.max(0, viewportEl.clientHeight - padY);
  
  // Calcular zoom para que la imagen quepa completa
  const scaleX = availW / natW;
  const scaleY = availH / natH;
  const optimalZoom = Math.min(scaleX, scaleY) * 0.95; // 95% para tener un pequeño margen
  
  setZoom(optimalZoom);
  await tick();
  
  // Centrar la imagen
  centerImage();
}

// Centrar imagen en el viewport
async function centerImage() {
  if (!viewportEl || !natW || !natH) return;
  
  await tick();
  
  const cs = getComputedStyle(viewportEl);
  const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  const availW = Math.max(0, viewportEl.clientWidth - padX);
  const availH = Math.max(0, viewportEl.clientHeight - padY);
  
  const contentW = natW * zoom;
  const contentH = natH * zoom;
  
  // Centrar horizontalmente
  viewportEl.scrollLeft = Math.max(0, (contentW - availW) / 2);
  
  // Centrar verticalmente
  viewportEl.scrollTop = Math.max(0, (contentH - availH) / 2);
}

// Zoom 100%
function resetZoom() {
  setZoom(1);
  centerImage();
}

// Rueda del mouse (anclada al cursor)
function handleWheel(e) {
  e.preventDefault();
  if (!viewportEl || !isImageLoaded) return;
  const rect = viewportEl.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const factor = e.deltaY < 0 ? 1.1 : 0.9;
  zoomTo(zoom * factor, x, y);
}

// Pan por arrastre
function onMouseDown(e) {
  if (e.button !== 0 || !viewportEl) return;
  isPanning = true;
  viewportEl.classList.add("cursor-grabbing");
  viewportEl.classList.remove("cursor-grab");
  panStartX = e.clientX; 
  panStartY = e.clientY;
  panScrollLeft = viewportEl.scrollLeft; 
  panScrollTop = viewportEl.scrollTop;
  e.preventDefault();
}

function onMouseMove(e) {
  if (!isPanning || !viewportEl) return;
  const dx = e.clientX - panStartX;
  const dy = e.clientY - panStartY;
  viewportEl.scrollLeft = panScrollLeft - dx;
  viewportEl.scrollTop = panScrollTop - dy;
}

function onMouseUp() {
  if (!viewportEl) return;
  isPanning = false;
  viewportEl.classList.remove("cursor-grabbing");
  viewportEl.classList.add("cursor-grab");
}

// Re-ajustar en resize
function onResize() { 
  if (isImageLoaded) {
    fitToView(); 
  }
}

// Al cargar imagen, capturar tamaño natural y ajustar
async function onImgLoad() {
  isImageLoaded = true;
  natW = imgEl.naturalWidth || 1;
  natH = imgEl.naturalHeight || 1;
  await fitToView();
}

// Cuando cambia la imagen actual, resetear estado
$: if (current) {
  isImageLoaded = false;
  scrollToThumbnail(currentIndex);
  // El ajuste se hará automáticamente en onImgLoad
}

// Actualizar estado de botones al montar y al cambiar items
$: if ($items && thumbnailContainer) {
  setTimeout(updateScrollButtons, 100);
}

// Tipos
const types = ["portada","contraportada","guardas","velinas","frontispicio","texto","ilustración","inserto","página blanca","referencia","sin-tipo"];
</script>

<svelte:window on:keydown={keyHandler} on:mouseup={onMouseUp} on:resize={onResize} />

<div class="card" role="region" aria-label="Visor de imagen">
  <div class="grid md:grid-cols-5 gap-4">
    <!-- Imagen grande -->
    <div class="md:col-span-4">
      {#if current}
        <div class="flex items-center justify-between mb-2">
          <div class="text-sm text-gray-600 truncate">{current.original_filename}</div>
          <div class="flex gap-2 items-center">
            <button 
              class="btn px-3 py-1 text-xs" 
              on:click={fitToView} 
              aria-label="Ajustar"
              title="Ajustar imagen completa"
            >
              ⊡
            </button>
            <button 
              class="btn px-3 py-1 text-xs" 
              on:click={resetZoom} 
              aria-label="100%"
              title="Zoom 100%"
            >
              100%
            </button>
            <button 
              class="btn px-3 py-1" 
              on:click={zoomOut} 
              aria-label="Alejar"
              title="Alejar (scroll down)"
            >
              −
            </button>
            <span class="text-sm text-gray-600 min-w-[50px] text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button 
              class="btn px-3 py-1" 
              on:click={zoomIn} 
              aria-label="Acercar"
              title="Acercar (scroll up)"
            >
              +
            </button>
          </div>
        </div>

        <!-- Viewport con imagen centrada -->
        <div
          bind:this={viewportEl}
          class="w-full overflow-auto border rounded-2xl bg-black/5 h-[65vh] cursor-grab p-4 relative"
          on:wheel={handleWheel}
          on:mousedown={onMouseDown}
          on:mousemove={onMouseMove}
          role="region"
          aria-label="Área de visualización de imagen"
        >
          <!-- Contenedor flex para centrar cuando la imagen es más pequeña -->
          <div 
            class="min-w-full min-h-full flex items-center justify-center"
            style="width: {natW * zoom}px; height: {natH * zoom}px;"
          >
            <img
              bind:this={imgEl}
              src={`${$API_BASE}/file_preview/${$sessionId}/${current.id}?w=1600`}
              alt={`Vista de ${current?.original_filename || ''}`}
              style="width: {natW * zoom}px; height: {natH * zoom}px;"
              class="max-w-none rounded-xl select-none block"
              draggable="false"
              on:load={onImgLoad}
            />
          </div>
          
          <!-- Indicador de carga -->
          {#if !isImageLoaded}
            <div class="absolute inset-0 flex items-center justify-center bg-white/50 rounded-2xl">
              <div class="text-gray-600">Cargando imagen...</div>
            </div>
          {/if}
        </div>

        <div class="flex justify-between mt-2">
          <button class="btn" on:click={prev} disabled={currentIndex === 0}>
            ← Anterior
          </button>
          <span class="text-sm text-gray-600 self-center">
            {currentIndex + 1} / {ordered.length}
          </span>
          <button class="btn" on:click={next} disabled={currentIndex === ordered.length - 1}>
            Siguiente →
          </button>
        </div>
      {/if}
    </div>

    <!-- Panel lateral -->
    <aside class="md:col-span-1 space-y-2">
      {#if current}
        <div class="card">
          <h3 class="font-semibold mb-2">Metadatos</h3>

          <label class="block text-sm mb-1" for="pageType">Tipo de página</label>
          <select 
            id="pageType" 
            class="input w-full mb-2" 
            bind:value={current.type} 
            on:change={(e)=>updateItem({type: e.target.value})}
          >
            {#each types as t}<option value={t}>{t}</option>{/each}
          </select>

          <label class="block text-sm mb-1" for="pageNumber">Numeración</label>
          <div class="flex gap-2 mb-2">
            <input 
              id="pageNumber" 
              class="input w-24" 
              type="number" 
              placeholder="nº" 
              bind:value={current.page_number} 
              on:change={(e)=>updateItem({page_number: parseInt(e.target.value)})} 
            />
            <label class="sr-only" for="scheme">Esquema</label>
            <select 
              id="scheme" 
              class="input" 
              bind:value={current.number_scheme} 
              on:change={(e)=>updateItem({number_scheme: e.target.value})}
            >
              <option value="arabic">Arábiga</option>
              <option value="roman">Romana</option>
            </select>
          </div>

          <label class="block text-sm mb-1" for="extra">Extra</label>
          <input 
            id="extra" 
            class="input w-full mb-2" 
            placeholder="bis, a, v" 
            bind:value={current.extra} 
            on:change={(e)=>updateItem({extra: e.target.value})} 
          />

          <div class="flex items-center gap-2 mb-2">
            <input 
              id="ghost" 
              type="checkbox" 
              checked={current.ghost_number} 
              on:change={(e)=>updateItem({ghost_number: e.target.checked})} 
            />
            <label for="ghost">Número fantasma</label>
          </div>

          <div class="flex items-center gap-2 mb-2">
            <input 
              id="graphic" 
              type="checkbox" 
              checked={current.graphic} 
              on:change={(e)=>updateItem({graphic: e.target.checked})} 
            />
            <label for="graphic">Gráfico</label>
          </div>

          <div class="flex items-center gap-2">
            <input 
              id="validated" 
              type="checkbox" 
              checked={current.validated} 
              on:change={(e)=>updateItem({validated: e.target.checked})} 
            />
            <label for="validated">Validada</label>
          </div>

          <div class="mt-2 text-xs text-gray-600">
            Vista previa token:
            {#if current.page_number}
              {formatNumber(parseInt(current.page_number), current.number_scheme, current.ghost_number)}
            {/if}
            {current.extra}
          </div>
        </div>
      {/if}
    </aside>
  </div>

  <!-- Carrusel de miniaturas -->
  <div class="mt-4 relative bg-gray-50 rounded-xl p-2">
    <div class="flex items-center gap-2">
      <!-- Botón izquierdo del carrusel -->
      <button
        class="flex-shrink-0 w-8 h-32 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
        on:click={scrollThumbnailsLeft}
        disabled={!canScrollLeft}
        aria-label="Desplazar miniaturas a la izquierda"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      
      <!-- Contenedor de miniaturas con scroll -->
      <div 
        bind:this={thumbnailContainer}
        class="flex-1 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-200"
        style="scroll-behavior: smooth;"
        on:scroll={updateScrollButtons}
      >
        <div class="flex gap-2 py-1">
          {#each $items as it, i}
            <div
              bind:this={thumbnailElements[i]}
              class={`flex-shrink-0 border-2 rounded-xl p-1 cursor-pointer transition-all ${
                i === currentIndex 
                  ? 'border-blue-500 shadow-lg scale-105 bg-blue-50' 
                  : 'border-gray-300 hover:shadow-md hover:border-gray-400'
              }`}
              role="button"
              tabindex="0"
              on:click={() => { currentIndex = i; scrollToThumbnail(i); }}
              on:keydown={(e) => { 
                if (e.key === 'Enter' || e.key === ' ') { 
                  e.preventDefault(); 
                  currentIndex = i;
                  scrollToThumbnail(i);
                } 
              }}
            >
              <div class="w-24 flex flex-col">
                <img 
                  class="w-full h-24 object-cover rounded-md" 
                  src={`${$API_BASE}/thumb/${$sessionId}/${it.id}`} 
                  alt={it.original_filename}
                  loading="lazy"
                />
                <div class="text-[10px] text-center truncate mt-1 px-1">
                  {it.original_filename}
                </div>
                <div class="text-[9px] text-center text-gray-500">
                  {i + 1}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
      
      <!-- Botón derecho del carrusel -->
      <button
        class="flex-shrink-0 w-8 h-32 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
        on:click={scrollThumbnailsRight}
        disabled={!canScrollRight}
        aria-label="Desplazar miniaturas a la derecha"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
    
    <!-- Indicador de posición -->
    <div class="text-center text-xs text-gray-500 mt-2">
      {currentIndex + 1} de {ordered.length} imágenes
    </div>
  </div>
</div>

<style>
  /* Estilos adicionales si necesitas */
  .cursor-grab {
    cursor: grab;
  }
  
  .cursor-grabbing {
    cursor: grabbing !important;
  }
  
  /* Transición suave al cambiar de imagen */
  img {
    transition: opacity 0.2s ease-in-out;
  }
  
  /* Personalización de la barra de scroll */
  .scrollbar-thin {
    scrollbar-width: thin;
  }
  
  .scrollbar-thin::-webkit-scrollbar {
    height: 6px;
  }
  
  .scrollbar-thin::-webkit-scrollbar-track {
    background: #e5e7eb;
    border-radius: 3px;
  }
  
  .scrollbar-thin::-webkit-scrollbar-thumb {
    background: #9ca3af;
    border-radius: 3px;
  }
  
  .scrollbar-thin::-webkit-scrollbar-thumb:hover {
    background: #6b7280;
  }
</style>