// src/lib/catalogStore.js
import { writable, derived, get } from "svelte/store";
import { API_BASE, sessionId } from "./stores.js";

/**
 * Estado de CSV / Catálogo
 * - csvLoaded: bandera real (no derivada) de si se ha cargado un CSV
 * - detectedCatalogId: id detectado a partir de las imágenes
 * - serverEntry: entrada proveniente del servidor/CSV para el id detectado
 * - manualOverrides: overrides manuales por id (toman prioridad)
 * - catalogMap: mapa auxiliar (compatibilidad) id -> última entrada conocida del servidor
 */
export const csvLoaded = writable(false);
export const detectedCatalogId = writable(null);
export const serverEntry = writable(null);
export const manualOverrides = writable({});
export const catalogMap = writable({}); // mantenido por compatibilidad

/**
 * detectedEntry (vista efectiva):
 * - Si hay overrides manuales para el id detectado => PRIORIDAD
 * - Si no, usa serverEntry
 * - Si no, null
 */
export const detectedEntry = derived(
  [detectedCatalogId, serverEntry, manualOverrides],
  ([$id, $server, $manual]) => {
    if (!$id) return null;
    const manual = $manual?.[$id];
    if (manual) return { ...($server || {}), ...manual, catalog_id: $id };
    if ($server) return { ...$server, catalog_id: $id };
    return null;
  }
);

/**
 * Texto de estado para UI:
 * - No asume que haya CSV (opcional)
 * - Muestra título si existe, si no el ID detectado
 */
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

/** Sube el CSV al backend y actualiza estado */
export async function uploadCatalogCSV(file) {
  if (!file) throw new Error("Selecciona un archivo CSV.");

  const api = get(API_BASE);
  const sid = get(sessionId) || "";
  const form = new FormData();
  form.append("session_id", sid);
  form.append("file", file);

  const resp = await fetch(`${api}/upload_csv`, { method: "POST", body: form });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data?.error || "Error al subir el CSV.");

  // Si el backend creó una sesión, persistirla
  if (data.session_id) sessionId.set(data.session_id);

  // Marcar que HAY CSV cargado
  csvLoaded.set(true);

  // Guardar id detectado si lo hay
  if (typeof data.detected_id !== "undefined") {
    detectedCatalogId.set(data.detected_id || null);
  }

  // Guardar entry del servidor (para el id detectado)
  if (data.entry && data.entry.catalog_id) {
    serverEntry.set(data.entry);
    // Mantener compatibilidad con 'catalogMap'
    catalogMap.update(m => ({ ...m, [data.entry.catalog_id]: data.entry }));
  } else {
    serverEntry.set(null);
  }

  // Por si ya había imágenes, refrescar estado del backend (no pisa overrides)
  await refreshCatalogStatus();

  return data;
}

/** Consulta el backend por id detectado y su entry; no pisa overrides */
export async function refreshCatalogStatus() {
  const sid = get(sessionId);
  if (!sid) return { detected_id: null, entry: null };

  const api = get(API_BASE);
  const resp = await fetch(`${api}/catalog_status?session_id=${encodeURIComponent(sid)}`);
  const data = await resp.json();

  if (!resp.ok) {
    // No hay sesión todavía o error leve; no rompas la UI
    return { detected_id: null, entry: null };
  }

  if (typeof data.detected_id !== "undefined") {
    detectedCatalogId.set(data.detected_id || null);
  }

  if (data.entry && data.entry.catalog_id) {
    serverEntry.set(data.entry);
    // Mantener compat con 'catalogMap'
    catalogMap.update(m => ({ ...m, [data.entry.catalog_id]: data.entry }));
  } else {
    serverEntry.set(null);
  }

  // Nota: aquí NO tocamos csvLoaded; no podemos inferirlo de este endpoint.
  return data;
}

/**
 * Guarda overrides manuales por id.
 * - Toman prioridad automáticamente en 'detectedEntry'
 * - Asegura que el id manual se vuelva el detectado (para que la UI lo use)
 */
export function upsertCatalogEntry(entry) {
  const id = entry?.catalog_id;
  if (!id) return;

  manualOverrides.update(map => ({
    ...map,
    [id]: { ...(map[id] || {}), ...entry, catalog_id: id }
  }));

  // Si el usuario cambia el ID manualmente, hacemos que la UI apunte a ese ID
  detectedCatalogId.set(id);

  // No tocamos serverEntry; detectedEntry ya prioriza overrides.
  return entry;
}

/** Limpia todo el estado del catálogo (por si lo necesitas) */
export function clearCatalog() {
  csvLoaded.set(false);
  detectedCatalogId.set(null);
  serverEntry.set(null);
  manualOverrides.set({});
  catalogMap.set({});
}

export function makeExportCatalogOverride(
  detectedId,
  formValues = {}
) {
  const m = get(catalogMap);

  // ID efectivo: lo que venga del form o el detectado
  const effId = (formValues.catalog_id ?? detectedId ?? "").toString().trim();
  const baseEntry = effId && m[effId] ? m[effId] : {};

  const take = (k) => {
    const fv = formValues[k];
    if (fv !== undefined && fv !== null && String(fv).trim() !== "") {
      return String(fv).trim();
    }
    if (baseEntry && baseEntry[k] !== undefined && baseEntry[k] !== null && String(baseEntry[k]).trim() !== "") {
      return String(baseEntry[k]).trim();
    }
    return "";
  };

  const parseYear = (v) => {
    if (v === null || v === undefined || String(v).trim() === "") return null;
    const n = parseInt(String(v).trim(), 10);
    return Number.isFinite(n) ? n : null;
  };

  return {
    catalog_id: effId || null,
    catalog_title: take("catalog_title"),
    catalog_author: take("catalog_author"),
    catalog_publication_year: parseYear(formValues.catalog_publication_year ?? baseEntry.catalog_publication_year),
    catalog_publisher: take("catalog_publisher"),
    catalog_place: take("catalog_place"),
    catalog_language: take("catalog_language"),
    catalog_keywords: take("catalog_keywords"),
  };
}
