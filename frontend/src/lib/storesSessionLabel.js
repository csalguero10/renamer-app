// src/lib/storesSessionLabel.js
import { writable } from "svelte/store";

export const sessionLabel = writable("");

export async function fetchSessionLabel(API_BASE, sessionId) {
  try {
    if (!API_BASE || !sessionId) return;
    const resp = await fetch(`${API_BASE}/session_label?session_id=${encodeURIComponent(sessionId)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    // asume { label: "..." } o algo similar
    sessionLabel.set((data && (data.label || data.name)) || "");
  } catch {
    // silencioso
  }
}
