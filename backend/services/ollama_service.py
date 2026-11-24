"""Existing Ollama discovery, capability cache, and smoke generation."""
import requests
from fastapi.responses import JSONResponse
from backend.services.settings_service import ollama_url

_caps = {}

def caps(name):
    if name not in _caps:
        try: _caps[name] = requests.post(ollama_url() + "/api/show", json={"model": name}, timeout=10).json().get("capabilities", [])
        except Exception: return []
    return _caps[name]

def models():
    try:
        t = requests.get(ollama_url() + "/api/tags", timeout=4).json().get("models", [])
        run = {m["name"]: m for m in requests.get(ollama_url() + "/api/ps", timeout=4).json().get("models", [])}
    except Exception:
        return JSONResponse({"error":"Ollama is unavailable. Check that it is running and the configured address is correct."},status_code=503)
    return {"models": [{"name": m["name"], "size": m["size"], "caps": caps(m["name"]),
            "params": m.get("details", {}).get("parameter_size"), "running": m["name"] in run,
            "vram": run.get(m["name"], {}).get("size_vram"), "ctx": run.get(m["name"], {}).get("context_length")} for m in t]}

def test(body: dict):
    try:
        r = requests.post(ollama_url() + "/api/chat", json={"model": body["model"], "stream": False, "options": {"num_ctx": 1024, "num_predict": 32},
            "messages": [{"role": "user", "content": "Reply exactly: Model is working."}]}, timeout=300)
        if r.status_code != 200: return JSONResponse({"error": f"HTTP {r.status_code}: {r.text[:300]}"}, 502)
        return {"reply": r.json()["message"]["content"]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, 502)
