# Verification report

## Scope and method
This phase reorganized the supplied FastAPI/Ollama application. It did not implement the staged GitHub,
search, scraping, IDE, MCP, new Knowledge/OCR or other placeholder features, and did not redesign the UI.
Original source inputs and the supplied personal database were kept unchanged. Temporary verification
wheels, generated test documents and private data are not part of the distribution.

## Recorded results
| Check | Actual result |
|---|---|
| Untouched original baseline | **12 passed**, one upstream deprecation warning (4.19 seconds) |
| Modular full automated suite | **35 passed**: all 12 original tests plus 23 added regressions |
| Original test preservation | AST comparison confirms all 12 original test function bodies/assertions are unchanged; only environment setup was adapted to the shared isolation fixture |
| Unit-only invocation | **8 passed** independently; these eight are already included in the 35, not additional tests |
| Python compileall | Passed for backend, scripts, tests and compatibility entry points |
| Original API contracts | All **31** original method/path contracts registered once; 36 app routes/mounts including framework docs and static mounting |
| API/static regression checks | Chat/project CRUD, persistence, settings, model discovery, stream/partial errors/regeneration, file/image context, Knowledge/citations/preview/export, monitoring fallback and all relocated assets passed |
| JavaScript syntax | All **7** external scripts passed `node --check` |
| Frontend preservation | Extracted script content matches the original apart from boundary whitespace; original stylesheet matches exactly after surrounding whitespace trimming |
| Browser smoke check | Headless Chromium 150 over CDP **pipes**, local-file harness and captured API fixtures; **15** navigation destinations rendered, **8** assets loaded, **0** uncaught JavaScript exceptions |
| Browser interface comparison | Original/modular initial title, navigation labels, hero, sidebar width and composer placeholder match; original CSS matches |
| Knowledge browser flow | Create/list/open collection rendered using an explicitly mocked/captured API fixture; not represented as live browser-to-server interaction |
| Existing supplied DB compatibility | A scratch copy opened successfully; schema, rows and file bytes unchanged; quick_check `ok`; original supplied DB bytes unchanged |
| DB/path safety | Missing DB refused without creation; explicit fresh initialization succeeds; existing DB reopening succeeds; relative configured paths independent of shell CWD; old-schema compatibility backup/row preservation tested |
| Import layering | Static graph covers **24** backend Python modules; **0** cycles and **0** service-to-API/main dependencies |
| Startup alignment | Launcher/README point to `python -m backend.main`, URL 127.0.0.1:8501 and the real verifier; no Ollama start/kill commands |

## Runtime and dependency details
Verification used Linux, Python 3.13, FastAPI 0.115.12, Starlette 0.46.2, PyMuPDF 1.26.7,
psutil 7.0.0, pytest 9.1.1, httpx 0.28.1 and Node 26.12.1. The same eight direct application/test
dependencies are retained, pinned to verified versions, with transitive constraints. Node/Chromium and
the temporary Linux wheel bundle are verification tools only, not new application dependencies.

The full suite emits one upstream Starlette/AnyIO `BlockingPortal` alias deprecation warning;
it is not a test failure. The standalone unit-only run has no such API-import warning.

## Failures encountered and disposition
- Initial baseline collection was blocked by missing sandbox dependencies. Isolated temporary wheels were
  staged and the untouched original baseline then passed. No replacement PDF implementation was introduced.
- One support-assembly run omitted its original test input. Correcting the staged input list resolved it.
- A test-harness unit-only assumption was corrected so unit tests initialize their own isolated schema.
- A real Uvicorn process completed application startup but **could not bind 127.0.0.1** in this sandbox;
  direct loopback requests failed with network errno 101. This is why browser checks use a local-file harness,
  captured API responses and CDP pipes. Backend APIs/assets were separately tested in-process with TestClient.

## Limitations — not claimed tested
- **Windows execution was unavailable.** The batch file was inspected, uses Windows line endings, resolves
  paths relative to itself, checks Python, creates a venv, installs requirements, checks configuration, requires
  deliberate first-DB initialization, launches the correct module, and keeps errors visible. That is not a
  claim that it was run on Windows. Windows dependency installation also was not exercised here.
- **Live Ollama inference, model discovery against an actual daemon, vision interpretation and real model OCR
  were unavailable.** Their success/payload/error paths use mocks; failure handling was also exercised without Ollama.
- **No browser-to-live-Uvicorn end-to-end run** was possible because sandbox loopback sockets are prohibited.
  Offline Chromium results do not verify Windows browser networking or all interactive/cancellation flows.
- No physical NVIDIA GPU/driver or per-process GPU validation was available. Original fallback and read-only
  monitoring contracts were checked. Host metrics from the sandbox are not a hardware benchmark.
- No uploaded source documents were supplied alongside the private DB (its Knowledge source tables were empty).
  Shared-file preservation was tested with generated non-private fixtures, not with a missing personal corpus.
- Known original issues remain documented in audit.md, including colon-tag action parsing, streaming/navigation
  edge cases, bounded keyword retrieval, queue races and staged placeholder pages. These are not advertised as fixed.

## Reproduction
From the extracted project folder, after installing requirements:
- `.venv\Scripts\python -m pytest -q`
- `.venv\Scripts\python -m pytest -q tests/unit`
- `.venv\Scripts\python -m compileall -q backend scripts tests server.py knowledge.py`
- `.venv\Scripts\python scripts\verify_installation.py` (existing configured DB)
- For a genuinely NEW empty installation only, use the verifier's `--initialize` flag.

The final packaging procedure checks archive entries/CRC, excludes private/runtime files, lists its contents,
extracts it to a new directory and reruns compilation, the full suite, unit subset, JavaScript syntax and
configuration/import checks. The final chat handoff reports those fresh-extraction results and exact ZIP location.
