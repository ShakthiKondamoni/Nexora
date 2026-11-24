"""Installation checks. Only --initialize authorizes a new empty database.
Exit 3: missing DB (fresh install may initialize); all other nonzero codes are errors.
"""
import argparse
import importlib
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize',action='store_true',help='Explicitly allow creation of a NEW empty database')
    args=parser.parse_args()
    if sys.version_info<(3,11):
        print('Python 3.11 or later is required.',file=sys.stderr);return 1
    failed=[]
    for name in ['fastapi','uvicorn','multipart','requests','psutil','fitz','pytest','httpx']:
        try: importlib.import_module(name)
        except ImportError as exc: failed.append(f'{name}: {exc}')
    if failed:
        print('Missing dependencies: '+'; '.join(failed),file=sys.stderr);return 1
    required=['backend/main.py','requirements.txt','constraints.txt','frontend/index.html','frontend/assets/css/studio.css']
    required += ['frontend/assets/js/'+name+'.js' for name in ['core','sidebar','chat','monitoring','knowledge','settings','bootstrap']]
    missing=[name for name in required if not (ROOT/name).is_file()]
    if missing:
        print('Missing project files: '+', '.join(missing),file=sys.stderr);return 1
    try:
        with sqlite3.connect(':memory:') as memory:
            memory.execute('CREATE VIRTUAL TABLE test_fts USING fts5(text)')
        from backend.core.config import DB_PATH, FILES, source_path
        if not DB_PATH.exists() and not args.initialize:
            print(f'Database missing: {DB_PATH}',file=sys.stderr)
            print('Existing user: set STUDIO_DB to your original DB. NEW installation only: rerun with --initialize.',file=sys.stderr)
            return 3
        from backend.database.schema import initialize_database
        initialize_database(allow_create=args.initialize)
        if args.initialize:
            marker=ROOT/'data'/'.initialized';marker.parent.mkdir(parents=True,exist_ok=True)
            marker.write_text('Database initialized explicitly. Do not silently replace missing databases.\n',encoding='utf-8')
        from backend.database.connection import q
        missing_files=sum(not source_path(row['path']).is_file() for row in q('SELECT DISTINCT path FROM sources'))
        if missing_files:
            print(f'{missing_files} uploaded source files are missing. Restore them before startup; do not reindex or delete their metadata.',file=sys.stderr)
            return 1
        from backend.main import app
        print(f'Checks passed: {len(app.routes)} registered routes/mounts; SQLite FTS5 available.')
        print('Database:',DB_PATH)
        print('Uploads:',FILES)
        print('URL: http://127.0.0.1:8501; Ollama connectivity is not required for these checks.')
    except Exception as exc:
        print(f'Configuration check failed: {exc}',file=sys.stderr);return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
