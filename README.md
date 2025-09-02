# Preservia — Web App (Flask + Svelte + Tailwind/CSS)

First version of a web application designed to manage the metadata workflow for heritage documents, aimed at archivists and librarians. It supports features such as upload and automatic classification (using heuristics and OCR), bulk validation and editing, flexible numbering with support for Arabic/Roman numerals, extras, and ghost numbers, as well as intelligent file renaming and an export function that creates a ZIP file with the renamed images and a metadata.json file.

https://dhdk.gitbook.io/preservia-app

## Structure
```
renamer-app/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── classifiers/
│   │   ├── heuristics.py
│   │   ├── ocr_utils.py
│   │   └── cnn.py
│   ├── utils/
│   │   ├── roman.py
│   │   ├── renamer.py
│   │   ├── file_utils.py
│   │   ├── export_utils.py
│   │   └── metadata_store.py
│   └── workspace/  (runtime)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── postcss.config.cjs
    ├── tailwind.config.cjs
    └── src/
        ├── app.css
        ├── main.js
        ├── App.svelte
        ├── lib/
        │   ├── stores.js
        │   └── catalogStore.js
        │   └── utilsSessionLabel.js
        │   └── utils.js        
        │   └── utils/
        │      └── niceSession.js
        └── pages/
            ├── Upload.svelte
            ├── Gallery.svelte
            ├── Viewer.svelte
            └── Export.svelte
```

## Requirements
- Python 3.10+
- Node 18+
- (Optional) Tesseract installed in the system for OCR (`pytesseract`).  
  If not present, a fallback without OCR will be used.
- (Optional) PyTorch if you want to use a CNN model (it will be loaded automatically if `backend/classifiers/model.pth` exists).

## Backend — How to run
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run
FLASK_APP=app.py FLASK_ENV=development flask run --port 5001
# or
python app.py
```
Backend runs on: http://localhost:5001

## Frontend — How to run
```bash
cd frontend
npm install
npm run dev
```
Backend runs on: http://localhost:5173

> **Note**: the frontend assumes the backend is running at `http://localhost:5001`.  
> Change `VITE_API_BASE` in `frontend/.env.development` if needed.

## Basic workflow
1. **Upload**: drag & drop or select multiple images (JPG/PNG/TIFF).
2. **Classify**: heuristics + OCR to suggest page type (all remain *pending validation*).
3. **Review/Edit**: in *Gallery* and *Viewer*, multi-selection, bulk assignments, flexible numbering (start+interval, Arabic/Roman, extras, ghost number, "graphic" yes/no).
4. **Preview**: see proposed renaming in real time.
5. **Export**: download ZIP with renamed images and `metadata.json`.

## Main Endpoints (Flask)
- `POST /upload` — Upload files. Returns `session_id` and initial state.
- `POST /classify` — Automatic classification. Marks items as `validated: false`.
- `POST /validate` — Batch/individual edits (type, numbering, extras, etc.).
- `GET  /preview?session_id=...` — Computes `new_filename` for all.
- `GET  /session?session_id=...` — Full session state.
- `GET  /file/<session_id>/<image_id>` — Download/view an image.
- `POST /export` — Generates ZIP + `metadata.json` and returns it.

## Classification notes (heuristics)
- **Blank page**: >90% white pixels / no borders / no detected text.
- **Text**: OCR detects lines/words.
- **Illustration**: many edges and low text density.
- **Cover**: first image or filename ends with `_000001`.
- **Back cover**: image before files with `ref` or `ins` in the name.
- **Endpapers**: second image (`_000002`) and the one before the back cover.
- **Insert**: filename contains `ins`.
- **Reference**: filename contains `ref`.
- **Tissue/Velum (velinas)**: very bright, very low intensity variation (low contrast).

## Renaming
new = <original_no_ext> + ' ' + <type> + ('_' + token_num) + <extra> + <ext>

- `token_num` in Arabic or Roman.
- If `ghost_number = true`, the `token_num` is wrapped in `[n]`.
- If `page_number = false` → only adds the type.

### Examples
- `BO0624_4866_000003_l text_4.jpg`
- `BO0624_4866_000005 text_[3].jpg`
- `BO0624_4866_000007 text_2bis.png`

---

> **Tip**: if you want to train a CNN, save your `model.pth` in `backend/classifiers/` with 10 output classes  
> (`cover`, `back cover`, `endpapers`, `tissue/velum`, `frontispiece`, `text`, `illustration`, `insert`, `blank page`, `reference`).  
> The backend will use it to support heuristic classification.
