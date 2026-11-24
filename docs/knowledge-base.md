# Knowledge Base (Task 2)

Supported formats: PDF (embedded text first, scanned/low-text pages OCRed only when needed), TXT/Markdown, DOCX, CSV, JSON, notebooks, common source/config text (Python, JavaScript/TypeScript, Java, C/C++, HTML, CSS, SQL, YAML, TOML, INI, shell/batch, XML and related UTF-8 files), PNG/JPG/JPEG/WebP. DOCX uses `python-docx`; PDFs use the existing PyMuPDF dependency. Image OCR and scanned-page OCR use only an installed local Ollama vision model selected in Settings. Studio does not download models or use cloud APIs.

## Use
1. Open Knowledge and create a collection.
2. Add one or more documents. The collection table shows file type/size, status, pages/sections completed, and failed page count/errors.
3. View opens extracted text and page details; PDF previews show the source page. Retry a failed page or use Re-index for the full document.
4. Search from Knowledge home for all collections or use the collection-scoped search. SQLite FTS5 retrieves overlapping ~1,200-character chunks with 180-character overlap.
5. Ask the collection a question. Only retrieved excerpts and the question are sent to the selected local Ollama chat model. The answer returns source labels plus inspectable passages; no-match questions get a deterministic insufficient-evidence response without a model call.

## OCR and storage
Low-text PDF pages (under 30 selectable characters) are rendered and sent to OCR; text-bearing pages in mixed PDFs are not. Page order and individual extraction errors are kept. OCR is serial; uploads are capped at 100 MiB each/20 per batch; image payloads are capped at 12 MiB. The app never pulls models automatically. Select an installed Ollama vision model in Settings; missing or non-vision models produce explicit retryable errors.

The migration adds source metadata, `chunks`, FTS5 `chunk_fts`, and version tracking without resetting chat/history tables. Existing DBs receive a timestamped SQLite backup beside the database before migration. New uploads are streamed to temporary files and atomically stored using their SHA-256 digest; display filenames are not paths, and identical file bytes may be shared between collections. Deletion only removes a verified app-managed hash file when no source references it. Configure data locations with existing `STUDIO_DB` and `STUDIO_FILES`. Back up both DB and files before moving them. The ZIP has no private DB/documents.

## Troubleshooting / limitations
- OCR requires Ollama running and a locally installed vision-capable model selected in Settings. Studio does not download it. OCR failure does not block text extraction from other PDF pages.
- Re-index retries an entire document; page Retry targets a single failed page. Queued/interrupted work resumes after restart; completed docs are not reprocessed automatically.
- Search is lexical FTS5, not semantic embeddings. PDF/DOCX complex layout and paragraph/table ordering can be simplified. Image/PDF OCR quality depends on the selected model and hardware. OCR is serial and cannot be cancelled mid-inference; removing a queued item prevents later work from being retained.
- Imported text is untrusted. Q&A explicitly instructs Ollama to ignore embedded commands, but users should review the linked cited passages for adversarial content.
