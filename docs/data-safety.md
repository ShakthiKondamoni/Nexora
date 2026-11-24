# Existing data: preserve it, do not initialize a replacement

The supplied database was inspected read-only and was **not** bundled. Its schema is compatible;
no refactor migration is required. It contains chat history. No uploaded Knowledge source rows or
upload files were supplied. Never commit or redistribute your personal database or upload folder.

## Safest option: keep the original database and files in place
1. Stop both the old and new Studio processes (`Ctrl+C`) and wait for ingestion to finish.
2. Back up your original database to a NEW filename (the utility refuses overwriting):
   `.venv\Scripts\python scripts\backup_database.py --database "C:\OldStudio\studio.db" --output "C:\StudioBackups\studio-before-modular.db"`
3. Copy the complete old `files` folder to a separate backup as well. SQLite backup does not copy documents.
4. In the Command Prompt that will launch the new Studio:
   `set "STUDIO_DB=C:\OldStudio\studio.db"`
   `set "STUDIO_FILES=C:\OldStudio\files"`
5. Run `run_studio.bat`. Do NOT choose/authorize a new database if you expect existing history.
6. Verify history, settings and Knowledge source files before changing/removing the old installation.

Use one Studio process only. Original DB connections, queue behavior and startup interruption marking
are retained; multiple app workers/processes could race over ingestion. This is not a multi-user server.

## Path rules
- Explicit STUDIO_DB and STUDIO_FILES may be absolute, or relative to this project's root (not the shell CWD).
- Without STUDIO_DB, an existing root `studio.db` is used, otherwise `data/studio.db`.
- If both default locations exist, startup refuses to guess: set STUDIO_DB explicitly.
- Stored absolute `sources.path` values stay unchanged. They must remain reachable, including their drive letters.
- Stored relative `sources.path` values resolve relative to the database's directory. The original normal
  startup stored absolute paths; if you previously used custom relative settings, confirm paths carefully.
- STUDIO_FILES controls NEW Knowledge uploads; it does **not** rewrite old sources.path entries.
- Do not relocate a DB alone and assume setting STUDIO_FILES repairs old references. Keeping old data in place
  is recommended. A relocation requires restoring files at referenced paths or a separately reviewed path-only migration.
- Text/PDF/notebook chat context and image bytes are inline in messages; chat attachments are not independent disk files.

## Missing/corrupt databases and backups
Normal DB queries use SQLite mode=rw, never automatic creation. Missing explicit databases fail startup.
The launcher offers new initialization only for an unconfigured fresh installation with no previous
`data/.initialized` marker. If this marker exists but the DB is missing, startup stops rather than replacing history.
An empty distribution cannot distinguish a first install from data lost before extraction: never confirm a fresh
installation if you expect existing data. The initializer's --initialize flag is deliberate permission to create an empty DB.

The original eight application tables and FTS5 layout are preserved. If an older database is missing original
tables or the original messages.sources compatibility column, the initializer makes a timestamped SQLite backup
**before** running that original DDL. It checks integrity and does not swallow migration errors. No destructive
migration is added. To reverse such compatibility initialization: stop Studio, save the current DB, and restore
the backup to the configured DB path; no private files are removed by initialization.
