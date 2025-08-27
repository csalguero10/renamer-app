import { writable, derived } from "svelte/store";

export const API_BASE = writable(import.meta.env.VITE_API_BASE || "http://localhost:5001");

export const sessionId = writable(null);
export const items = writable([]); // [{ id, original_filename, type, page_number, number_scheme, extra, ghost_number, validated, graphic, new_filename }]
export const selection = writable(new Set()); // set of ids

export const currentPage = writable("Upload");
export const pages = ["Upload", "Galería", "Visor", "Exportar"];

export function toggleSelect(id) {
  selection.update(s => {
    const ns = new Set(s);
    if (ns.has(id)) ns.delete(id);
    else ns.add(id);
    return ns;
  });
}

export function clearSelection() {
  selection.set(new Set());
}
