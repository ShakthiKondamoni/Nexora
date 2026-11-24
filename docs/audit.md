# Audit of supplied Nexora

## Inventory and baseline
- `server.py` (14,496 bytes): FastAPI app, SQLite helper/schema, settings, chat/projects,
  Ollama discovery/test/generation and host monitoring. Actual entry: `py server.py`;
  Uvicorn binds 127.0.0.1:8501. No Flask, React or cloud service was present.
- `knowledge.py` (15,676 bytes): injected query/capability/URL globals, APIRouter `/api/kb`,
  bounded single-worker ingestion queue, PDFs/Ollama OCR, notebook/text parsing, FTS5 retrieval and exports.
- `index.html` (49,352 bytes): one document with embedded CSS, classic JavaScript, inline SVG icons,
  delegated data-a actions, fetch API and Canvas charts. No external images/fonts/icons were required.
- `requirements.txt`: eight direct dependencies, originally unpinned; no other configuration supplied.
- `run_studio.bat`: cd to script directory, global pip install, browser open then server.py; no venv or error checks.
- `test_studio.py`: twelve tests, with isolated temp DB but some reliance on Ollama being absent.
- `studio.db`: supplied SQLite state; quick_check=ok, inspected read-only, private contents excluded.
  No source folder tree or uploaded-file folder was supplied.

Initial sandbox pytest failed because dependencies were missing. Temporary public wheel downloads provided
an isolated runtime; then the untouched original twelve tests passed (12 passed, one upstream warning, 4.19s).
See verification.md for final run results. No earlier reported claims were used as baseline evidence.

## Database and references
Application tables: projects(id,name); chats(id,title,pinned,archived,project_id,updated);
messages(id,chat_id,role,content,context,images,names,model,created,sources);
settings(key,value); collections(id,name,created);
sources(id,coll_id,type,title,path,hash,status,error,ocr_model,added);
pages(source_id,loc,kind,status,text,error); FTS5 fts(text,source_id,coll_id,loc).
SQLite FTS internals and sqlite_sequence are not separate application features.

The supplied DB had 2 chats/10 messages/2 settings, no projects/collections/sources/pages.
No private messages or settings values are copied into this audit. Chat attachments store text context,
filenames and image base64 in messages. Knowledge documents store a content hash + filename on disk,
with sources.path pointing to that file. Identical files can be shared across collections; deleting the
last referencing source removes the shared file (original behavior, retained). See data-safety.md.

## Dependency direction / route-to-component map
- main -> API routers -> services -> database connection/repositories + config; no service imports main/API.
- settings service -> SQLite; Ollama service -> settings; OCR service receives URL/capabilities as arguments.
- Knowledge -> document/PDF/OCR helpers + Ollama/settings + SQLite; chat -> attachments + Knowledge.
- frontend/core.js: utilities/shared state; sidebar.js: navigation/chat actions; chat.js: composer/stream;
  monitoring.js: dashboard/task manager charts/process list; knowledge.js: collections/preview/retrieval UI;
  settings.js: model library/settings; bootstrap.js: startup. Classic scripts share the original lexical scope.
- chat/sidebar -> `/api/chats*`, `/api/projects`; composer uploads are part of the send multipart endpoint.
- Knowledge -> `/api/kb/*`; settings -> `/api/settings*`; models -> `/api/models`, `/api/test`;
  dashboard/task manager -> `/api/metrics`, `/api/processes`.
- All 31 original method/path contracts are recorded in tests/route_contract.json and regression-checked.

## Duplication, unused elements and cycles
No duplicate source files were supplied. Duplicated text extension sets, SQLite connection handling,
PDF page handling and notebook parsing access are consolidated. Original `knowledge.py` imported unused
`os` after path resolution was centralized and had broad injected globals. There was no original Python
import cycle (server imported knowledge, which received callbacks); the mutable cross-module URL coupling
was replaced with an explicit settings accessor. Root compatibility modules contain no second implementation.
The original unused taskView local `e` helper and placeholder navigation definitions are retained to avoid unrelated edits;
no generalized dead-code cleanup/feature deletion was attempted. Queue size and serial OCR behavior are preserved.

## Feature state and pre-existing issues (not claimed fixed)
| Area | State / evidence |
|---|---|
| Chat CRUD, project assignment, pin/archive, message persistence | Implemented; API regression tests |
| Markdown export/copy, recent grouping, system prompt, stop/regenerate | Existing frontend code retained; basic browser navigation only, not all interaction paths tested |
| Model discovery/test/default selection | Implemented; HTTP-mocked tests; no live Ollama inference |
| Stream + partial error marker + DB persistence | Implemented; mocked streaming tests |
| PDF/text/notebook chat attachments; vision image payload | Implemented; PDF/helper/image payload tests; image bytes interpreted only by a live vision model |
| Knowledge collections, duplicate detection, shared files, FTS5, citations, exports, PDF preview | Implemented and regression-tested with generated non-private fixtures |
| Knowledge OCR and page retry | Implemented in original; mocked OCR success/retry and no-Ollama partial failure tested |
| Settings | Implemented; persisted and validated, default fallback retained |
| Dashboard/Task Manager | Implemented; read-only metrics/fallback/process API tested; no physical NVIDIA validation |
| Standalone OCR, Image Reader, Document Chat nav | Placeholder pages despite working related attachment/Knowledge flows |
| Images, Scheduled Tasks, Library, Plugins, Code Assistant, Explore Tools | Explicit unbuilt-stage placeholder pages, not implemented here |

Known original problems intentionally left outside this refactor:
1. Delegated action parsing uses `split(':')` with three variables. `useM:model:tag` and `testM:model:tag`
   therefore pass only `model` instead of the full tagged name. The exact original JS is retained; Settings
   dropdown saving passes the complete model name and is the workaround. A Node reproduction is in verification.
2. A stream can outlive navigation; handlers retain detached DOM references and shared generation state.
   Stop/abort persistence may depend on thread/network cancellation timing; no guarantee of full server cancellation.
3. The chart's advertised one-hour history is capped at 1,800 samples: 30 minutes at 1s polling, 60 at 2s.
4. Retrieval is keyword FTS5 with bounded passages, not embeddings or guaranteed whole-document coverage.
   Inline chat PDF extraction does not OCR scanned pages; the existing Knowledge ingestion path does.
5. Server-side validation is inconsistent: malformed `kb` JSON, unknown chat IDs, missing reindex/retry
   sources and out-of-range preview pages can raise errors or allow orphan metadata. Existing UI sends valid values.
6. The queue can race with deleting/reindexing a document; single-process serial ingestion is still required.
   Full-queue status updates and swallowed polling errors were present originally, not redesigned.
7. GPU support uses only the first nvidia-smi row; nonnumeric counters can fail. Per-process GPU usage is not collected.
8. API is local, unauthenticated, and not hardened for exposure. Existing Settings privacy copy presumes a local
   Ollama URL; configuring a remote URL sends prompts/documents there. Default remains local, no paid keys required.

These static audit observations are not fixes or claims that every edge case was reproduced live.
