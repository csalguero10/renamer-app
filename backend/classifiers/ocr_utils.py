import pytesseract

def has_text(pil_image) -> bool:
    """Returns True if OCR detects some text-like content."""
    try:
        txt = pytesseract.image_to_string(pil_image, config="--psm 6")
        # Heuristic: consider text if there are at least a few letters/digits
        return sum(c.isalnum() for c in txt) >= 5
    except Exception:
        # if Tesseract missing, fall back to False
        return False
