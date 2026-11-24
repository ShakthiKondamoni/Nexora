"""SQLite connection/query boundary, shared by chat, settings and Knowledge."""
import sqlite3
from backend.core.config import DB_PATH

def connect():
    # Normal queries must never create an empty replacement for a missing database.
    if not DB_PATH.is_file():
        raise RuntimeError(f'Database missing: {DB_PATH}. Run verify_installation.py --initialize for a NEW installation only.')
    c = sqlite3.connect(DB_PATH.as_uri() + '?mode=rw', uri=True)
    c.row_factory = sqlite3.Row
    return c

def q(sql: str, *args, one: bool = False):
    c = connect()
    try:
        with c:
            r = c.execute(sql, args)
            rows = [dict(x) for x in r.fetchall()] if r.description else []
    finally:
        c.close()
    return (rows[0] if rows else None) if one else rows

def many(sql: str, rows):
    c = connect()
    try:
        with c:
            c.executemany(sql, rows)
    finally:
        c.close()
