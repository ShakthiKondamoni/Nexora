"""Original persisted settings validation and connection testing."""
import json
import requests
from urllib.parse import urlsplit
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from backend.database.connection import q
from backend.core.config import CTX_CHOICES, DEFAULTS

def _valid(k, v):
    if k == "ctx": return isinstance(v, int) and not isinstance(v, bool) and v in CTX_CHOICES
    if k == "poll_ms": return isinstance(v, int) and not isinstance(v, bool) and v in (1000, 2000, 5000)
    if k == "theme_mode": return isinstance(v, str) and v in ("system", "light", "dark")
    if k == "ollama_url": return isinstance(v, str) and v.startswith(("http://", "https://")) and len(v) < 200
    if k in ("chat_model", "ocr_model"): return isinstance(v, str) and len(v) < 200
    if k == "web_mode_default": return isinstance(v, str) and v in ("off", "search_first", "automatic")
    if k == "web_provider": return v == "searxng"
    if k == "web_instance_url":
        if not isinstance(v,str) or len(v)>500: return False
        if not v.strip(): return True
        try:
            u=urlsplit(v.strip()); return u.scheme in ("http","https") and bool(u.hostname) and not u.username and not u.password and not u.fragment
        except Exception: return False
    if k == "web_result_count": return isinstance(v,int) and not isinstance(v,bool) and 1<=v<=8
    if k == "web_timeout": return isinstance(v,int) and not isinstance(v,bool) and 3<=v<=30
    return False

def get_settings():
    cfg = dict(DEFAULTS)
    for r in q("SELECT key,value FROM settings"):
        try: v = json.loads(r["value"])
        except Exception: continue          # malformed stored value never blocks startup
        if r["key"] in DEFAULTS and _valid(r["key"], v): cfg[r["key"]] = v
    return cfg

def ollama_url(): return get_settings()["ollama_url"].rstrip("/")

def read_settings(): return get_settings()

def write_settings(body: dict):
    bad = [k for k, v in body.items() if k not in DEFAULTS or not _valid(k, v)]
    if bad: raise HTTPException(422, "Invalid setting(s): " + ", ".join(bad))
    for k, v in body.items():
        q("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", k, json.dumps(v))
    return get_settings()

def test_connection(body: dict = {}):
    url = str((body or {}).get("url") or ollama_url()).rstrip("/")
    try:
        r = requests.get(url + "/api/tags", timeout=4)
        r.raise_for_status()
        return {"ok": True, "models": len(r.json().get("models", []))}
    except Exception:
        return {"ok": False, "error": "Could not reach Ollama. Verify it is running and the configured address is correct."}
