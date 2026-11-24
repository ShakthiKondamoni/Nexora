import base64,hashlib,sqlite3,sys,tempfile,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class HTTPException(Exception):
 def __init__(self,status_code,detail):self.status_code=status_code;self.detail=detail;super().__init__(detail)
f=types.ModuleType('fastapi');f.HTTPException=HTTPException;sys.modules.setdefault('fastapi',f)
from backend.database import migrations
from backend.services import github_service as gh
checks=[]
def run(name,fn):
 try:fn();checks.append((name,True,''))
 except Exception as e:checks.append((name,False,repr(e)))
def migration():
 c=sqlite3.connect(':memory:');c.execute('CREATE TABLE sources(id TEXT PRIMARY KEY,coll_id TEXT,type TEXT,title TEXT,path TEXT,hash TEXT,status TEXT,error TEXT,ocr_model TEXT,added REAL)');c.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY,chat_id TEXT,role TEXT,content TEXT,context TEXT,images TEXT,names TEXT,model TEXT,created REAL)');migrations.apply_migrations(c);names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert migrations.CURRENT_VERSION==2 and {'github_projects','github_jobs','github_code_fts','github_messages'}.issubset(names)
def filters():
 v,ch=gh.pkce();assert ch==base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip('=');assert gh.safe_path('src/main.py') and not gh.safe_path('../x.py');assert gh.skip('node_modules/a.js') and gh.skip('id_rsa') and gh.skip('src/main.py') is None;assert gh._safe_text('x.py',b'API_KEY="privatevalue123456789"')[1];assert gh._safe_text('x.py',b'API_KEY="your-example-key"')[0]
def index():
 with tempfile.TemporaryDirectory() as td:
  db=Path(td)/'x.db'
  def connect():
   c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
  gh.connect=connect
  with connect() as c:c.executescript("CREATE TABLE github_jobs(id TEXT,cancel_requested INT);CREATE TABLE github_projects(id TEXT,owner TEXT,name TEXT,branch TEXT,status TEXT,updated REAL);CREATE TABLE github_project_files(id TEXT PRIMARY KEY,project_id TEXT,path TEXT,branch TEXT,commit_sha TEXT,blob_sha TEXT,file_hash TEXT,language TEXT,size_bytes INT,content TEXT,indexed_at REAL,status TEXT,UNIQUE(project_id,path));CREATE TABLE github_code_chunks(id TEXT PRIMARY KEY,project_id TEXT,file_id TEXT,path TEXT,branch TEXT,commit_sha TEXT,language TEXT,symbol TEXT,line_start INT,line_end INT,text TEXT);CREATE VIRTUAL TABLE github_code_fts USING fts5(text,chunk_id UNINDEXED,project_id UNINDEXED,path UNINDEXED,line_start UNINDEXED,line_end UNINDEXED);CREATE TABLE github_conversations(id TEXT,project_id TEXT,branch TEXT,title TEXT,created REAL,updated REAL);CREATE TABLE github_messages(id INTEGER,conversation_id TEXT,role TEXT,content TEXT,sources TEXT,created REAL);INSERT INTO github_jobs VALUES('j',0);INSERT INTO github_jobs VALUES('j2',0);INSERT INTO github_projects VALUES('p','owner','repo','main','ready',0);INSERT INTO github_projects VALUES('p2','owner','repo2','main','ready',0);")
  def cand(path,sha):return {'path':path,'sha':sha,'size':30}
  def f(sha,text):return {'blob_sha':sha,'hash':hashlib.sha256(text.encode()).hexdigest(),'content':text,'size':len(text),'language':'Python'}
  gh._snapshot('j','p','main','c1',[cand('src/auth.py','a')],{'src/auth.py':f('a','def authenticate_user(token):\\n return token')},set())
  with connect() as c:first=c.execute('SELECT id FROM github_code_chunks').fetchone()[0]
  gh._snapshot('j','p','main','c2',[cand('src/auth.py','a')],{}, {'src/auth.py'})
  with connect() as c:assert c.execute('SELECT id FROM github_code_chunks').fetchone()[0]==first
  assert gh.retrieve('p','main','authenticate_user') and gh.retrieve('p2','main','authenticate_user')==[]
  gh._snapshot('j','p','main','c3',[cand('src/new.py','b')],{'src/new.py':f('b','def fresh():\\n return 1')},set())
  with connect() as c:assert [r[0] for r in c.execute('SELECT path FROM github_project_files')]==['src/new.py']
  with connect() as c:c.execute("UPDATE github_jobs SET cancel_requested=1 WHERE id='j2'")
  try:gh._snapshot('j2','p2','main','c1',[],{},set());raise AssertionError('cancel ignored')
  except gh.Cancelled:pass
def insufficient():
 with tempfile.TemporaryDirectory() as td:
  db=Path(td)/'x.db'
  def connect():
   c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
  gh.connect=connect
  with connect() as c:c.executescript("CREATE TABLE github_projects(id TEXT,owner TEXT,name TEXT,branch TEXT,status TEXT,updated REAL);CREATE TABLE github_conversations(id TEXT,project_id TEXT,branch TEXT,title TEXT,created REAL,updated REAL);CREATE TABLE github_messages(id INTEGER,conversation_id TEXT,role TEXT,content TEXT,sources TEXT,created REAL);INSERT INTO github_projects VALUES('p','o','r','main','ready',0);")
  gh.retrieve=lambda *a:[];out=gh.chat('p','where is code?');assert 'not find enough relevant evidence' in out['answer'].lower() and out['sources']==[]
run('v2 migration on Task 2 schema',migration);run('PKCE/path/secret filters',filters);run('incremental index/isolation/deletion/cancel',index);run('insufficient-evidence response',insufficient)
for n,ok,e in checks:print(('PASS ' if ok else 'FAIL ')+n+((': '+e) if e else ''))
if not all(x[1] for x in checks):raise SystemExit(1)
print('4 smoke checks passed')
