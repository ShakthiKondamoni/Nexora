"""Secret-safe, read-only runtime diagnostics."""
from datetime import datetime,timezone
from pathlib import Path
import sqlite3,requests
from backend.core.config import DB_PATH
from backend.services import settings_service,web_research_service,github_service

def _item(key,label,state,message):return {"id":key,"name":label,"state":state,"message":message}
def _database_status():
 path=Path(DB_PATH)
 if not path.is_file():return _item("database","Database","Unavailable","The configured database file is missing. Check its location; do not recreate it as a shortcut.")
 try:
  with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=1) as db:db.execute("SELECT 1").fetchone()
  return _item("database","Database","Ready","SQLite opened successfully in read-only mode.")
 except Exception:return _item("database","Database","Unavailable","SQLite could not open the configured database. Check its location and back it up before repair.")
def _ollama_status(cfg):
 url=str(cfg.get("ollama_url") or "").rstrip("/")
 if not url:return _item("ollama","Ollama","Not configured","Set the Ollama address in Settings, then retry."),[]
 try:
  r=requests.get(url+"/api/tags",timeout=3);r.raise_for_status();data=r.json()
  names=[str(m.get("name")) for m in data.get("models",[]) if isinstance(m,dict) and m.get("name")]
  return _item("ollama","Ollama","Ready","Ollama responded to model discovery."),names
 except Exception:return _item("ollama","Ollama","Unavailable","Could not reach Ollama. Start it, verify its configured address, and retry."),[]
def _model_status(selected,ollama,names):
 if not selected:return _item("model","Selected model","Needs attention","Choose a default chat model in Settings.")
 if ollama["state"]!="Ready":return _item("model","Selected model","Unavailable","Model availability cannot be checked until Ollama responds.")
 if selected in names:return _item("model","Selected model","Ready","The selected model is available in Ollama.")
 return _item("model","Selected model","Needs attention","The selected model was not found. Choose an installed model; Nexora will not download weights automatically.")
def _web_status():
 probe=getattr(web_research_service,"test_provider",None)
 if not callable(probe):return _item("web","Web search provider","Needs attention","This build has no provider health probe. Verify the configured provider in Settings.")
 try:
  result=probe(timeout=4);ok=result is True or (isinstance(result,dict) and bool(result.get("ok")))
  if ok:return _item("web","Web search provider","Ready","The configured provider answered a connectivity check.")
  return _item("web","Web search provider","Needs attention","The provider did not confirm readiness. Check its Settings configuration.")
 except Exception:return _item("web","Web search provider","Unavailable","Could not reach the configured provider. Check its instance address and retry.")
def _github_status():
 try:state=github_service.status()
 except Exception:return _item("github","GitHub","Unavailable","Secure GitHub status could not be read. Check the system credential store.")
 if state.get("storage_error"):return _item("github","GitHub","Needs attention","The secure credential store is unavailable. Fix it before reconnecting.")
 if not state.get("configured"):return _item("github","GitHub","Not configured","Configure the GitHub App in Account & Integrations to enable repositories.")
 if not state.get("connected"):return _item("github","GitHub","Needs attention","The GitHub App is configured but no account is connected.")
 return _item("github","GitHub","Needs attention","A credential is present, but repository access was not live-verified here. Verify from GitHub Projects.")
def collect():
 try:cfg=settings_service.get_settings()
 except Exception:cfg={}
 db=_database_status();ollama,names=_ollama_status(cfg);model=_model_status(cfg.get("chat_model"),ollama,names)
 return {"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"components":[_item("backend","Nexora backend","Ready","The local API is responding."),ollama,model,_web_status(),_github_status(),db]}
