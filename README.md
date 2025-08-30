# Renamer Flow — Web App (Flask + Svelte + Tailwind)

Aplicación web para gestionar el flujo de digitalización de documentos patrimoniales:
carga, clasificación automática (heurísticas + OCR y CNN opcional), validación/edición masiva,
numeración flexible (arábiga/romana, extras, número fantasma), renombrado inteligente
y exportación (ZIP de imágenes renombradas + `metadata.json`).

## Estructura
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

## Requisitos
- Python 3.10+
- Node 18+
- (Opcional) Tesseract instalado en el sistema para OCR (`pytesseract`). Si no está, se usa fallback sin OCR.
- (Opcional) PyTorch si desea usar un modelo CNN (se carga automáticamente si existe `backend/classifiers/model.pth`).

## Backend — Cómo ejecutar
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar
FLASK_APP=app.py FLASK_ENV=development flask run --port 5001
# o
python app.py
```
El backend corre en: http://localhost:5001

## Frontend — Cómo ejecutar
```bash
cd frontend
npm install
npm run dev
```
El frontend corre en: http://localhost:5173

> Nota: el frontend asume el backend en `http://localhost:5001`. Cambia `VITE_API_BASE` en `frontend/.env.development` si lo necesitas.

## Flujo básico
1. **Upload**: arrastrar/soltar o seleccionar múltiples imágenes (JPG/PNG/TIFF).
2. **Classify**: heurísticas + OCR para sugerir tipo de página (todo queda *pendiente de validación*).
3. **Revisar/Editar**: en *Galería* y *Visor*, selección múltiple, asignaciones masivas, numeración flexible (inicio+intervalo, arábiga/romana, extras, número fantasma, "gráfico" sí/no).
4. **Preview**: ver renombrado propuesto en tiempo real.
5. **Export**: descargar ZIP con imágenes renombradas y `metadata.json`.

## Endpoints principales (Flask)
- `POST /upload` — Subir archivos. Devuelve `session_id` y estado inicial.
- `POST /classify` — Clasificación automática. Marca elementos como `validated: false`.
- `POST /validate` — Ediciones por lote/individuales (tipo, numeración, extras, etc.).
- `GET  /preview?session_id=...` — Calcula `new_filename` para todos.
- `GET  /session?session_id=...` — Estado completo de la sesión.
- `GET  /file/<session_id>/<image_id>` — Descarga/visualización de la imagen.
- `POST /export` — Genera ZIP + `metadata.json` y lo devuelve.

## Notas de clasificación (heurísticas)
- **Página blanca**: >90% píxeles blancos / sin bordes / sin texto detectado.
- **Texto**: OCR detecta líneas/palabras.
- **Ilustración**: muchos bordes y baja densidad de texto.
- **Portada**: primera imagen o nombre termina en `_000001`.
- **Contraportada**: imagen anterior a archivos con `ref` o `ins` en el nombre.
- **Guardas**: segunda imagen (`_000002`) y la previa a la contraportada.
- **Inserto**: nombre contiene `ins`.
- **Referencia**: nombre contiene `ref`.
- **Velinas**: muy brillante, muy poca variación de intensidad (bajo contraste).

## Renombrado
`new = <original_sin_ext> + ' ' + <type> + ('_' + token_num) + <extra> + <ext>`  
- `token_num` en arábigo o romano.
- Si `ghost_number = true`, el `token_num` se envuelve en `[n]`.
- Si `page_number = false` → solo agrega el tipo.

Ejemplos:
- `BO0624_4866_000003_l texto_4.jpg`
- `BO0624_4866_000005 texto_[3].jpg`
- `BO0624_4866_000007 texto_2bis.png`

---

> **Consejo**: si desea entrenar una CNN, guarde su `model.pth` en `backend/classifiers/` con salida de 10 clases (`portada`, `contraportada`, `guardas`, `velinas`, `frontispicio`, `texto`, `ilustración`, `inserto`, `página blanca`, `referencia`). El backend la usará de apoyo a las heurísticas.
