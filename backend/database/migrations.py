"""Additive, versioned SQLite Knowledge migration."""
from datetime import datetime,timezone
CURRENT_VERSION=1
def _cols(c,t): return {r[1] for r in c.execute(f'PRAGMA table_info({t})')}
def apply_migrations(c):
 c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL)')
 versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}
 if 1 not in versions:
  cols=_cols(c,'sources')
  for n,d in [('size_bytes','INTEGER NOT NULL DEFAULT 0'),('mime_type','TEXT NOT NULL DEFAULT "application/octet-stream"'),('extension','TEXT NOT NULL DEFAULT ""'),('processed_at','REAL'),('updated','REAL'),('extractor','TEXT NOT NULL DEFAULT ""')]:
   if n not in cols: c.execute(f'ALTER TABLE sources ADD COLUMN {n} {d}')
  if 'sources' not in _cols(c,'messages'): c.execute('ALTER TABLE messages ADD COLUMN sources TEXT')
  c.execute("""CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,coll_id TEXT NOT NULL,ordinal INTEGER NOT NULL,loc INTEGER NOT NULL,kind TEXT NOT NULL,label TEXT NOT NULL,start_char INTEGER NOT NULL,end_char INTEGER NOT NULL,text TEXT NOT NULL,created REAL NOT NULL)""")
  c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id,ordinal)')
  c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_collection ON chunks(coll_id,source_id)')
  c.execute('CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(text,chunk_id UNINDEXED,source_id UNINDEXED,coll_id UNINDEXED,loc UNINDEXED,label UNINDEXED)')
  c.execute('INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)',(1,datetime.now(timezone.utc).isoformat()))
 c.execute('CREATE INDEX IF NOT EXISTS idx_sources_hash_coll ON sources(coll_id,hash)')


_v1_apply_migrations=apply_migrations
CURRENT_VERSION=2
def apply_migrations(c):
 _v1_apply_migrations(c)
 c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL)')
 versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}
 if 2 in versions:return
 statements=[
 "CREATE TABLE IF NOT EXISTS github_oauth_state(state TEXT PRIMARY KEY,verifier TEXT NOT NULL,created REAL NOT NULL)",
 "CREATE TABLE IF NOT EXISTS github_projects(id TEXT PRIMARY KEY,repo_id INTEGER NOT NULL,owner TEXT NOT NULL,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',html_url TEXT NOT NULL,private INTEGER NOT NULL DEFAULT 0,default_branch TEXT NOT NULL,branch TEXT NOT NULL,commit_sha TEXT NOT NULL DEFAULT '',indexed_revision TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'new',include_paths TEXT NOT NULL DEFAULT '[]',last_synced REAL,created REAL NOT NULL,updated REAL NOT NULL)",
 "CREATE INDEX IF NOT EXISTS idx_github_projects_repo ON github_projects(repo_id,branch)",
 "CREATE TABLE IF NOT EXISTS github_jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,progress REAL NOT NULL DEFAULT 0,files_total INTEGER NOT NULL DEFAULT 0,files_done INTEGER NOT NULL DEFAULT 0,bytes_total INTEGER NOT NULL DEFAULT 0,bytes_done INTEGER NOT NULL DEFAULT 0,current_file TEXT,error TEXT,skipped_json TEXT NOT NULL DEFAULT '[]',cancel_requested INTEGER NOT NULL DEFAULT 0,started REAL,finished REAL,created REAL NOT NULL)",
 "CREATE INDEX IF NOT EXISTS idx_github_jobs_project ON github_jobs(project_id,created)",
 "CREATE TABLE IF NOT EXISTS github_project_files(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,path TEXT NOT NULL,branch TEXT NOT NULL,commit_sha TEXT NOT NULL,blob_sha TEXT NOT NULL,file_hash TEXT NOT NULL,language TEXT NOT NULL,size_bytes INTEGER NOT NULL,content TEXT NOT NULL,indexed_at REAL NOT NULL,status TEXT NOT NULL DEFAULT 'indexed',UNIQUE(project_id,path))",
 "CREATE TABLE IF NOT EXISTS github_code_chunks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,file_id TEXT NOT NULL,path TEXT NOT NULL,branch TEXT NOT NULL,commit_sha TEXT NOT NULL,language TEXT NOT NULL,symbol TEXT NOT NULL,line_start INTEGER NOT NULL,line_end INTEGER NOT NULL,text TEXT NOT NULL)",
 "CREATE VIRTUAL TABLE IF NOT EXISTS github_code_fts USING fts5(text,chunk_id UNINDEXED,project_id UNINDEXED,path UNINDEXED,line_start UNINDEXED,line_end UNINDEXED)",
 "CREATE TABLE IF NOT EXISTS github_conversations(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,branch TEXT NOT NULL,title TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL)",
 "CREATE TABLE IF NOT EXISTS github_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,sources TEXT,created REAL NOT NULL)"
 ]
 for sql in statements:c.execute(sql)
 c.execute('INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)',(2,datetime.now(timezone.utc).isoformat()))


_v2_apply_migrations = apply_migrations
def apply_migrations(c):
    _v2_apply_migrations(c)
    c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_owner(id INTEGER PRIMARY KEY CHECK(id=1),email TEXT NOT NULL COLLATE NOCASE UNIQUE,password_hash TEXT,google_sub TEXT UNIQUE,created REAL NOT NULL,updated REAL NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,created REAL NOT NULL,expires REAL NOT NULL,last_seen REAL NOT NULL)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_oauth_state(state_hash TEXT PRIMARY KEY,provider TEXT NOT NULL,verifier TEXT NOT NULL,nonce TEXT NOT NULL,browser_hash TEXT NOT NULL,session_hash TEXT,created REAL NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_reset_tokens(token_hash TEXT PRIMARY KEY,owner_id INTEGER NOT NULL,expires REAL NOT NULL,created REAL NOT NULL,consumed REAL)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_auth_reset_expiry ON auth_reset_tokens(expires)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_rate_limits(bucket TEXT PRIMARY KEY,window_start REAL NOT NULL,attempts INTEGER NOT NULL)")
    cols={r[1] for r in c.execute('PRAGMA table_info(github_oauth_state)')}
    if 'browser_hash' not in cols: c.execute('ALTER TABLE github_oauth_state ADD COLUMN browser_hash TEXT')
    if 'session_hash' not in cols: c.execute('ALTER TABLE github_oauth_state ADD COLUMN session_hash TEXT')
    versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}
    if 3 not in versions:
        from datetime import datetime, timezone
        c.execute('INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)',(3,datetime.now(timezone.utc).isoformat()))


_task5_prev_apply=apply_migrations
CURRENT_VERSION=4
def apply_migrations(c):
    _task5_prev_apply(c)
    if 'web_mode' not in _cols(c,'messages'):
        c.execute("ALTER TABLE messages ADD COLUMN web_mode TEXT NOT NULL DEFAULT 'off'")
    versions={int(r[0]) for r in c.execute('SELECT version FROM schema_migrations')}
    if 4 not in versions: c.execute('INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)',(4,datetime.now(timezone.utc).isoformat()))
