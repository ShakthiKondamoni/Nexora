"""Run: py -m pip install pytest httpx && py -m pytest -q   (no Ollama needed; Ollama calls are mocked/expected to fail)"""
import os, time, tempfile, json
tmp = os.path.dirname(os.environ["STUDIO_DB"])  # isolated by tests/conftest.py
import fitz
from fastapi.testclient import TestClient
import server, knowledge
c = TestClient(server.app)
TXT = "Photosynthesis converts light energy into chemical energy inside plant chloroplasts."

def wait(sid):
    for _ in range(200):
        s = c.get(f"/api/kb/sources/{sid}").json()
        if s["status"] not in ("queued", "processing", "ocr"): return s
        time.sleep(.1)
    raise AssertionError("timeout")
def pdf(pages):
    d = fitz.open()
    for t in pages:
        p = d.new_page()
        if t: p.insert_text((72, 72), t)
    return d.tobytes()
def coll(n="Test"): return c.post("/api/kb/collections", json={"name": n}).json()["id"]
def up(co, name, data, ocr=""): return c.post("/api/kb/sources", data={"coll": co, "ocr_model": ocr}, files=[("files", (name, data))]).json()[0]

def test_collection_persistence_rename_delete():
    i = coll("Geo"); c.patch(f"/api/kb/collections/{i}", json={"name": "Geography"})
    assert any(x["name"] == "Geography" for x in c.get("/api/kb/collections").json())
    c.delete(f"/api/kb/collections/{i}"); assert not any(x["id"] == i for x in c.get("/api/kb/collections").json())

def test_pdf_text_extraction_and_page_citation():
    co = coll(); r = up(co, "bio.pdf", pdf(["Intro page about nothing in particular, filler text here.", TXT]))
    s = wait(r["id"]); assert s["status"] == "ready" and len(s["pages"]) == 2
    hits = knowledge.retrieve("how does photosynthesis work", [{"t": "src", "id": r["id"]}])
    assert hits[0]["loc"] == 2 and hits[0]["label"] == "p."
    assert knowledge.retrieve("explain page 1", [{"t": "src", "id": r["id"]}])[0]["loc"] == 1

def test_scanned_page_failure_visible_retry_and_export(monkeypatch):
    co = coll(); r = up(co, "scan.pdf", pdf([TXT, None]), ocr="glm-ocr"); s = wait(r["id"])
    assert s["status"] == "partial" and s["pages"][1]["status"] == "failed" and s["pages"][1]["error"]
    assert "FAILED" in c.get(f"/api/kb/sources/{r['id']}/export").text  # never silently omitted
    class R:  # mock Ollama OCR success
        status_code = 200
        def json(self): return {"message": {"content": "Scanned text about mitochondria and energy"}}
    monkeypatch.setattr(knowledge.requests, "post", lambda *a, **k: R()); monkeypatch.setattr(knowledge, "CAPS", lambda m: ["vision"])
    c.post(f"/api/kb/sources/{r['id']}/pages/2/retry", json={}); s = wait(r["id"])
    assert s["status"] == "ready"; assert knowledge.retrieve("mitochondria", [{"t": "src", "id": r["id"]}])[0]["loc"] == 2

def test_notebook_parsed_not_executed():
    flag = tmp + "/pwned"
    nb = {"cells": [{"cell_type": "markdown", "source": ["# Title\n", "Intro to CNN models"]},
                    {"cell_type": "code", "source": f"open(r'{flag}','w').write('x')", "outputs": [{"output_type": "stream", "text": ["accuracy 0.93\n"]}]}]}
    co = coll(); r = up(co, "n.ipynb", json.dumps(nb).encode()); s = wait(r["id"])
    assert s["status"] == "ready" and not os.path.exists(flag)
    h = knowledge.retrieve("accuracy", [{"t": "src", "id": r["id"]}])[0]; assert h["label"] == "cell" and h["loc"] == 2

def test_duplicate_detection_and_shared_file_survives():
    a, b = coll("A"), coll("B"); d = TXT.encode()
    r1 = up(a, "x.txt", d); wait(r1["id"]); assert "Duplicate" in up(a, "x2.txt", d)["error"]
    r2 = up(b, "x.txt", d); wait(r2["id"]); p = c.get(f"/api/kb/sources?coll={a}").json()
    path = knowledge.Q("SELECT path FROM sources WHERE id=?", r1["id"], one=True)["path"]
    c.delete(f"/api/kb/collections/{a}"); assert os.path.exists(path)
    c.delete(f"/api/kb/collections/{b}"); assert not os.path.exists(path)

def test_reindex_and_source_delete():
    co = coll(); r = up(co, "n.md", b"# Notes\n\nQuantum entanglement is a correlation of states."); wait(r["id"])
    c.post(f"/api/kb/sources/{r['id']}/reindex", json={}); assert wait(r["id"])["status"] == "ready"
    assert c.get("/api/kb/search?q=entanglement").json()
    c.delete(f"/api/kb/sources/{r['id']}"); assert not c.get("/api/kb/search?q=entanglement").json()

def test_unsupported_type_and_isolation():
    co = coll(); assert "Unsupported" in up(co, "a.docx", b"x")["error"]
    r1 = up(co, "a.txt", b"Volcanoes erupt magma and ash clouds regularly."); r2 = up(co, "b.txt", b"Glaciers move slowly across mountain valleys.")
    wait(r1["id"]); wait(r2["id"])
    assert all(h["sid"] == r1["id"] for h in knowledge.retrieve("glaciers volcanoes", [{"t": "src", "id": r1["id"]}]))

def test_chat_with_sources_header_and_ollama_down():
    co = coll(); r = up(co, "bio.txt", TXT.encode()); wait(r["id"]); cid = c.post("/api/chats").json()["id"]
    resp = c.post(f"/api/chats/{cid}/send", data={"text": "what is photosynthesis", "model": "x", "kb": json.dumps([{"t": "src", "id": r["id"]}])})
    assert "X-Sources" in resp.headers and "\x00ERR:" in resp.text   # citation present, Ollama failure reported clearly
    assert c.get("/api/models").status_code == 503
    assert c.post(f"/api/chats/{cid}/send", data={"text": "hi", "model": "x"}, files=[("files", ("a.png", b"x"))]).status_code == 400


# ---------- Stage 1: server-side settings ----------
def test_settings_defaults_persist_and_validate():
    s = c.get("/api/settings").json()
    assert s["ctx"] == 4096 and s["chat_model"] == ""
    r = c.put("/api/settings", json={"chat_model": "qwen2.5:latest", "ctx": 8192, "ocr_model": "glm-ocr:latest", "poll_ms": 5000})
    assert r.status_code == 200 and r.json()["ctx"] == 8192
    assert c.get("/api/settings").json()["chat_model"] == "qwen2.5:latest"   # read back from SQLite
    assert c.put("/api/settings", json={"ctx": 12345}).status_code == 422      # invalid context rejected
    assert c.put("/api/settings", json={"ollama_url": "ftp://x"}).status_code == 422
    assert c.put("/api/settings", json={"nope": 1}).status_code == 422
    assert c.get("/api/settings").json()["ctx"] == 8192                        # bad write changed nothing

def test_theme_mode_persists_without_overwriting_other_settings():
    c.put("/api/settings", json={"chat_model": "keep-this-model"})
    r = c.put("/api/settings", json={"theme_mode": "light"})
    assert r.status_code == 200 and r.json()["theme_mode"] == "light"
    assert c.get("/api/settings").json()["chat_model"] == "keep-this-model"
    assert c.put("/api/settings", json={"theme_mode": "sepia"}).status_code == 422
    assert c.put("/api/settings", json={"theme_mode": "system"}).json()["theme_mode"] == "system"

def test_malformed_stored_setting_does_not_break_startup():
    server.q("INSERT INTO settings(key,value) VALUES('ctx','not-json') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
    assert c.get("/api/settings").json()["ctx"] == 4096                        # falls back to default

def test_chat_uses_server_default_model_and_requires_one():
    c.put("/api/settings", json={"chat_model": ""}); cid = c.post("/api/chats").json()["id"]
    assert c.post(f"/api/chats/{cid}/send", data={"text": "hi"}).status_code == 400
    c.put("/api/settings", json={"chat_model": "m1"})
    resp = c.post(f"/api/chats/{cid}/send", data={"text": "hi"})
    assert resp.status_code == 200 and "\x00ERR:" in resp.text                 # model resolved from settings; Ollama down reported
    assert server.q("SELECT model FROM messages WHERE chat_id=? AND role='user'", cid, one=True)["model"] == "m1"

def test_connection_test_reports_unreachable():
    r = c.post("/api/settings/test-connection", json={"ollama_url": "http://127.0.0.1:9"})
    assert r.status_code == 503 and r.json()["ok"] is False

def test_task2_formats_search_and_text_details():
    from pathlib import Path
    from io import BytesIO
    from docx import Document
    co=coll('Task2 formats'); doc=Document();doc.add_paragraph('Photosynthesis converts sunlight into chemical energy in chloroplasts.');buf=BytesIO();doc.save(buf)
    files=[('files',('notes.md',b'# Photosynthesis\nChloroplasts contain chlorophyll.','text/markdown')),('files',('facts.csv',b'topic,detail\nphotosynthesis,light stored in sugars','text/csv')),('files',('facts.json',b'{"topic":"photosynthesis","site":"chloroplasts"}','application/json')),('files',('source.py',b'def photosynthesis():\n return "chloroplasts"\n','text/x-python')),('files',('guide.docx',buf.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))]
    response=c.post('/api/kb/sources',data={'coll':co},files=files);assert response.status_code==200
    records=response.json();assert len(records)==5 and all(x.get('id') for x in records)
    for item in records:
        result=wait(item['id']);assert result['status']=='ready',result;assert result['size_bytes']>0 and result['extension']
        detail=c.get(f"/api/kb/sources/{item['id']}/text").json();assert detail['pages'][0]['text']
    hits=c.get('/api/kb/search',params={'q':'photosynthesis chloroplasts','coll':co}).json();assert hits

def test_task2_grounded_answers_and_insufficient_evidence(monkeypatch):
    co=coll('Task2 Q&A');doc=up(co,'plants.txt',b'Chloroplasts convert light energy into chemical energy during photosynthesis.');assert wait(doc['id'])['status']=='ready'
    miss=c.post(f'/api/kb/collections/{co}/ask',json={'question':'What is the capital of Mars?','model':'local-test'}).json();assert miss['status']=='insufficient_evidence' and not miss['citations']
    class Fake:
        status_code=200;text=''
        def json(self):return {'message':{'content':'Chloroplasts convert light into stored chemical energy [S1].'}}
    monkeypatch.setattr(knowledge.requests,'post',lambda *a,**k:Fake())
    result=c.post(f'/api/kb/collections/{co}/ask',json={'question':'What happens in chloroplasts?','model':'local-test'}).json()
    assert '[S1]' in result['answer'] and result['citations'][0]['filename']=='plants.txt';assert result['passages'][0]['reference']=='Section 1'

def test_task2_safe_names_duplicates_and_shared_file_deletion():
    from pathlib import Path
    from backend.core.config import FILES
    from backend.database.connection import q
    data=b'Path traversal must remain inside the configured folder.';a=coll('safe A');b=coll('safe B')
    first=up(a,'../../escape.txt',data);assert wait(first['id'])['status']=='ready';row=q('SELECT path,title FROM sources WHERE id=?',first['id'],one=True)
    assert row['title']=='escape.txt' and Path(row['path']).resolve().parent==FILES.resolve()
    duplicate=up(a,'escape.txt',data);assert 'Duplicate' in duplicate.get('error','')
    second=up(b,'shared.txt',data);assert wait(second['id'])['status']=='ready';shared=q('SELECT path FROM sources WHERE id=?',second['id'],one=True)['path'];assert shared==row['path']
    c.delete(f"/api/kb/sources/{first['id']}");assert Path(shared).is_file();c.delete(f"/api/kb/sources/{second['id']}");assert not Path(shared).exists()

def test_task2_image_without_vision_model_is_visible(monkeypatch):
    co=coll('No OCR model');monkeypatch.setattr(knowledge,'CAPS',lambda model:[])
    item=up(co,'scan.png',b'\x89PNG\r\n\x1a\nsynthetic image');result=wait(item['id']);assert result['status']=='failed';assert 'vision-capable' in result['error'] or 'installed local vision' in result['error']

