import os, io, uuid, json, shutil
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageOps
from utils.file_utils import is_allowed, ensure_session_dirs, save_upload, thumb_path, make_thumbnail
from utils.metadata_store import new_session_state, new_item
from utils.renamer import compute_new_name
from utils.export_utils import export_zip
from classifiers.heuristics import guess_type
from classifiers.cnn import predict_with_cnn

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(APP_DIR, "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

app = Flask(__name__)
CORS(app)

# Simple in-memory store (would be Redis/DB in production)
SESSIONS = {}

def get_state(session_id: str):
    state = SESSIONS.get(session_id)
    if not state:
        # Try to lazy-load if a workspace exists (simple robustness)
        session_dir = os.path.join(WORKSPACE, session_id)
        if os.path.isdir(session_dir):
            state = new_session_state(session_id)
            SESSIONS[session_id] = state
    return state

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

@app.route("/upload", methods=["POST"])
def upload():
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir, orig_dir = ensure_session_dirs(WORKSPACE, session_id)
    state = get_state(session_id) or new_session_state(session_id)
    SESSIONS[session_id] = state

    files = request.files.getlist("files")
    for f in files:
        if not is_allowed(f.filename):
            continue
        path = save_upload(f, orig_dir)
        image_id = str(uuid.uuid4())
        item = new_item(image_id, path, os.path.basename(path))
        state["items"].append(item)
        # Thumbnail
        make_thumbnail(path, thumb_path(session_dir, image_id))

    # Sort items by original filename (common scan order)
    state["items"].sort(key=lambda x: x["original_filename"])

    return jsonify({"session_id": session_id, "count": len(state["items"]), "items": state["items"]})

@app.route("/classify", methods=["POST"])
def classify():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    names = [it["original_filename"] for it in state["items"]]
    total = len(state["items"])
    for idx, it in enumerate(state["items"]):
        try:
            with Image.open(it["path"]) as im:
                pred = predict_with_cnn(im)
                if pred:
                    it["type"] = pred
                else:
                    it["type"] = guess_type(im, it["original_filename"], idx, total, names)
        except Exception:
            it["type"] = "texto"
        it["validated"] = False

    return jsonify({"session_id": session_id, "items": state["items"]})

@app.route("/validate", methods=["POST"])
def validate():
    """Bulk or single updates.
    Body JSON can contain:
    - session_id
    - updates: [ {id, type?, validated?, page_number?, number_scheme?, extra?, ghost_number?, graphic?}, ... ]
    - bulk_numbering: { ids: [..], start: int, step: int, scheme: "arabic"|"roman", extra: "", ghost: bool }
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    updates = data.get("updates", [])
    id2item = {it["id"]: it for it in state["items"]}

    # Apply direct field updates
    for u in updates:
        it = id2item.get(u.get("id"))
        if not it:
            continue
        for field in ["type", "validated", "number_scheme", "extra", "ghost_number", "graphic"]:
            if field in u:
                it[field] = u[field]
        if "page_number" in u:
            it["page_number"] = u["page_number"]

    # Apply bulk numbering with interval
    bn = data.get("bulk_numbering")
    if bn and isinstance(bn.get("ids"), list):
        ids = bn["ids"]
        start = int(bn.get("start", 1))
        step = int(bn.get("step", 1))
        scheme = bn.get("scheme", "arabic")
        extra = bn.get("extra", "")
        ghost = bool(bn.get("ghost", False))
        n = start
        for iid in ids:
            it = id2item.get(iid)
            if not it:
                continue
            it["page_number"] = n
            it["number_scheme"] = scheme
            it["extra"] = extra
            it["ghost_number"] = ghost
            n += step

    return jsonify({"session_id": session_id, "items": state["items"]})

@app.route("/preview", methods=["GET"])
def preview():
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it["type"] or "sin-tipo",
            it["page_number"],
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False)
        )
    return jsonify({"session_id": session_id, "items": state["items"]})

@app.route("/session", methods=["GET"])
def session_state():
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    return jsonify(state)

@app.route("/file/<session_id>/<image_id>", methods=["GET"])
def serve_file(session_id, image_id):
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    for it in state["items"]:
        if it["id"] == image_id:
            return send_file(it["path"])
    return jsonify({"error": "image not found"}), 404

@app.route("/thumb/<session_id>/<image_id>", methods=["GET"])
def serve_thumb(session_id, image_id):
    session_dir = os.path.join(WORKSPACE, session_id)
    p = os.path.join(session_dir, "thumbs", f"{image_id}.jpg")
    if os.path.exists(p):
        return send_file(p)
    return jsonify({"error": "thumb not found"}), 404

# ---------- PREVIEW COMPATIBLE PARA EL NAVEGADOR (JPEG) ----------
@app.route("/file_preview/<session_id>/<image_id>", methods=["GET"])
def serve_preview(session_id, image_id):
    """Renderiza una vista previa web-segura (JPEG) para cualquier formato original (TIFF, PNG con alfa, CMYK, etc.).
       Soporta query ?w=1600 para limitar ancho.
    """
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    for it in state["items"]:
        if it["id"] == image_id:
            try:
                with Image.open(it["path"]) as im:
                    # Corrige orientación EXIF
                    im = ImageOps.exif_transpose(im)
                    # Asegura espacio de color visible
                    if im.mode in ("RGBA", "LA", "P"):
                        im = im.convert("RGBA")
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    elif im.mode not in ("RGB",):
                        im = im.convert("RGB")

                    # Redimensionado opcional
                    w = request.args.get("w", type=int)
                    if w and w < im.width:
                        h = int(im.height * (w / im.width))
                        im = im.resize((w, h), Image.LANCZOS)

                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=85)
                    buf.seek(0)
                    return send_file(buf, mimetype="image/jpeg")
            except Exception as e:
                return jsonify({"error": f"cannot render preview: {e}"}), 500

    return jsonify({"error": "image not found"}), 404

@app.route("/export", methods=["POST"])
def export():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    # Ensure preview names are up to date
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it["type"] or "sin-tipo",
            it["page_number"],
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False)
        )

    export_dir = os.path.join(WORKSPACE, session_id, "export")
    zip_path = export_zip(state, export_dir)
    return send_file(zip_path, as_attachment=True, download_name=f"export_{session_id}.zip")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
