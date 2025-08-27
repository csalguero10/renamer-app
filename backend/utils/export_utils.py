import os, json, zipfile, shutil
from PIL import Image

def export_zip(session_state: dict, export_dir: str) -> str:
    """Creates an export folder of renamed images and metadata.json, then zips it.
    Returns the zip file path.
    """
    os.makedirs(export_dir, exist_ok=True)
    images_out = os.path.join(export_dir, "images")
    os.makedirs(images_out, exist_ok=True)
    metadata = []

    for item in session_state["items"]:
        src = item["path"]
        new_name = item.get("new_filename") or item["original_filename"]
        dst = os.path.join(images_out, new_name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Write copy (preserving format)
        with Image.open(src) as im:
            im.save(dst)
        metadata.append({
            "original_filename": item["original_filename"],
            "new_filename": new_name,
            "type": item.get("type"),
            "graphic": bool(item.get("graphic")),
            "validated": bool(item.get("validated")),
            "page_number": item.get("page_number", False) if item.get("page_number", None) is not None else False
        })

    with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    zip_path = export_dir.rstrip("/\\") + ".zip"
    # Re-create zip if exists
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(export_dir):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, export_dir)
                z.write(full, rel)
    return zip_path
