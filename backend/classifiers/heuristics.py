# classifiers/heuristics.py
# ------------------------------------------------------------
# Heurísticas robustas para:
# 1) Detectar páginas "en blanco" -> basado en bordes + contornos, NO en color absoluto.
# 2) Distinguir "ilustración" vs "texto" combinando densidad
#    de bordes con OCR (cantidad de palabras).
# ------------------------------------------------------------

import numpy as np
import cv2
from PIL import Image, ImageOps

from classifiers.ocr_utils import get_text_stats  # devuelve dict con word_count, etc.

CATEGORIES = [
    "portada", "contraportada", "guardas", "velinas",
    "frontispicio", "texto", "ilustración", "inserto",
    "página blanca", "referencia"
]

# ---------- Utilidades de imagen ----------

def to_gray_np(pil_img: Image.Image) -> np.ndarray:
    """Convierte a escala de grises (corrigiendo orientación EXIF)."""
    im = ImageOps.exif_transpose(pil_img)
    g = im.convert("L")
    return np.array(g)


def is_low_contrast(gray_arr: np.ndarray) -> bool:
    """Heurística simple de bajo contraste (papel translúcido, velinas)."""
    return float(gray_arr.std()) < 8.0


def edge_density(gray_arr: np.ndarray) -> float:
    """Proporción de píxeles detectados como borde por Canny."""
    blur = cv2.GaussianBlur(gray_arr, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)
    # edges es binario {0,255}; usar >0 para contar pixeles borde:
    return float((edges > 0).mean())


def color_variance(pil_img: Image.Image) -> float:
    """Varianza global de color (indicador muy grueso)."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    arr = np.array(pil_img)
    return float(arr.std())


# ---------- Páginas en blanco (estructura, no color) ----------

def is_blank_from_gray(gray_arr: np.ndarray) -> bool:
    """
    Detecta “página en blanco” basándose en ausencia de estructura:
    - Suavizado + Canny
    - Conteo de píxeles-borde (edge ratio)
    - Conteo de contornos significativos (tras ligera dilatación)
    Considera variaciones de papel envejecido/sombras.

    Umbrales recomendados (ajustables):
      - edge_ratio < 0.004  (0.4%)
      - contour_density_per_mp < 150 contornos / Mpx
    """
    if gray_arr is None or gray_arr.size == 0:
        return False

    # Suavizado leve para no contar ruido fino
    blur = cv2.GaussianBlur(gray_arr, (3, 3), 0)

    # Bordes: Canny conservador
    edges = cv2.Canny(blur, 40, 120)
    edge_ratio = float((edges > 0).mean())

    # Dilatamos un poco los bordes para consolidar trazos finos
    dil = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    # Contornos (sólo externos, sin jerarquía)
    cnts, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtramos contornos muy diminutos (polvo/ruido)
    MIN_AREA = 25  # px
    significant = [c for c in cnts if cv2.contourArea(c) >= MIN_AREA]

    # Densidad por megapíxel para ser invariante al tamaño
    mpix = gray_arr.size / 1_000_000.0
    contour_density_per_mp = (len(significant) / mpix) if mpix > 0 else len(significant)

    # UMBRALES CLAVE (ajustables):
    BLANK_EDGE_MAX = 0.004    # 0.4% de pixeles como borde
    BLANK_CNT_MAX = 150.0     # 150 contornos / Mpx

    return (edge_ratio < BLANK_EDGE_MAX) and (contour_density_per_mp < BLANK_CNT_MAX)


def is_blank_page(pil_or_path) -> bool:
    """
    API “amigable”: acepta PIL.Image o ruta.
    Internamente evalúa con la versión por array en gris.
    """
    if isinstance(pil_or_path, Image.Image):
        gray = to_gray_np(pil_or_path)
        return is_blank_from_gray(gray)

    # Si llega ruta:
    img = cv2.imread(str(pil_or_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False
    return is_blank_from_gray(img)


# ---------- Clasificación principal ----------

def guess_type(pil_img: Image.Image, original_name: str, index: int, total: int, neighbors_names):
    """
    Flujo mejorado:
      1) Reglas por nombre/posición
      2) Detección de “página blanca” estructural
      3) Velinas (bajo contraste + alto brillo medio)
      4) Densidad de bordes + OCR:
         - Si bordes altos y OCR detecta poco texto -> ilustración
         - Si OCR detecta mucho texto -> texto (o frontispicio por hint)
      5) Fallbacks
    """
    # -------- Hints por nombre ----------
    name_l = (original_name or "").lower()
    if "ins" in name_l:
        return "inserto"
    if "ref" in name_l:
        return "referencia"

    # -------- Hints por posición ----------
    if (
        index == 0
        or name_l.endswith("_000001.jpg")
        or name_l.endswith("_000001.png")
        or name_l.endswith("_000001.tif")
        or name_l.endswith("_000001.tiff")
    ):
        return "portada"

    if total >= 2 and index == 1:
        # segunda imagen frecuentemente son "guardas"
        return "guardas"

    if 0 < index < total - 1:
        # Heurística muy simple para contraportada: anterior a ref/ins
        next_name = (neighbors_names[index + 1] or "").lower()
        if ("ref" in next_name) or ("ins" in next_name):
            return "contraportada"

    # -------- Análisis de imagen ----------
    gray = to_gray_np(pil_img)

    # 2) Página “en blanco” (estructura, no color)
    if is_blank_from_gray(gray):
        return "página blanca"

    # 3) Velinas / páginas translúcidas muy claras
    if is_low_contrast(gray) and float(gray.mean()) > 210.0:
        return "velinas"

    # 4) Bordes + OCR para diferenciar ilustración vs texto
    ed = edge_density(gray)

    # OCR stats (robusto a falta de Tesseract; ver ocr_utils)
    ocr = get_text_stats(pil_img)
    word_count = int(ocr.get("word_count", 0))
    # avg_conf = ocr.get("avg_conf", None)  # disponible si quieres afinación futura

    # UMBRALES (ajustables):
    EDGE_ILLUST = 0.05   # 5% de pixeles-borde ~ imagen rica en detalle
    WORDS_TEXT  = 20     # >=20 palabras => muy probablemente página de texto

    if ed > EDGE_ILLUST and word_count < WORDS_TEXT:
        # Muchos bordes pero muy poco texto -> ilustración
        return "ilustración"

    # Si OCR ve suficiente texto, es texto (o frontispicio si hint)
    if word_count >= WORDS_TEXT:
        if "front" in name_l or "frontis" in name_l:
            return "frontispicio"
        return "texto"

    # 5) Fallbacks: usa señales débiles restantes
    #    (mejor inclinarse hacia "texto" para minimizar falsos positivos de ilustración)
    if color_variance(pil_img) > 40.0 and ed > 0.02 and word_count < 10:
        return "ilustración"

    return "texto"
