# Preservia App

**Preservia App** is the first version of a web application designed to manage the metadata workflow for heritage documents, aimed at archivists and librarians. It supports features such as upload and automatic classification (using heuristics and OCR), bulk validation and editing, flexible numbering with support for Arabic/Roman numerals, extras, and ghost numbers, as well as intelligent file renaming and an export function that creates a ZIP file with the renamed images and a `metadata.json` file.

### Key Features

* **Batch upload and automatic classification**
  * Supports uploading entire sets of digitized images.
  * Automatically identifies common page types (cover, back cover, illustration, blank page, etc.).
  * Assigns initial metadata to each file to accelerate cataloging.
* **Metadata editing (batch or individual)**
  * Enables corrections or additions for each page: pagination (Arabic or Roman), additional notes (bis, a, v…), ghost pages, or validation status.
  * Allows batch editing for multiple images at once.
* **Flexible visualization modes**
  * **Gallery:** fast browsing via thumbnails with direct selection (inspired by desktop file explorers).
  * **List:** detailed view with filters by status or page type.
  * **Viewer:** full-screen navigation with dynamic zoom, pan, and immediate editing.
* **Structured export**
  * Automatically generates a `metadata.json` file with normalized information for all images.
  * Packages renamed and coherent files into a ZIP for preservation, sharing, or integration into digital repositories.
* **Tools adapted to real workflows**
  * Multi-selection with clicks, ranges, or keyboard shortcuts.
  * Automatic page numbering for filtered sets.
  * Visual indicators (blue border on selected items, quick validation).
