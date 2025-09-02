# Future Development Fases

* A **collaborative platform** for multi-user metadata enrichment.
* **Integration with a NAS system using Docker containers**, allowing user session management and direct access to each catalog or file.
* **Transition from an in-memory model to relational databases** (SQLite/PostgreSQL), with storage of absolute NAS paths, checksums, file dimensions, edited metadata, and validation states.
* **Asynchronous jobs for bulk ingestion**, including OCR and derivative file generation.
* **Synchronization with IIIF servers**, so that the current viewer evolves into a fully interoperable **IIIF Viewer**.
* **Semantic enrichment through RDF/JSON-LD export**, with a dedicated _context_ for types such as _cover_, _endpapers_, _blank\_page_, etc. This would also include OCR integration as _annotations_ (e.g., `body: textualBody`, `motivation: supplementing`) and connection to a triplestore for linking with _Linked Open Data (LOD)_.

**Advanced metadata workflows**

* Introduces initial **clustering** based on page names, paving the way for information extraction.
* Supports hybrid retrieval strategies that combine different levels of representation:
  * _Low-level_: visual attributes (color, texture, form, structure).
  * _Mid-level_: textual annotations and attributes.
* This enables more complex multimedia information retrieval tasks, such as cross-referencing images and text.
