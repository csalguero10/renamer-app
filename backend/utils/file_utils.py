import os, uuid, shutil
from PIL import Image

ALLOWED = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

def is_allowed(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED

def ensure_session_dirs(workspace: str, session_id: str):
    session_dir = os.path.join(workspace, session_id)
    os.makedirs(session_dir, exist_ok=True)
    orig_dir = os.path.join(session_dir, "originals")
    os.makedirs(orig_dir, exist_ok=True)
    return session_dir, orig_dir

def save_upload(file_storage, dest_dir: str) -> str:
    filename = file_storage.filename
    dest = os.path.join(dest_dir, filename)
    # If duplicate names appear, disambiguate
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(dest):
        dest = os.path.join(dest_dir, f"{base}({i}){ext}")
        i += 1
    file_storage.save(dest)
    return dest

def read_image_grayscale(path: str):
    from PIL import Image
    im = Image.open(path)
    if im.mode not in ("L", "LA"):
        im = im.convert("L")
    return im

def pil_to_cv2_gray(pil_img):
    import numpy as np, cv2
    arr = np.array(pil_img)
    return arr  # already grayscale

def thumb_path(session_dir: str, image_id: str) -> str:
    return os.path.join(session_dir, "thumbs", f"{image_id}.jpg")

def make_thumbnail(src_path: str, dst_path: str, size=(300, 300)):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with Image.open(src_path) as im:
        im.thumbnail(size)
        im.save(dst_path, "JPEG", quality=85)
