import os, numpy as np, cv2
from PIL import Image
from .ocr_utils import has_text

CATEGORIES = [
    "portada", "contraportada", "guardas", "velinas",
    "frontispicio", "texto", "ilustración", "inserto",
    "página blanca", "referencia"
]

def is_white_page(gray_arr) -> bool:
    # >90% of pixels are very bright and low variance
    thresh = 240
    white_ratio = (gray_arr >= thresh).mean()
    return white_ratio > 0.90

def is_low_contrast(gray_arr) -> bool:
    return gray_arr.std() < 8

def edge_density(gray_arr) -> float:
    edges = cv2.Canny(gray_arr, 50, 150)
    return edges.mean() / 255.0

def color_variance(pil_img) -> float:
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    arr = np.array(pil_img)
    return float(arr.std())

def guess_type(pil_img: Image.Image, original_name: str, index: int, total: int, neighbors_names):
    # Filename based hints
    name_l = original_name.lower()
    if "ins" in name_l:
        return "inserto"
    if "ref" in name_l:
        return "referencia"

    # Positional hints
    if index == 0 or original_name.endswith("_000001.jpg") or original_name.endswith("_000001.png") or original_name.endswith("_000001.tif") or original_name.endswith("_000001.tiff"):
        return "portada"
    if total >= 2 and index == 1:
        # Frequent guardas
        return "guardas"

    # For contraportada: image before a name with ref/ins
    if index > 0 and index < total-1:
        next_name = neighbors_names[index + 1].lower()
        if ("ref" in next_name) or ("ins" in next_name):
            return "contraportada"

    # Image analysis
    gray = pil_img.convert("L")
    arr = np.array(gray)
    if is_white_page(arr):
        return "página blanca"
    if is_low_contrast(arr) and np.mean(arr) > 220:
        return "velinas"

    # Text detection
    if has_text(pil_img):
        # frontispicio is rare; keep as texto unless name hints
        if "front" in name_l or "frontis" in name_l:
            return "frontispicio"
        return "texto"

    # Illustration: many edges and/or color var
    if edge_density(arr) > 0.05 or color_variance(pil_img) > 40.0:
        return "ilustración"

    # Default fallbacks
    return "texto"
