# utils/ocr_utils.py
# ------------------------------------------------------------
# OCR robusto con pytesseract:
# - Preprocesado ligero
# - Métricas: word_count, char_count, avg_conf
# - Funciona aunque Tesseract no esté instalado (devuelve 0)
# ------------------------------------------------------------

from typing import Dict, Any
import numpy as np
import cv2
from PIL import Image, ImageOps

try:
    import pytesseract
    TESS_AVAILABLE = True
except Exception:
    pytesseract = None
    TESS_AVAILABLE = False


def _pil_to_cv_gray(pil_img: Image.Image) -> np.ndarray:
    im = ImageOps.exif_transpose(pil_img)
    g = im.convert("L")
    return np.array(g)


def _prep_for_ocr(gray: np.ndarray) -> np.ndarray:
    """
    Preprocesado sencillo:
      - upscale suave si imagen muy pequeña
      - blur ligero
      - umbral Otsu (binario)
    """
    h, w = gray.shape[:2]
    min_side = min(h, w)
    # Upscale hasta ~1200px el lado corto para dar más señales al OCR
    if min_side < 1200:
        scale = 1200 / float(min_side)
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Tesseract suele preferir texto oscuro sobre claro; invertimos si hace falta:
    white_ratio = float((th == 255).mean())
    if white_ratio < 0.5:  # si predominan negros, invertir
        th = cv2.bitwise_not(th)

    return th


def get_text_stats(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Devuelve métricas de OCR:
      - word_count: nº de palabras detectadas (tokens alfanum >=2)
      - char_count: suma de longitudes de tokens válidos
      - avg_conf: confianza media (si disponible)
      - ocr_available: bool
    Si pytesseract no está disponible, retorna 0s de forma segura.
    """
    if not TESS_AVAILABLE or pil_img is None:
        return {"word_count": 0, "char_count": 0, "avg_conf": None, "ocr_available": False}

    try:
        gray = _pil_to_cv_gray(pil_img)
        img = _prep_for_ocr(gray)

        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            lang="spa+eng"  # ajusta según tus materiales
        )
        n = len(data.get("text", []))
        words = []
        confs = []
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if len([ch for ch in txt if ch.isalnum()]) >= 2:
                # conf puede ser "-1" cuando es ruido; ignorar
                conf = float(data.get("conf", ["-1"])[i])
                if conf >= 0:
                    words.append(txt)
                    confs.append(conf)

        word_count = len(words)
        char_count = sum(len(w) for w in words)
        avg_conf = (sum(confs) / len(confs)) if confs else None

        return {
            "word_count": int(word_count),
            "char_count": int(char_count),
            "avg_conf": (float(avg_conf) if avg_conf is not None else None),
            "ocr_available": True
        }
    except Exception:
        # Falla silenciosa: preferimos no romper la clasificación
        return {"word_count": 0, "char_count": 0, "avg_conf": None, "ocr_available": TESS_AVAILABLE}
