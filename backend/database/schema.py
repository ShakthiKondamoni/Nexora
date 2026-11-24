"""SQLite schema and safe, additive migration with a pre-migration backup."""
import os,sqlite3
from datetime import datetime,timezone
from backend.core.config import DB_PATH,FILES
from backend.database.migrations import apply_migrations,CURRENT_VERSION
STATEMENTS=['CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT)','CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,title TEXT,pinned INT DEFAULT 0,archived INT DEFAULT 0,project_id TEXT,updated REAL)','CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id TEXT,role TEXT,content TEXT,context TEXT,images TEXT,names TEXT,model TEXT,created REAL)','CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)','CREATE TABLE IF NOT EXISTS collections(id TEXT PRIMARY KEY,name TEXT,created REAL)','CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,coll_id TEXT,type TEXT,title TEXT,path TEXT,hash TEXT,status TEXT,error TEXT,ocr_model TEXT,added REAL)','CREATE TABLE IF NOT EXISTS pages(source_id TEXT,loc INT,kind TEXT,status TEXT,text TEXT,error TEXT,PRIMARY KEY(source_id,loc))','CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(text,source_id UNINDEXED,coll_id UNINDEXED,loc UNINDEXED)']
def _needs_migration(c):
 names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 if 'schema_migrations' not in names or not {'sources','messages'}.issubset(names): return True
 versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}; cols={r[1] for r in c.execute('PRAGMA table_info(sources)')}; msg={r[1] for r in c.execute('PRAGMA table_info(messages)')}
 return CURRENT_VERSION not in versions or not {'size_bytes','mime_type','extension','processed_at','updated','extractor'}.issubset(cols) or 'sources' not in msg or not {'chunks','chunk_fts'}.issubset(names)
def initialize_database(allow_create: bool=False):
 existed=DB_PATH.exists()
 if not existed and not (allow_create or os.environ.get('STUDIO_INIT_DB')=='1'): raise RuntimeError(f'Refusing to create a missing database: {DB_PATH}. For a fresh installation run: python scripts/verify_installation.py --initialize')
 DB_PATH.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(DB_PATH.as_uri()+('?mode=rw' if existed else '?mode=rwc'),uri=True)
 try:
  check=c.execute('PRAGMA quick_check').fetchone()[0]
  if check!='ok': raise RuntimeError(f'Database integrity check failed: {check}')
  if existed and _needs_migration(c):
   stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); backup=DB_PATH.with_name(DB_PATH.name+'.backup-'+stamp)
   with sqlite3.connect(backup) as dest: c.backup(dest)
   print('Backup before Knowledge schema migration:',backup)
  with c:
   for sql in STATEMENTS: c.execute(sql)
   apply_migrations(c)
   check=c.execute('PRAGMA quick_check').fetchone()[0]
   if check!='ok': raise RuntimeError(f'Database integrity check failed after migration: {check}')
 finally: c.close()
 FILES.mkdir(parents=True,exist_ok=True); return DB_PATH


_v1_needs_migration=_needs_migration
def _needs_migration(c):
 if _v1_needs_migration(c):return True
 names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 return not {'github_projects','github_jobs','github_project_files','github_code_chunks','github_code_fts','github_conversations','github_messages','github_oauth_state'}.issubset(names)


_v2_needs_migration = _needs_migration
def _needs_migration(c):
    if _v2_needs_migration(c): return True
    versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}
    names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return 3 not in versions or not {'auth_owner','auth_sessions','auth_oauth_state','auth_reset_tokens','auth_rate_limits'}.issubset(names)


_task5_prev_needs=_needs_migration
def _needs_migration(c):
    if _task5_prev_needs(c): return True
    names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'messages' not in names: return True
    cols={r[1] for r in c.execute('PRAGMA table_info(messages)')}
    versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')} if 'schema_migrations' in names else set()
    return 'web_mode' not in cols or 4 not in versions
