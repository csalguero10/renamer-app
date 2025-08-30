// Muestra un nombre de sesión agradable:
// 1) etiqueta guardada (si existe)
// 2) ID de catálogo detectado (si existe)
// 3) fallback compacto: 8 chars del UUID sin guiones (en mayúsculas)
export function niceSession(sessionId, sessionLabel, detectedCatalogId) {
  if (sessionLabel && sessionLabel.trim()) return sessionLabel.trim();
  if (detectedCatalogId && detectedCatalogId.trim()) return detectedCatalogId.trim();
  if (!sessionId) return "—";
  const compact = sessionId.replace(/-/g, "").slice(0, 8).toUpperCase();
  return compact;
}
