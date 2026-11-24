# Nexora — modularized existing application

This is the supplied FastAPI/Ollama application reorganized into maintainable modules, not a new prototype.
The original interface, API contracts, model endpoint, streaming protocol and SQLite schema are retained.
GitHub is available as a read-only repository integration configured by an administrator; no GitHub write operations, web search/scraping, IDE, MCP, paid API, or cloud inference service is included.

## Windows: extract and run
1. Extract **LocalAIStudio_Modular.zip** completely. Open the extracted **LocalAIStudio_Modular** folder.
   Do not run inside the ZIP. Use a writable folder (not Program Files).
2. Install **Python 3.11+** (3.13 was used for Linux verification), with the `py` launcher or Python on PATH.
   First dependency installation requires internet access. No packages/model weights are bundled.
3. **Existing user:** follow `docs/data-safety.md` FIRST: stop Studio, make a database + files backup,
   and set STUDIO_DB / STUDIO_FILES to your original data before starting. Personal data is not in this ZIP.
4. Double-click **run_studio.bat** or run it from a Command Prompt in this folder. It detects Python,
   creates `.venv` if needed, installs `requirements.txt`, checks files/config/SQLite/FTS5 and starts
   **`python -m backend.main`**. It does not start, stop or kill Ollama.
5. **New installation only:** when no DB is configured/found, the launcher asks before creating an empty DB.
   Answer Y only if you want a new empty application. Existing users must answer N and select their old DB.
6. Once Uvicorn reports startup, open **http://127.0.0.1:8501**. The script intentionally does not open a
   browser prematurely. Keep its console open. Errors remain visible; press a key only after reading them.
7. Start/keep Ollama running separately, as before, with models installed. Default URL is
   **http://localhost:11434**. Select a default model in Settings. No models are downloaded by Studio.
8. Stop Studio with **Ctrl+C** in its console (confirm batch termination if Windows asks). Ollama keeps running.

If a configured DB is missing/corrupt, or a previously initialized default DB disappears, startup stops.
Do not delete the `.initialized` marker or approve new initialization to work around lost history.
If both `studio.db` and `data/studio.db` exist, set STUDIO_DB explicitly rather than guessing.

## Manual commands (Command Prompt, from this project folder)
```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\verify_installation.py
```
For a genuinely NEW empty installation only, authorize initialization explicitly:
```
.venv\Scripts\python scripts\verify_installation.py --initialize
```
Then:
```
.venv\Scripts\python -m backend.main
```
Compatibility `python server.py` still starts the same application. Use a single process (no --workers/reload).
The installation checker is **scripts/verify_installation.py**. It does not require Ollama and checks
configured upload references before starting. `STUDIO_INIT_DB=1` is also understood for automated disposable
installations; do not leave it enabled for normal use. local environment template is documentation, not automatically read.

## Configure existing local data / Ollama
```
set "STUDIO_DB=C:\OldStudio\studio.db"
set "STUDIO_FILES=C:\OldStudio\files"
set "OLLAMA_HOST=http://localhost:11434"
run_studio.bat
```
These are process environment variables, not permanent settings. Use the same console.
Saved `settings.ollama_url` overrides the OLLAMA_HOST default, as in the original application.
Changing STUDIO_FILES does not rewrite existing sources.path references. Back up and see
`docs/data-safety.md` before relocation; using data in place avoids path changes.

## Test / verify
```
.venv\Scripts\python -m compileall -q backend scripts tests server.py knowledge.py
.venv\Scripts\python -m pytest -q
```
Tests use a disposable temporary database/upload folder and mocked network requests; they do NOT use
personal data, execute notebook cells, call real Ollama or require a GPU. All 12 original test functions
and assertions are retained under tests/integration/test_studio.py with fixture-safe environment setup.
Additional regressions cover moved modules, route contracts, static assets, stream/attachment/DB behavior,
configuration, backup and original-schema compatibility. Tests require installed dependencies.
If Node.js is available, check each file in frontend/assets/js with `node --check <file>` (not a runtime dependency).
Read **docs/verification.md** for actual results and limitations. Windows batch execution and live Ollama
inference were not available in the Linux test environment. Do not confuse mocked inference with live testing.

## Task 4: Connected Apps and Appearance

- **Settings → Connected Apps** shows Google sign-in readiness, GitHub connection status, and optional email configuration. The Google status is provider readiness, not a separate linked-account indicator.
- GitHub uses the existing server-side GitHub App OAuth flow. An administrator configures the GitHub App Client ID and Client Secret once under `/setup` (Account & Integrations); they are stored through the operating-system credential store and are not exposed in browser code. Register the callback URL shown by the setup page. End users do not enter personal access tokens or OAuth secrets.
- Users select **Connect GitHub** from Connected Apps, then browse accessible repositories and branches, search the repositories currently loaded, inspect eligible paths, and import selected files or folders. Imports remain read-only and isolated as project-aware code content; sync and local Ollama project chat are available in the GitHub Projects view. No push, commit, or pull-request operation is implemented.
- **Settings → Appearance** offers System, Light, and Dark. The choice is stored in the existing SQLite settings table without replacing other settings and applies without a restart. Dark is the default; System follows OS changes.
- Live GitHub OAuth and repository browsing require an administrator-configured GitHub App and internet access. They are not considered live-tested by the offline/automated test suite.

## Layout / module map
```
LocalAIStudio_Modular/
  run_studio.bat, requirements.txt, constraints.txt, README.md, CHANGELOG.md
  .gitignore, local environment template, pytest.ini
  server.py, knowledge.py                  # compatibility shims only
  backend/
    main.py                               # app wiring/static mount/Uvicorn
    api/{chat,models,knowledge,settings,monitoring}.py
    services/{chat,file,pdf,document,ocr,knowledge,ollama,settings,monitoring}_service.py
    database/{connection,repositories,schema}.py
    core/config.py
  frontend/
    index.html
    assets/css/studio.css
    assets/js/{core,sidebar,chat,monitoring,knowledge,settings,bootstrap}.js
  tests/
    conftest.py, route_contract.json
    integration/{test_studio,test_refactor}.py
    unit/test_safety.py
  scripts/{backup_database,verify_installation}.py
  data/README.md                          # safe new initialization; private runtime DB excluded
  files/README.md                         # private Knowledge uploads excluded
  docs/{audit,data-safety,verification}.md, source_checksums.json
```
Package `__init__.py` files are also included. No empty uploads API, ORM models, icon/image directories,
logging framework or exceptions abstraction was created: uploads already belong to chat/Knowledge,
schema.py defines the actual SQLite DDL, icons are inline SVG, and existing error contracts are preserved.

## Preserved behavior and limitations
Chat history/projects/pins/archive, model discovery/default settings, streamed replies/stop/regenerate,
text/PDF/notebook/image attachments, Knowledge collections/OCR/retry/search/citations/previews/exports,
Dashboard/Task Manager and read-only CPU/RAM/disk/NVIDIA monitoring remain in their original flows.
See docs/audit.md for evidence and known pre-existing limitations. Staged placeholder pages remain placeholders.
In particular, inline chat PDF extraction does not perform OCR; the existing Knowledge ingestion does.
For tagged models use the Settings dropdown: the original Model Library action parser truncates `:tag`.
This is a local unauthenticated app: keep it bound to 127.0.0.1; no security/exposure redesign is included.

A consistent DB backup (source/destination must be different; destination must not exist):
```
.venv\Scripts\python scripts\backup_database.py --database "C:\OldStudio\studio.db" --output "C:\StudioBackups\before-modular.db"
```
Stop Studio and copy uploaded files separately. The backup script does not move or rewrite private data.


## Knowledge Base and document processing

Task 2 adds persistent collections, multi-file ingestion, SQLite FTS5 chunk search, and document-grounded Q&A. Inputs include PDF, TXT/Markdown, DOCX, CSV/JSON, notebooks, common source/config text, and PNG/JPEG/WebP. PDF text is extracted before OCR; only low-text pages use a selected local Ollama vision model. There are no cloud OCR/search services and no automatic model downloads. View documents for extracted text, status, page errors and source passages; retry a page or re-index a document. See `docs/knowledge-base.md` for supported formats, settings, storage, citations, and troubleshooting.


## GitHub Projects and safe chat formatting

### GitHub App setup
Create a GitHub App, enable user authorization and expiring user tokens, set the callback to `http://127.0.0.1:8501/api/github/callback`, and grant only **Metadata: read-only** and **Contents: read-only**. Install/authorize the App for repositories you need. In Nexora > GitHub Projects, save the App Client ID and Client Secret, then authorize the account. PKCE S256 and state validation protect the authorization flow; `offline_access` supports refresh tokens. Tokens/client secret are stored by Python `keyring` in the OS credential manager and never returned to JavaScript or written to `.env`, logs, or the database. Disconnect asks GitHub to revoke and deletes local credentials even if remote revoke cannot be reached.

Browse repositories/branches, preview text files, import a repository or checked paths, and monitor/cancel import jobs. Limits: 1,500 files, 512 KB per file, 50 MB per selection. VCS directories, common build/cache folders, unsupported/binary/oversized files, likely credential files, and common secret assignments are skipped. Code is never executed. Synchronization is manual; changed/new files are reindexed, unchanged blobs reuse chunks, deleted files are removed, and a failed fetch retains the previous index. GitHub writes, commits, and PRs are not implemented. Root `.gitignore` patterns are applied with basic glob support; nested ignore semantics are a limitation.

Open a project to browse indexed source and ask questions. Search is project/branch scoped SQLite FTS5, chat history is separate from ordinary chats, and local Ollama is required. Answers show retrieved passages and file/line citations; if evidence is not found, the app says so. Keep the app on loopback; it is not designed to be exposed to untrusted networks.

### Markdown rendering
Marked v18.0.14 parses GFM Markdown; DOMPurify 3.4.16 sanitizes output. Headings, emphasis, lists, blockquotes, code, tables, rules, and safe links are rendered. External links use `noopener noreferrer`; unsafe HTML/events/protocols are blocked. A narrow normalizer repairs clearly accidental escaped structural Markdown and literal escaped newlines only when format signals are present; stored model responses are not altered. Mathematical typesetting is not added.

Troubleshoot OAuth by checking callback URL, App user authorization, expiring tokens, and repository installation. 403/404 usually mean missing App permissions/access; 429 includes a retry time. Keyring errors require the pinned dependency and an OS credential backend. Project inference refuses non-local Ollama endpoints; select an installed model in Settings. No credentials, models, or private repository contents are packaged.


## Optional accounts and integrations

See [Authentication and integrations](docs/authentication.md) for optional single-owner sign-in, Google, read-only GitHub App connection, and SMTP password recovery setup. No cloud account is required for local Ollama and existing local features.


## Nexora Web Research

Web Search is optional in chat. Configure the no-key SearXNG provider in **Settings → Web & Research**; use Search first for model-independent research, or Automatic with compatible Ollama tool-calling models. See [docs/web-research.md](docs/web-research.md). Web Search Off remains local-only.


## Web & Research

Open **Settings → Web & Research** to configure a self-hosted SearXNG instance (JSON output enabled). Chat supports Off (local-only), Search first, and Automatic native tools for compatible Ollama models. Off does not access the internet. See [docs/web-research.md](docs/web-research.md) and the secret-free [provider example](docs/searxng-provider.example.json).

## Task 6 — Composer, desktop shell, and Code Assistant

The chat composer provides **Off**, **Search first**, and **Automatic** Web Search modes. The selected mode continues through the existing `web_mode` chat field and real research services; the SQLite settings table stores the default, while per-conversation choices are remembered in browser storage.

The **Code Assistant** opens a project folder using a native picker. It indexes only supported text files, skips secrets, generated directories, databases, binary/oversize files, and symbolic links/reparse points. Search scans a bounded amount of source and sends a small set of relevant excerpts to a loopback Ollama model. Proposed unified diffs are validated and shown before approval; applying rechecks file hashes and writes recoverable copies to `.nexora-backups/`. Nexora does not execute test or shell commands.

### Optional Windows desktop
Install the main requirements and `requirements-desktop.txt`; run `python desktop/launcher.py` for the source desktop shell. It binds the existing FastAPI application to an OS-assigned loopback port, waits for readiness, uses `%APPDATA%\Nexora` for packaged data, and stops its server thread on close. To build on Windows, install Microsoft Edge WebView2 Runtime and Inno Setup 6, then run `powershell -ExecutionPolicy Bypass -File desktop/build_windows.ps1`. This sandbox did not build a Windows installer.

Run focused tests with `python -m unittest tests.test_task6_workspace`. The existing pytest suite and real Ollama/web integrations require the normal project dependencies and were not run in this sandbox.

## Task 7: diagnostics and Windows desktop build

The sidebar **System Status** checks backend, SQLite availability (read-only), Ollama and selected-model availability, web search, and GitHub configuration. The copied report excludes credentials, service URLs, and document contents. A stored GitHub credential is not proof of repository access.

### Windows desktop build

No compiled installer is included in this source archive. Build on Windows with Python on `PATH`, Microsoft Edge WebView2 Runtime, and Inno Setup 6 installed:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-desktop.txt
powershell -ExecutionPolicy Bypass -File .\desktop\build_windows.ps1
```

The script builds `dist\Nexora`; with Inno Setup 6 it creates `dist-installer\Nexora-Setup.exe`. Install Ollama/model weights separately; none are bundled or downloaded. Desktop starts a loopback-only backend on an ephemeral port and waits for `/api/health`. Browser startup via `run_studio.bat` remains supported.

### Desktop data and backup

Packaged Windows data is under `%APPDATA%\Nexora\` (`studio.db` and `files\`). Close Nexora and copy the whole directory to secure storage; restore with the app closed by replacing that directory. Do not delete/recreate the DB to troubleshoot; see `docs/data-safety.md`.

This archive was prepared in a non-Windows sandbox. No Windows installer, live integrations, or fresh GUI screenshots were produced or tested. Existing screenshots are previews, not live captures. See `docs/task7-audit.md` and `docs/task7-test-report.md`.
