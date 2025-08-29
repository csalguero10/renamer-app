import { writable, derived, get } from "svelte/store";
import { API_BASE, sessionId } from "./stores.js";

// Mapa de id_catalogo -> entrada de catálogo
export const catalogMap = writable({});
export const detectedCatalogId = writable(null);

// ¿Hay CSV cargado?
export const csvLoaded = derived(catalogMap, ($m) => Object.keys($m).length > 0);

// Entrada detectada (si hay)
export const detectedEntry = derived(
    [catalogMap, detectedCatalogId],
    ([$map, $id]) => ($id ? $map[$id] : null)
);

// Texto de estado (CSV opcional)
export const catalogStatusText = derived(
    [csvLoaded, detectedCatalogId, detectedEntry],
    ([$csv, $id, $entry]) => {
        if (!$csv) {
            // CSV no cargado: opcional
            return $id
                ? `CSV not loaded (optional). Detected catalog ID: ${$id}`
                : "CSV not loaded (optional).";
        }
        if (!$id) return "No catalog ID detected yet.";
        if ($entry) return `Catalog detected: ${$entry.catalog_title || $id}`;
        return `Catalog ID '${$id}' not found in CSV.`;
    }
);

// ---------- API helpers ----------
export async function uploadCatalogCSV(file) {
    const form = new FormData();
    form.append("session_id", get(sessionId) || "");
    form.append("file", file);

    const resp = await fetch(`${get(API_BASE)}/upload_csv`, { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "CSV upload failed");
    await refreshCatalogStatus();
    return data;
}

export async function refreshCatalogStatus() {
    const sid = get(sessionId);
    if (!sid) return { detected_id: null, entry: null };
    const resp = await fetch(`${get(API_BASE)}/catalog_status?session_id=${sid}`);
    const data = await resp.json();

    if (data.entry && data.entry.catalog_id) {
        catalogMap.update(m => ({ ...m, [data.entry.catalog_id]: data.entry }));
    }
    if (typeof data.detected_id !== "undefined") {
        detectedCatalogId.set(data.detected_id || null);
    }
    return data;
}
