# Changelog

## Modularization / packaging phase
- Moved the actual FastAPI routes into five thin API modules without changing method/path contracts.
- Extracted existing chat, Ollama, attachment, PDF, notebook/chunking, OCR, Knowledge, settings and monitoring logic.
- Centralized filesystem/configuration and SQLite connection/query operations; preserved original schema.
- Externalized the original frontend CSS and seven ordered classic JavaScript assets; no redesign or new features.
- Retained minimal server.py / knowledge.py compatibility shims, not duplicate implementations.
- Added isolated regression tests, route inventory, input checksums, safe DB backup/install checks, documentation,
  pinned tested dependencies and a Windows venv-based launcher.
- Added startup safety: explicit new-DB initialization, integrity checks, ambiguous DB detection, no query-time
  empty DB creation, backups before original compatibility DDL, stable paths independent of shell working directory.
- Removed the need to synchronize a mutable knowledge.OLLAMA global; OCR reads current saved endpoint settings.
- Database/upload contents and temporary verification dependencies are not distributed.

## Known pre-existing issues
See docs/audit.md. Tagged-model menu action parsing, streaming/navigation edge cases, queue races,
keyword-only retrieval, placeholder pages and incomplete defensive validation are not represented as fixed.

## Future phases (NOT implemented)
GitHub integration; web search/scraping; IDE/workspace; MCP; new Knowledge features;
new OCR engines/workflows; new standalone OCR/Image Reader/Document Chat pages; UI redesign.

## Task 2 — Knowledge Base
- Added additive migration/backup, persistent overlapping chunk metadata and FTS5 retrieval.
- Added safe multi-format ingestion, PDF text-first/local OCR workflow, local image OCR, collection-scoped search, grounded Ollama answers, citations and inspectable passages.
- Added tests and Knowledge documentation; no cloud services, embeddings, or unrelated features.
