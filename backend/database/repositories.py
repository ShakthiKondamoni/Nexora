"""Chat/project SQL operations and the shared query interface."""
import uuid, time
from backend.database.connection import q

def chats():
    return {"chats": q("SELECT id,title,pinned,archived,project_id,updated FROM chats ORDER BY updated DESC"),
            "projects": q("SELECT * FROM projects")}

def new_chat():
    i = uuid.uuid4().hex[:10]
    q("INSERT INTO chats VALUES(?,?,0,0,NULL,?)", i, "New chat", time.time()); return {"id": i}

def patch(i: str, body: dict):
    for k in ("title", "pinned", "archived", "project_id"):
        if k in body: q(f"UPDATE chats SET {k}=? WHERE id=?", body[k], i)
    return {"ok": True}

def delete(i: str):
    q("DELETE FROM messages WHERE chat_id=?", i); q("DELETE FROM chats WHERE id=?", i); return {"ok": True}

def messages(i: str):
    return q("SELECT id,role,content,names,model,sources FROM messages WHERE chat_id=? ORDER BY id", i)

def drop_last(i: str):
    r = q("SELECT id,role FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT 1", i, one=True)
    if r and r["role"] == "assistant": q("DELETE FROM messages WHERE id=?", r["id"])
    return {"ok": True}

def mk_project(body: dict):
    i = uuid.uuid4().hex[:8]; q("INSERT INTO projects VALUES(?,?)", i, body["name"]); return {"id": i}
