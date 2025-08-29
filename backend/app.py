import os, io, uuid, json, shutil, re, csv
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageOps

from utils.file_utils import is_allowed, ensure_session_dirs, save_upload, thumb_path, make_thumbnail
from utils.metadata_store import new_session_state, new_item
from utils.renamer import compute_new_name
from utils.export_utils import export_zip  # (lo sigo dejando por compatibilidad con tu /export actual)
from classifiers.heuristics import guess_type
from classifiers.cnn import predict_with_cnn

from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(APP_DIR, "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

app = Flask(__name__)
CORS(app)

# Simple in-memory store (would be Redis/DB in production)
SESSIONS = {}

CATALOG_ID_RE = re.compile(r'^([A-Za-z0-9]+_\d+)', re.IGNORECASE)

def get_state(session_id: str):
    state = SESSIONS.get(session_id)
    if not state:
        # Try to lazy-load if a workspace exists (simple robustness)
        session_dir = os.path.join(WORKSPACE, session_id)
        if os.path.isdir(session_dir):
            state = new_session_state(session_id)
            SESSIONS[session_id] = state
    # Asegura el espacio para catálogo
    if state is not None and "catalog" not in state:
        state["catalog"] = {"map": {}, "detected_id": None}
    return state

def ensure_catalog(state):
    if "catalog" not in state:
        state["catalog"] = {"map": {}, "detected_id": None}
    return state["catalog"]

def extract_catalog_id_from_name(filename: str):
    """Extrae id tipo BO0624_5445 a partir del nombre (antes de la numeración)."""
    base = os.path.splitext(os.path.basename(filename))[0]
    m = CATALOG_ID_RE.match(base)
    return m.group(1) if m else None

def safe_int(v):
    try:
        return int(v)
    except Exception:
        return None

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

# ---------------------------
# Upload de imágenes (mejorado)
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload():
    # Permite que falte session_id (se genera uno nuevo)
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir, orig_dir = ensure_session_dirs(WORKSPACE, session_id)
    state = get_state(session_id) or new_session_state(session_id)
    SESSIONS[session_id] = state
    ensure_catalog(state)  # asegura state["catalog"]

    # Acepta "files" (múltiple) o "file" (simple)
    files = request.files.getlist("files")
    if not files:
        one = request.files.get("file")
        if one:
            files = [one]
    if not files:
        return jsonify({"error": "missing files", "hint": "Use field 'files' (multiple) or 'file' (single)"}), 400

    created_any = False
    for f in files:
        if not f or not is_allowed(f.filename):
            continue
        path = save_upload(f, orig_dir)
        image_id = str(uuid.uuid4())
        item = new_item(image_id, path, os.path.basename(path))
        # Asegura campo 'keywords' por página
        item.setdefault("keywords", "")
        state["items"].append(item)
        # Miniatura
        make_thumbnail(path, thumb_path(session_dir, image_id))
        created_any = True

    # Orden por nombre original (orden típico de escaneo)
    state["items"].sort(key=lambda x: x["original_filename"])

    # Detecta ID de catálogo del primer archivo del lote (si existe utilízalo)
    if created_any and state["items"]:
        first_name = state["items"][0]["original_filename"]
        try:
            detected = extract_catalog_id_from_name(first_name)  # si ya tienes esta función
        except NameError:
            # Fallback simple: toma los dos primeros segmentos separados por "_"
            base = os.path.splitext(first_name)[0]
            parts = base.split("_")
            detected = "_".join(parts[:2]) if len(parts) >= 2 else None
        if detected:
            state["catalog"]["detected_id"] = detected

    return jsonify({
        "session_id": session_id,
        "count": len(state["items"]),
        "items": state["items"],
        "catalog": state["catalog"]
    })


# ---------------------------
# Clasificación (igual)
# ---------------------------
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

# ---------------------------
# Validación / Edición masiva (igual)
# ---------------------------
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
    
    for u in updates:
        it = id2item.get(u.get("id"))
        if not it:
            continue
        for field in ["type", "validated", "number_scheme", "extra", "ghost_number", "graphic", "keywords"]:  # 👈 aquí
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

# ---------------------------
# Previsualización de nombres (igual)
# ---------------------------
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

# ---------------------------
# Estado de sesión (igual)
# ---------------------------
@app.route("/session", methods=["GET"])
def session_state():
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    return jsonify(state)

# ---------------------------
# Archivos y miniaturas (igual)
# ---------------------------
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

# ---------------------------
# Exportación clásica (tuya)
# ---------------------------
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

# =========================================================
#                INTEGRACIÓN CSV + PREVIEW FINAL
# =========================================================

# Cargar CSV maestro: id_catalogo, titulo, autor, anio_publicacion
@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    session_id = request.form.get("session_id") or request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    state = get_state(session_id)
    if not state:
        state = new_session_state(session_id)
        SESSIONS[session_id] = state
    catalog = ensure_catalog(state)

    f = request.files.get("file")
    if not f:
        return jsonify({"error": "missing file"}), 400

    raw = f.read()
    text = raw.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    def norm(s):
        return (s or "").strip().lower().replace(" ", "_")

    headers = reader.fieldnames or []
    colmap = {norm(h): h for h in headers}

    def getcol(*cands):
        for c in cands:
            if c in colmap:
                return colmap[c]
        return None

    # Requeridos mínimos: id + título (si no hay título, lo dejamos vacío, pero id es clave)
    id_col = getcol("id_catalogo", "catalog_id")
    if not id_col:
        return jsonify({"error": "CSV missing required column 'id_catalogo' (or 'catalog_id')"}), 400

    title_col = getcol("titulo", "title")
    year_col = getcol("anio_publicacion", "year")
    publisher_col = getcol("publisher", "editorial")
    place_col = getcol("place", "lugar")
    language_col = getcol("language", "idioma")
    keywords_col = getcol("keywords", "palabras_clave")

    catalog_map = {}
    for row in reader:
        cid = (row.get(id_col) or "").strip()
        if not cid:
            continue
        entry = {
            "catalog_id": cid,
            "catalog_title": (row.get(title_col) or "").strip() if title_col else "",
            "catalog_publication_year": safe_int((row.get(year_col) or "").strip()) if year_col else None,
            "catalog_publisher": (row.get(publisher_col) or "").strip() if publisher_col else "",
            "catalog_place": (row.get(place_col) or "").strip() if place_col else "",
            "catalog_language": (row.get(language_col) or "").strip() if language_col else "",
            "catalog_keywords": (row.get(keywords_col) or "").strip() if keywords_col else "",
        }
        catalog_map[cid] = entry

    catalog["map"] = catalog_map

    # (Re)detectar ID si ya hay imágenes cargadas
    if state["items"]:
        first_name = state["items"][0]["original_filename"]
        detected = extract_catalog_id_from_name(first_name)
        if detected:
            catalog["detected_id"] = detected

    return jsonify({"ok": True, "count": len(catalog_map), "detected_id": catalog.get("detected_id")})

# Estado del catálogo
@app.route("/catalog_status", methods=["GET"])
def catalog_status():
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    catalog = ensure_catalog(state)
    detected = catalog.get("detected_id")
    entry = catalog["map"].get(detected) if detected else None
    return jsonify({
        "detected_id": detected,
        "found": bool(entry),
        "entry": entry
    })

# Previsualización de exportación (combina nombres + metadatos de catálogo)
@app.route("/export_preview", methods=["GET"])
def export_preview():
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    catalog = ensure_catalog(state)

    # Asegura nombres
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it["type"] or "sin-tipo",
            it["page_number"],
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False)
        )

    detected = catalog.get("detected_id")
    entry = catalog["map"].get(detected) if detected else None

    preview_rows = []
    for it in state["items"]:
        row = {
            "original_filename": it["original_filename"],
            "new_filename": it.get("new_filename"),
            "type": it.get("type"),
            "graphic": it.get("graphic", False),
            "validated": it.get("validated", False),
            "page_number": it.get("page_number"),
        }
        if entry:
            row.update(entry)
        preview_rows.append(row)

    return jsonify({
        "catalog_detected": detected,
        "catalog_entry": entry,
        "items": preview_rows
    })

# Confirmación y export ZIP con metadata.json enriquecido
@app.route("/export_confirm", methods=["POST"])
def export_confirm():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    catalog_state = ensure_catalog(state)

    # Asegura nombres actualizados
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it["type"] or "sin-tipo",
            it["page_number"],
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False)
        )
        # default keywords por si faltan
        it.setdefault("keywords", "")

    # 1) Determinar metadatos de catálogo (override > CSV detectado)
    override = data.get("catalog_override") or {}
    detected_id = catalog_state.get("detected_id")
    cmap = catalog_state.get("map", {})

    if any(v not in (None, "", []) for v in override.values()):
        catalog_meta = {
            "catalog_id": override.get("catalog_id") or detected_id,
            "catalog_title": override.get("catalog_title") or "",
            "catalog_publication_year": override.get("catalog_publication_year"),
            "catalog_publisher": override.get("catalog_publisher") or "",
            "catalog_place": override.get("catalog_place") or "",
            "catalog_language": override.get("catalog_language") or "",
            "catalog_keywords": override.get("catalog_keywords") or "",
        }
    else:
        entry = cmap.get(detected_id) if detected_id else None
        catalog_meta = {
            "catalog_id": entry.get("catalog_id") if entry else detected_id,
            "catalog_title": entry.get("catalog_title") if entry else "",
            "catalog_publication_year": entry.get("catalog_publication_year") if entry else None,
            "catalog_publisher": entry.get("catalog_publisher") if entry else "",
            "catalog_place": entry.get("catalog_place") if entry else "",
            "catalog_language": entry.get("catalog_language") if entry else "",
            "catalog_keywords": entry.get("catalog_keywords") if entry else "",
        }

    # 2) Construir array: primero el objeto de catálogo, luego las páginas
    out = []
    out.append(catalog_meta)

    for it in state["items"]:
        row = {
            "original_filename": it["original_filename"],
            "new_filename": it["new_filename"],
            "type": it.get("type"),
            "graphic": it.get("graphic", False),
            "validated": it.get("validated", False),
            "page_number": it.get("page_number"),
            # referencia al catálogo
            "catalog_id": catalog_meta.get("catalog_id"),
            # keywords por página
            "keywords": it.get("keywords", "")
        }
        out.append(row)

    # 3) Generar zip en memoria
    mem = io.BytesIO()
    with ZipFile(mem, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(out, ensure_ascii=False, indent=2))
        for it in state["items"]:
            src = it.get("path")
            newname = it.get("new_filename") or it["original_filename"]
            arcname = f"images/{newname}"
            if src and os.path.exists(src):
                try:
                    zf.write(src, arcname=arcname)
                except Exception:
                    zf.writestr(arcname, b"")
            else:
                zf.writestr(arcname, b"")

    mem.seek(0)
    filename = f"export_{session_id}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.zip"
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=filename)

# -----------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
