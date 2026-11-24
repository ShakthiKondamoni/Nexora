"""Regression coverage for moved routes, assets, attachments, streams and persistence."""
import base64
import json
from pathlib import Path
import time
import requests
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import DB_PATH, FILES, FRONTEND
from backend.database.connection import q
from backend.services import knowledge_service as knowledge
from backend.services import file_service, monitoring_service

client=TestClient(app)

class Reply:
    def __init__(self,data=None,lines=(),status=200):
        self.data=data or {};self.lines=lines;self.status_code=status;self.text='simulated response'
    def json(self):return self.data
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError(str(self.status_code))
    def __enter__(self):return self
    def __exit__(self,*exc):return False
    def iter_lines(self):return iter(self.lines)

def chat():return client.post('/api/chats').json()['id']
def collect():return client.post('/api/kb/collections',json={'name':'Regression'}).json()['id']
def upload(co,name,data):
    r=client.post('/api/kb/sources',data={'coll':co},files={'files':(name,data)})
    assert r.status_code==200
    sid=r.json()[0]['id']
    for _ in range(200):
        s=client.get('/api/kb/sources/'+sid).json()
        if s['status'] not in ['queued','processing','ocr']:return sid,s
        time.sleep(.02)
    raise AssertionError('Ingestion did not finish')

def test_all_original_http_contracts_registered_once():
    contract=json.loads((Path(__file__).parents[1]/'route_contract.json').read_text())
    current=[(m,r.path) for r in app.routes for m in getattr(r,'methods',[]) if m!='HEAD']
    for r in contract:
        assert current.count((r['method'],r['path']))==1
    assert len(contract)==31

def test_frontend_assets_and_mime_types():
    root=client.get('/');assert root.status_code==200
    assert '<style>' not in root.text and '<script>' not in root.text
    for p in (FRONTEND/'assets').rglob('*'):
        if not p.is_file():continue
        response=client.get('/assets/'+str(p.relative_to(FRONTEND/'assets')).replace('\\','/'))
        assert response.status_code==200 and response.content==p.read_bytes()
        assert ('css' if p.suffix=='.css' else 'javascript') in response.headers['content-type']

def test_compatibility_imports_are_aliases_not_copies():
    import server
    import knowledge as legacy
    assert server.app is app and server.q is q and legacy is knowledge

def test_chat_project_pin_archive_rename_delete_and_last():
    cid=chat();pid=client.post('/api/projects',json={'name':'Work'}).json()['id']
    assert client.patch('/api/chats/'+cid,json={'title':'Renamed','pinned':1,'archived':1,'project_id':pid}).status_code==200
    c=client.get('/api/chats').json()['chats'][0]
    assert (c['title'],c['pinned'],c['archived'],c['project_id'])==('Renamed',1,1,pid)
    q("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)",cid,'user','question')
    q("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)",cid,'assistant','answer')
    client.delete('/api/chats/'+cid+'/last')
    assert [r['role'] for r in client.get('/api/chats/'+cid+'/messages').json()]==['user']
    client.delete('/api/chats/'+cid)
    assert not q('SELECT * FROM messages WHERE chat_id=?',cid) and not client.get('/api/chats').json()['chats']

def test_stream_payload_persistence_and_regeneration(monkeypatch):
    seen=[]
    def post(url,**kw):
        seen.append((url,kw))
        return Reply(lines=[json.dumps({'message':{'content':t}}).encode() for t in ['Hello',' world']])
    monkeypatch.setattr(requests,'post',post)
    client.put('/api/settings',json={'chat_model':'model:tag','ctx':8192})
    cid=chat();r=client.post('/api/chats/'+cid+'/send',data={'text':'Hi','system':'Be concise'})
    assert r.text=='Hello world'
    payload=seen[-1][1]['json']
    assert payload['model']=='model:tag' and payload['options']['num_ctx']==8192 and payload['stream'] is True
    assert payload['messages'][0]=={'role':'system','content':'Be concise'}
    assert [x['content'] for x in client.get('/api/chats/'+cid+'/messages').json()]==['Hi','Hello world']
    client.delete('/api/chats/'+cid+'/last')
    assert client.post('/api/chats/'+cid+'/send',data={'regenerate':'true'}).text=='Hello world'
    assert len(client.get('/api/chats/'+cid+'/messages').json())==2

def test_partial_stream_error_marker_and_saved_partial(monkeypatch):
    monkeypatch.setattr(requests,'post',lambda *a,**k:Reply(lines=[b'{"message":{"content":"partial"}}',b'{"error":"out of memory"}']))
    cid=chat();r=client.post('/api/chats/'+cid+'/send',data={'model':'x','text':'test'})
    assert r.text=='partial\x00ERR:out of memory'
    assert client.get('/api/chats/'+cid+'/messages').json()[-1]['content']=='partial'

def test_attachment_context_and_image_are_persisted(monkeypatch):
    monkeypatch.setattr(file_service,'caps',lambda m:['vision'])
    seen=[]
    def post(*a,**kw):seen.append(kw['json']);return Reply(lines=[b'{"message":{"content":"ok"}}'])
    monkeypatch.setattr(requests,'post',post)
    cid=chat();r=client.post('/api/chats/'+cid+'/send',data={'model':'vision','text':'Read'},files=[('files',('n.txt',b'important attached context')),('files',('i.png',b'image-bytes'))])
    assert r.text=='ok'
    message=seen[-1]['messages'][-1]
    assert 'important attached context' in message['content'] and message['images']==[base64.b64encode(b'image-bytes').decode()]
    row=q("SELECT * FROM messages WHERE chat_id=? AND role='user'",cid,one=True)
    assert json.loads(row['names'])==['n.txt','i.png'] and 'attached context' in row['context']

def test_failed_attachment_does_not_write_message(monkeypatch):
    cid=chat()
    r=client.post('/api/chats/'+cid+'/send',data={'model':'x','text':'read'},files={'files':('x.docx',b'x')})
    assert r.status_code==415 and not q('SELECT * FROM messages')
    monkeypatch.setattr(file_service,'MAX_MB',0)
    r=client.post('/api/chats/'+cid+'/send',data={'model':'x','text':'read'},files={'files':('x.txt',b'x')})
    assert r.status_code==413 and not q('SELECT * FROM messages')

def test_grounded_stream_source_header_and_persistence(monkeypatch):
    sid,s=upload(collect(),'plant.txt',b'Chloroplasts convert sunlight into chemical energy by photosynthesis.')
    assert s['status']=='ready'
    seen=[]
    def post(*a,**kw):seen.append(kw['json']);return Reply(lines=[b'{"message":{"content":"Plants [S1]"}}'])
    monkeypatch.setattr(requests,'post',post)
    cid=chat();r=client.post('/api/chats/'+cid+'/send',data={'model':'x','text':'Explain photosynthesis','kb':json.dumps([{'t':'src','id':sid}])})
    srcs=json.loads(base64.b64decode(r.headers['X-Sources']))
    assert srcs[0]['sid']==sid and srcs[0]['loc']==1
    assert seen[-1]['messages'][0]['content'].startswith('Answer ONLY')
    assert 'SOURCES:' in seen[-1]['messages'][-1]['content']
    assert json.loads(client.get('/api/chats/'+cid+'/messages').json()[-1]['sources'])==srcs

def test_pdf_preview_and_export_assets():
    import fitz
    with fitz.open() as d:
        p=d.new_page();p.insert_text((72,72),'A sufficiently long selectable PDF sentence for preview regression.')
        sid,s=upload(collect(),'preview.pdf',d.tobytes())
    assert s['status']=='ready'
    response=client.get('/api/kb/sources/'+sid+'/pages/1/image')
    assert response.status_code==200 and response.content.startswith(b'\x89PNG')
    assert '## p. 1' in client.get('/api/kb/sources/'+sid+'/export?fmt=md').text

def test_live_settings_url_used_by_existing_ocr(monkeypatch,tmp_path):
    import fitz
    from backend.services.settings_service import write_settings
    path=tmp_path/'scan.pdf'
    with fitz.open() as d:d.new_page();d.save(path)
    write_settings({'ollama_url':'http://127.0.0.1:11435','ocr_model':'ocr'})
    monkeypatch.setattr(knowledge,'CAPS',lambda m:['vision'])
    seen=[]
    def post(url,**kwargs):seen.append(url);return Reply({'message':{'content':'recognized text'}})
    monkeypatch.setattr(requests,'post',post)
    assert knowledge.ocr_page({'path':str(path),'ocr_model':''},1)=='recognized text'
    assert seen==['http://127.0.0.1:11435/api/chat']

def test_monitoring_fallback_and_process_contract(monkeypatch):
    monkeypatch.setattr(monitoring_service.shutil,'which',lambda p:None)
    r=client.get('/api/metrics')
    assert r.status_code==200
    m=r.json();assert m['gpu'] is None and 'nvidia-smi' in m['gpu_err'] and m['ollama']=={'up':False,'running':[]}
    assert 0<=m['ram']['pct']<=100 and m['disk']['total']>0
    processes=client.get('/api/processes');assert processes.status_code==200
    assert all({'pid','name','cpu','mem','status','ai'}<=p.keys() for p in processes.json())

def test_model_discovery_and_connection_contract(monkeypatch):
    def get(url,**kw):
        if url.endswith('/api/tags'):return Reply({'models':[{'name':'m:tag','size':123,'details':{'parameter_size':'3B'}}]})
        return Reply({'models':[{'name':'m:tag','size_vram':64,'context_length':4096}]})
    monkeypatch.setattr(requests,'get',get)
    monkeypatch.setattr(requests,'post',lambda *a,**kw:Reply({'capabilities':['vision'],'message':{'content':'Model is working.'}}))
    m=client.get('/api/models').json()['models'][0]
    assert m['name']=='m:tag' and m['running'] and m['caps']==['vision'] and m['vram']==64
    assert client.post('/api/test',json={'model':'m:tag'}).json()['reply']=='Model is working.'
    assert client.post('/api/settings/test-connection',json={}).json()['models']==1

def test_database_and_uploads_use_isolated_configured_paths():
    assert DB_PATH.is_file() and FILES.is_dir() and 'studio-tests-' in str(DB_PATH)
    assert DB_PATH.parent==FILES.parent

def test_invalid_settings_write_is_atomic():
    r=client.put('/api/settings',json={'chat_model':'would-change','ctx':True})
    assert r.status_code==422 and client.get('/api/settings').json()['chat_model']==''
