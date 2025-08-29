import { writable, derived, get } from "svelte/store";
import { API_BASE, sessionId } from "./stores.js";

/**
 * Mapa: catalog_id -> entrada normalizada
 * Entrada normalizada (claves canónicas):
 *  - catalog_id
 *  - catalog_title
 *  - catalog_author
 *  - catalog_publication_year (number | string)
 *  - catalog_publisher
 *  - catalog_place
 *  - catalog_language
 *  - catalog_keywords
 */
export const catalogMap = writable({});

// ID detectado a partir de los nombres de archivo subidos (BO0624_XXXX)
export const detectedCatalogId = writable(null);

// ¿Hay CSV cargado?
export const csvLoaded = derived(catalogMap, ($m) => Object.keys($m).length > 0);

// Entrada detectada a partir del id detectado
export const detectedEntry = derived(
  [catalogMap, detectedCatalogId],
  ([$map, $id]) => ($id ? $map[$id] : null)
);

// Texto de estado para UI (CSV es OPCIONAL)
export const catalogStatusText = derived(
  [csvLoaded, detectedCatalogId, detectedEntry],
  ([$csv, $id, $entry]) => {
    if (!$csv) {
      return $id
        ? `CSV no cargado (opcional). ID detectado: ${$id}`
        : "CSV no cargado (opcional).";
    }
    if (!$id) return "Aún no se detecta un ID de catálogo.";
    if ($entry) return `Catálogo detectado: ${$entry.catalog_title || $id}`;
    return `ID de catálogo '${$id}' no encontrado en el CSV.`;
  }
);

/**
 * Sube un CSV al backend.
 * - Acepta que NO exista sessionId (el backend creará uno).
 * - Guarda en stores: sessionId (si viene), detectedCatalogId y catalogMap[entry].
 */
export async function uploadCatalogCSV(file) {
  if (!file) throw new Error("Selecciona un archivo CSV.");

  const form = new FormData();
  // Si ya tienes sessionId en el store, lo mandamos. Si no, el backend creará uno.
  form.append("session_id", get(sessionId) || "");
  // El backend acepta 'file' o 'csv'; usamos 'file'
  form.append("file", file);

  const resp = await fetch(`${get(API_BASE)}/upload_csv`, {
    method: "POST",
    body: form
  });

  const data = await resp.json();
  if (!resp.ok) {
    const msg = data?.error || "Error al subir el CSV.";
    throw new Error(msg);
  }

  // Si el backend creó una nueva sesión, la guardamos
  if (data.session_id) {
    sessionId.set(data.session_id);
  }

  // Si devolvió la entrada del catálogo, añadimos al mapa
  if (data.entry && data.entry.catalog_id) {
    catalogMap.update((m) => ({ ...m, [data.entry.catalog_id]: data.entry }));
  }

  // Actualiza id detectado si viene en la respuesta
  if (typeof data.detected_id !== "undefined") {
    detectedCatalogId.set(data.detected_id || null);
  }

  // Refresca estado por si ya había imágenes subidas
  await refreshCatalogStatus();

  return data; // devuelve ok, loaded, detected_id, entry...
}

/**
 * Consulta el backend para saber:
 * - id detectado actual
 * - entrada vinculada si existe
 */
export async function refreshCatalogStatus() {
  const sid = get(sessionId);
  if (!sid) return { detected_id: null, entry: null };

  const resp = await fetch(`${get(API_BASE)}/catalog_status?session_id=${sid}`);
  const data = await resp.json();

  if (!resp.ok) {
    // Si no hay sesión todavía, no es error grave.
    return { detected_id: null, entry: null };
  }

  if (data.entry && data.entry.catalog_id) {
    catalogMap.update((m) => ({ ...m, [data.entry.catalog_id]: data.entry }));
  }
  if (typeof data.detected_id !== "undefined") {
    detectedCatalogId.set(data.detected_id || null);
  }

  return data;
}

/**
 * Permite sobrescribir manualmente la entrada en memoria (por ejemplo, si el usuario edita campos).
 * Útil para reflejar cambios en la UI antes del export.
 */
export function upsertCatalogEntry(entry) {
  if (!entry || !entry.catalog_id) return;
  catalogMap.update((m) => ({ ...m, [entry.catalog_id]: { ...m[entry.catalog_id], ...entry } }));
  detectedCatalogId.set(entry.catalog_id);
}

/**
 * Borra todos los datos del catálogo en memoria (no obligatorio, por si lo necesitas).
 */
export function clearCatalog() {
  catalogMap.set({});
  detectedCatalogId.set(null);
}
