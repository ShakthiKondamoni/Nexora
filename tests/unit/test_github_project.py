import base64,hashlib,time
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from backend.services import github_service as gh

def test_pkce_s256():
 v,c=gh.pkce();assert c==base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip('=')
def test_path_and_filter():
 assert gh.safe_path('src/a.py') and not gh.safe_path('../a.py') and not gh.safe_path('C:\\a.py')
 assert gh.skip('node_modules/a.js') and gh.skip('id_rsa') and gh.skip('src/a.py') is None
def test_secret_filter():
 assert gh._safe_text('config.py',b'API_KEY="supersecretvalue123456789"')[1]
 assert gh._safe_text('config.py',b'API_KEY="your-example-key"')[0]
def test_api_rate_limit(monkeypatch):
 monkeypatch.setattr(gh,'_token',lambda:'mock');r=Mock(status_code=403,text='rate limit',headers={'X-RateLimit-Remaining':'0','X-RateLimit-Reset':str(int(time.time())+30)});monkeypatch.setattr(gh.requests,'request',lambda *a,**k:r)
 with pytest.raises(HTTPException) as e:gh._request('GET','/user')
 assert e.value.status_code==429
def test_repo_pagination(monkeypatch):
 r=Mock(headers={'Link':'<next>; rel="next"'});r.json.return_value=[{'id':1,'owner':{'login':'o'},'name':'r','full_name':'o/r','private':True,'default_branch':'main'}];monkeypatch.setattr(gh,'_request',lambda *a,**k:r)
 d=gh.repositories();assert d['next_page']==2 and d['repositories'][0]['private']
def _fixture(monkeypatch,tmp_path):
 import sqlite3
 db=tmp_path/'test.db'
 def con():c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
 monkeypatch.setattr(gh,'connect',con)
 with con() as c:
  c.executescript("CREATE TABLE github_jobs(id TEXT,cancel_requested INT);CREATE TABLE github_projects(id TEXT,status TEXT,updated REAL);CREATE TABLE github_project_files(id TEXT PRIMARY KEY,project_id TEXT,path TEXT,branch TEXT,commit_sha TEXT,blob_sha TEXT,file_hash TEXT,language TEXT,size_bytes INT,content TEXT,indexed_at REAL,status TEXT,UNIQUE(project_id,path));CREATE TABLE github_code_chunks(id TEXT PRIMARY KEY,project_id TEXT,file_id TEXT,path TEXT,branch TEXT,commit_sha TEXT,language TEXT,symbol TEXT,line_start INT,line_end INT,text TEXT);CREATE VIRTUAL TABLE github_code_fts USING fts5(text,chunk_id UNINDEXED,project_id UNINDEXED,path UNINDEXED,line_start UNINDEXED,line_end UNINDEXED);CREATE TABLE github_conversations(id TEXT,project_id TEXT,branch TEXT,title TEXT,created REAL,updated REAL);CREATE TABLE github_messages(id INTEGER,conversation_id TEXT,role TEXT,content TEXT,sources TEXT,created REAL);INSERT INTO github_jobs VALUES('j',0);INSERT INTO github_projects VALUES('p','ready',0);")
 return con
def cand(path,sha):return {'path':path,'sha':sha,'size':30}
def f(sha,txt):return {'blob_sha':sha,'hash':hashlib.sha256(txt.encode()).hexdigest(),'content':txt,'size':len(txt),'language':'Python'}
def test_snapshot_updates_and_reuses_unchanged(monkeypatch,tmp_path):
 con=_fixture(monkeypatch,tmp_path);gh._snapshot('j','p','main','c1',[cand('a.py','a')],{'a.py':f('a','def old(): pass')},set());
 with con() as c:old=c.execute('select id from github_code_chunks').fetchone()[0]
 gh._snapshot('j','p','main','c2',[cand('a.py','a')],{}, {'a.py'})
 with con() as c:assert c.execute('select id from github_code_chunks').fetchone()[0]==old
 gh._snapshot('j','p','main','c3',[cand('b.py','b')],{'b.py':f('b','def new(): pass')},set())
 with con() as c:assert [r[0] for r in c.execute('select path from github_project_files')]==['b.py']
def test_cancelled_import_does_not_commit(monkeypatch,tmp_path):
 con=_fixture(monkeypatch,tmp_path)
 with con() as c:c.execute("UPDATE github_jobs SET cancel_requested=1 WHERE id='j'")
 with pytest.raises(gh.Cancelled):gh._snapshot('j','p','main','c1',[],{},set())
 with con() as c:assert c.execute('select count(*) from github_project_files').fetchone()[0]==0
def test_insufficient_evidence(monkeypatch,tmp_path):
 _fixture(monkeypatch,tmp_path);monkeypatch.setattr(gh,'_project',lambda p:{'id':p,'branch':'main','owner':'o','name':'r'});monkeypatch.setattr(gh,'retrieve',lambda *a:[])
 d=gh.chat('p','where is x?');assert 'not find enough relevant evidence' in d['answer'].lower() and not d['sources']
