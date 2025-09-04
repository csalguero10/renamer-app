import os, io, uuid, json, shutil, csv, zipfile, re
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageOps

# ---- Utilidades existentes ----
from utils.file_utils import is_allowed, ensure_session_dirs, save_upload, thumb_path, make_thumbnail
from utils.metadata_store import new_session_state, new_item
from utils.renamer import compute_new_name
# from utils.export_utils import export_zip  

from classifiers.heuristics import guess_type
from classifiers.cnn import predict_with_cnn

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(APP_DIR, "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

app = Flask(__name__)
CORS(app)

# -------------------- Estado en memoria (demo) --------------------
SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene (o intenta lazy-load) el estado de una sesión."""
    state = SESSIONS.get(session_id)
    if not state:
        session_dir = os.path.join(WORKSPACE, session_id)
        if os.path.isdir(session_dir):
            state = new_session_state(session_id)
            SESSIONS[session_id] = state
    # Asegura campos base
    if state is not None and "label" not in state:
        state["label"] = None  # nombre amigable opcional
    return state


# -------------------- Catálogo / CSV helpers --------------------
def ensure_catalog(state: Dict[str, Any]) -> Dict[str, Any]:
    """Asegura estructura de catálogo dentro del estado."""
    if "catalog" not in state:
        state["catalog"] = {"detected_id": None, "entry": None}
    if "catalog_map" not in state:
        state["catalog_map"] = {}  # id -> fila normalizada
    return state["catalog"]


def extract_catalog_id_from_name(filename: str) -> Optional[str]:
    """Extrae ID tipo 'BO0624_5445' de nombres como 'BO0624_5445_00001.jpg'."""
    base = os.path.splitext(os.path.basename(filename))[0]
    parts = base.split("_")
    if len(parts) >= 2 and parts[0] and parts[1]:
        return f"{parts[0]}_{parts[1]}"
    return None


# Mapeo flexible de cabeceras CSV -> claves canónicas
CSV_KEY_MAP = {
    "id_catalogo": "catalog_id",
    "catalog_id": "catalog_id",
    "id": "catalog_id",

    "titulo": "catalog_title",
    "title": "catalog_title",

    "autor": "catalog_author",
    "author": "catalog_author",

    "anio_publicacion": "catalog_publication_year",
    "año_publicacion": "catalog_publication_year",
    "publication_year": "catalog_publication_year",
    "year": "catalog_publication_year",

    "publisher": "catalog_publisher",
    "editorial": "catalog_publisher",

    "place": "catalog_place",
    "lugar": "catalog_place",

    "language": "catalog_language",
    "idioma": "catalog_language",

    "keywords": "catalog_keywords",
    "palabras_clave": "catalog_keywords",
}


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        key = str(k).strip().lower()
        canon = CSV_KEY_MAP.get(key)
        if canon:
            out[canon] = (v or "").strip()
    # Tipar año si es posible
    if "catalog_publication_year" in out:
        try:
            out["catalog_publication_year"] = int(out["catalog_publication_year"])
        except Exception:
            pass
    return out


def build_metadata_array(
    state: Dict[str, Any],
    catalog_override: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Construye el array de metadata para exportar:
    - Primer objeto: metadatos del catálogo (header)
    - Luego, una entrada por cada página
    """
    ensure_catalog(state)
    detected_id = state["catalog"].get("detected_id")

    # Fuente: override explícito > entrada de CSV > detected_id solo
    header: Dict[str, Any] = {}
    entry = state["catalog"].get("entry") or {}

    def pick(key: str, default=None):
        if catalog_override and key in catalog_override and catalog_override[key] not in (None, ""):
            return catalog_override[key]
        if key in entry and entry[key] not in (None, ""):
            return entry[key]
        return default

    header["catalog_id"] = pick("catalog_id", detected_id)
    header["catalog_title"] = pick("catalog_title", "")
    header["catalog_author"] = pick("catalog_author", "")
    header["catalog_publication_year"] = pick("catalog_publication_year", None)
    header["catalog_publisher"] = pick("catalog_publisher", "")
    header["catalog_place"] = pick("catalog_place", "")
    header["catalog_language"] = pick("catalog_language", "")
    header["catalog_keywords"] = pick("catalog_keywords", "")

    # Asegurar nombres nuevos al día
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it.get("type") or "sin-tipo",
            it.get("page_number"),
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False),
        )

    pages: List[Dict[str, Any]] = []
    for it in state["items"]:
        page_num = it.get("page_number", None)
        page_keywords = it.get("keywords", "")  # vacío si no hay
        pages.append({
            "original_filename": it["original_filename"],
            "new_filename": it.get("new_filename"),
            "type": it.get("type"),
            "graphic": bool(it.get("graphic", False)),
            "validated": bool(it.get("validated", False)),
            "page_number": page_num if page_num is not False else None,
            "catalog_id": header["catalog_id"],
            "keywords": page_keywords
        })

    return [header] + pages


def nice_export_basename(state: Dict[str, Any], session_id: str) -> str:
    """
    Devuelve un nombre corto y seguro para el ZIP:
    label (si existe) -> catalog_id detectado -> primeros 8 del uuid.
    """
    label = (state.get("label") or "").strip()
    cat_id = ((state.get("catalog") or {}).get("detected_id") or "").strip()
    base = label or cat_id or session_id.replace("-", "")[:8].upper()
    # Sanitiza para filesystem
    base = re.sub(r"[^A-Za-z0-9_\-]+", "_", base)
    if not base:
        base = session_id.replace("-", "")[:8].upper()
    return base


# -------------------- Endpoints --------------------
@app.route("/ping")
def ping():
    return jsonify({"ok": True})


# ---------- Etiqueta de sesión (nombre amigable) ----------
@app.get("/session_label_get")
def session_label_get():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    st = get_state(session_id)
    if not st:
        return jsonify({"error": "session not found"}), 404
    return jsonify({"session_id": session_id, "label": st.get("label") or ""})


@app.post("/session_label_set")
def session_label_set():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    st = get_state(session_id)
    if not st:
        return jsonify({"error": "session not found"}), 404
    label = (data.get("label") or "").strip() or None
    st["label"] = label
    return jsonify({"session_id": session_id, "label": label or ""})


@app.route("/upload", methods=["POST"])
def upload():
    """
    Carga de imágenes.
    - Acepta 'files' (múltiple) o 'file' (simple).
    - Detecta catalog_id desde el primer archivo y vincula entrada del CSV si existe.
    """
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir, orig_dir = ensure_session_dirs(WORKSPACE, session_id)
    state = get_state(session_id) or new_session_state(session_id)
    SESSIONS[session_id] = state
    ensure_catalog(state)

    files = request.files.getlist("files")
    if not files:
        one = request.files.get("file")
        if one:
            files = [one]
    if not files:
        return jsonify({"error": "missing files", "hint": "Use field 'files' (multiple) or 'file' (single)"}), 400

    for f in files:
        if not f or not is_allowed(f.filename):
            continue
        path = save_upload(f, orig_dir)
        image_id = str(uuid.uuid4())
        item = new_item(image_id, path, os.path.basename(path))
        item.setdefault("keywords", "")  # campo por página
        state["items"].append(item)
        make_thumbnail(path, thumb_path(session_dir, image_id))

    # Orden por nombre original
    state["items"].sort(key=lambda x: x["original_filename"])

    # Detectar ID de catálogo con el primer archivo
    if state["items"]:
        first_name = state["items"][0]["original_filename"]
        detected = extract_catalog_id_from_name(first_name)
        state["catalog"]["detected_id"] = detected
        entry = state.get("catalog_map", {}).get(detected) if detected else None
        state["catalog"]["entry"] = entry

    return jsonify({
        "session_id": session_id,
        "label": state.get("label") or "",
        "count": len(state["items"]),
        "items": state["items"],
        "catalog": state["catalog"]
    })


@app.post("/upload_csv")
def upload_csv():
    """
    Carga un CSV maestro (opcional).
    - Acepta 'file' o 'csv'
    - Si no se provee session_id, crea uno
    - Normaliza cabeceras y guarda un mapa id->fila
    - Si hay imágenes, intenta detectar catalog_id y vincular entrada
    """
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    state = get_state(session_id) or new_session_state(session_id)
    SESSIONS[session_id] = state
    ensure_catalog(state)

    f = request.files.get("file") or request.files.get("csv")
    if not f:
        return jsonify({"error": "missing CSV file. Use field 'file' or 'csv'"}), 400

    try:
        raw = f.read()
        text = raw.decode("utf-8-sig", errors="ignore")

        # Detectar delimitador
        sample = "\n".join(text.splitlines()[:5])
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            class _D: delimiter = ','
            dialect = _D()

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        catalog_map = {}
        for row in reader:
            norm = _normalize_row(row)
            cid = norm.get("catalog_id")
            if cid:
                catalog_map[cid] = norm

        state["catalog_map"] = catalog_map

        # Si ya hay imágenes cargadas, intenta detectar ID del primer archivo
        detected = state.get("catalog", {}).get("detected_id")
        if not detected and state.get("items"):
            first_name = state["items"][0]["original_filename"]
            detected = extract_catalog_id_from_name(first_name)
            state["catalog"]["detected_id"] = detected

        # Vincular entrada si existe
        entry = catalog_map.get(detected) if detected else None
        state["catalog"]["entry"] = entry

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "label": state.get("label") or "",
            "loaded": len(catalog_map),
            "detected_id": detected,
            "entry": entry
        })
    except Exception as e:
        return jsonify({"error": f"CSV parse error: {e}"}), 400


@app.get("/catalog_status")
def catalog_status():
    """Devuelve el id detectado y la entrada de catálogo vinculada (si existe)."""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    ensure_catalog(state)
    detected = state["catalog"].get("detected_id")
    entry = state.get("catalog_map", {}).get(detected) if detected else None
    state["catalog"]["entry"] = entry
    return jsonify({
        "session_id": session_id,
        "label": state.get("label") or "",
        "detected_id": detected,
        "entry": entry
    })


@app.route("/classify", methods=["POST"])
def classify():
    """Clasificación automática (CNN ligera + heurísticas)."""
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
            it["type"] = "text"
        it["validated"] = False

    return jsonify({"session_id": session_id, "items": state["items"]})


@app.route("/validate", methods=["POST"])
def validate():
    """
    Actualizaciones individuales o masivas.
    Body JSON:
    - session_id
    - updates: [ {id, type?, validated?, page_number?, number_scheme?, extra?, ghost_number?, graphic?, keywords?}, ... ]
    - bulk_numbering: { ids: [..], start: int, step: int, scheme: "arabic"|"roman", extra: "", ghost: bool }
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    updates = data.get("updates", [])
    id2item = {it["id"]: it for it in state["items"]}

    # Apply direct updates
    for u in updates:
        it = id2item.get(u.get("id"))
        if not it:
            continue
        for field in ["type", "validated", "number_scheme", "extra", "ghost_number", "graphic", "keywords"]:
            if field in u:
                it[field] = u[field]
        if "page_number" in u:
            it["page_number"] = u["page_number"]

    # Bulk numbering
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
    """Actualiza y devuelve nombres nuevos (para UI)."""
    session_id = request.args.get("session_id")
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404
    for it in state["items"]:
        it["new_filename"] = compute_new_name(
            it["original_filename"],
            it.get("type") or "sin-tipo",
            it.get("page_number"),
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False)
        )
    return jsonify({"session_id": session_id, "items": state["items"]})


# ------- Export preview (para modal en el frontend) -------
@app.post("/export_preview")
def export_preview():
    """Devuelve el JSON de metadata (header + páginas) sin crear archivos."""
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    catalog_override = data.get("catalog_override") or {}
    meta = build_metadata_array(state, catalog_override=catalog_override)
    return jsonify({"session_id": session_id, "metadata": meta})


# ------- Export final (ZIP + metadata.json) -------
@app.route("/export", methods=["POST"])
def export():
    """
    Genera ZIP con:
    - metadata.json (primer objeto = catálogo, luego cada página)
    - todas las imágenes renombradas (copiadas con new_filename en raíz del ZIP)
    Admite 'catalog_override' para sobreescribir campos del catálogo.
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    catalog_override = data.get("catalog_override") or {}

    # Construir metadata (y asegurar new_filename al día)
    metadata_array = build_metadata_array(state, catalog_override=catalog_override)

    # Directorio de exportación limpio
    export_dir = os.path.join(WORKSPACE, session_id, "export")
    if os.path.isdir(export_dir):
        shutil.rmtree(export_dir)
    os.makedirs(export_dir, exist_ok=True)

    # Escribir metadata.json
    meta_path = os.path.join(export_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata_array, f, ensure_ascii=False, indent=2)

    # Copiar imágenes con el nuevo nombre en export_dir
    for it in state["items"]:
        src = it["path"]
        new_name = it.get("new_filename") or compute_new_name(
            it["original_filename"],
            it.get("type") or "sin-tipo",
            it.get("page_number"),
            it.get("number_scheme", "arabic"),
            it.get("extra", ""),
            it.get("ghost_number", False),
        )
        dst = os.path.join(export_dir, new_name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except Exception:
            try:
                with Image.open(src) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode in ("RGBA", "LA", "P"):
                        im = im.convert("RGBA")
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    elif im.mode not in ("RGB",):
                        im = im.convert("RGB")
                    base_no_ext, _ = os.path.splitext(dst)
                    dst = base_no_ext + ".jpg"
                    im.save(dst, format="JPEG", quality=90)
            except Exception:
                continue

    # Crear ZIP (nombre de archivo físico interno puede ser fijo,
    # el nombre que ve el usuario lo controlamos con download_name)
    zip_path = os.path.join(WORKSPACE, session_id, f"export_{session_id}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(meta_path, arcname="metadata.json")
        for name in os.listdir(export_dir):
            if name == "metadata.json":
                continue
            full = os.path.join(export_dir, name)
            if os.path.isfile(full):
                zf.write(full, arcname=name)

    # <- aquí aplicamos el nombre "bonito"
    pretty = nice_export_basename(state, session_id)
    download_name = f"export_{pretty}.zip"
    return send_file(zip_path, as_attachment=True, download_name=download_name)


# -------------------- Archivos / Previews --------------------
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


@app.route("/file_preview/<session_id>/<image_id>", methods=["GET"])
def serve_preview(session_id, image_id):
    """
    Renderiza una vista previa web-segura (JPEG). Soporta ?w=1600 para limitar ancho.
    """
    state = get_state(session_id)
    if not state:
        return jsonify({"error": "session not found"}), 404

    for it in state["items"]:
        if it["id"] == image_id:
            try:
                with Image.open(it["path"]) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode in ("RGBA", "LA", "P"):
                        im = im.convert("RGBA")
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    elif im.mode not in ("RGB",):
                        im = im.convert("RGB")

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


# -------------------- App --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
