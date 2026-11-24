"""Configuration, database safety, backup, schema and pure parsing regression tests."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from backend.services.document_service import chunk, nb_cells
from scripts.backup_database import backup

ROOT=Path(__file__).resolve().parents[2]

def run(code,db,cwd,extra=None):
    env=dict(os.environ,STUDIO_DB=str(db),STUDIO_FILES=str(db.parent/'uploads'))
    env.pop('STUDIO_INIT_DB',None)
    env['PYTHONPATH']=str(ROOT)+os.pathsep+os.environ.get('PYTHONPATH','')
    env.update(extra or {})
    return subprocess.run([sys.executable,'-c',code],cwd=cwd,env=env,text=True,capture_output=True,timeout=20)

def test_missing_database_is_not_silently_created(tmp_path):
    db=tmp_path/'missing.db'
    r=run('from backend.database.schema import initialize_database;initialize_database()',db,tmp_path)
    assert r.returncode!=0 and 'Refusing to create' in r.stderr and not db.exists()

def test_explicit_initialize_and_query_do_not_replace_missing_database(tmp_path):
    db=tmp_path/'new.db'
    r=run('from backend.database.schema import initialize_database;initialize_database(allow_create=True)',db,tmp_path)
    assert r.returncode==0,r.stderr
    db.unlink()
    r=run('from backend.database.connection import q;q("SELECT 1")',db,tmp_path)
    assert r.returncode!=0 and 'Database missing' in r.stderr and not db.exists()

def test_path_resolution_does_not_depend_on_cwd(tmp_path):
    r=run('import json;from backend.core.config import DB_PATH,FILES;print(json.dumps([str(DB_PATH),str(FILES)]))',Path('relative.db'),tmp_path,{'STUDIO_FILES':'relative-files'})
    assert r.returncode==0,r.stderr
    db,files=json.loads(r.stdout)
    assert Path(db)==ROOT/'relative.db' and Path(files)==ROOT/'relative-files'

def test_backup_preserves_content_and_refuses_overwrite(tmp_path):
    src=tmp_path/'source.db';dst=tmp_path/'backup.db'
    with sqlite3.connect(src) as c:c.execute('CREATE TABLE sample(value TEXT)');c.execute("INSERT INTO sample VALUES('preserved')")
    before=src.read_bytes();backup(src,dst)
    with sqlite3.connect(dst) as c:assert c.execute('SELECT value FROM sample').fetchone()[0]=='preserved'
    assert src.read_bytes()==before
    import pytest
    with pytest.raises(FileExistsError):backup(src,dst)
    with pytest.raises(FileExistsError):backup(src,src)
    with pytest.raises(FileNotFoundError):backup(tmp_path/'absent.db',tmp_path/'absent-backup.db')

def test_original_schema_upgrade_backs_up_and_preserves_rows(tmp_path):
    db=tmp_path/'older.db'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id TEXT,role TEXT,content TEXT,context TEXT,images TEXT,names TEXT,model TEXT,created REAL)')
        c.execute("INSERT INTO messages(chat_id,role,content) VALUES('legacy','user','keep me')")
    r=run('from backend.database.schema import initialize_database;initialize_database()',db,tmp_path)
    assert r.returncode==0,r.stderr
    backups=list(tmp_path.glob('older.db.backup-*'));assert len(backups)==1
    with sqlite3.connect(backups[0]) as c:assert 'sources' not in [r[1] for r in c.execute('PRAGMA table_info(messages)')]
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT content FROM messages').fetchone()[0]=='keep me'
        assert 'sources' in [r[1] for r in c.execute('PRAGMA table_info(messages)')]
    # Restore the backup to reverse the original compatibility initialization.
    r=run('from backend.database.schema import initialize_database;initialize_database()',db,tmp_path)
    assert r.returncode==0 and len(list(tmp_path.glob('older.db.backup-*')))==1

def test_relative_source_paths_are_database_relative(tmp_path):
    db=tmp_path/'data.db'
    r=run('from backend.core.config import source_path;print(source_path("files/abc.txt"))',db,tmp_path)
    assert r.returncode==0 and Path(r.stdout.strip())==tmp_path/'files'/'abc.txt'

def test_chunking_and_notebook_are_pure():
    assert chunk('   ')==[]
    assert all(x.strip() for x in chunk(('paragraph words '*300)+'\n\nEnd'))
    rows=nb_cells(json.dumps({'cells':[{'cell_type':'code','source':['print(123)'],'outputs':[{'output_type':'stream','text':['123\n']}]}]}))
    assert rows[0][0:2]==(1,'code') and 'print(123)' in rows[0][2] and '--- output ---' in rows[0][2]

def test_launcher_and_readme_match_entry_point():
    bat=(ROOT/'run_studio.bat').read_text();readme=(ROOT/'README.md').read_text()
    assert 'cd /d "%~dp0"' in bat and '-m backend.main' in bat
    assert 'http://127.0.0.1:8501' in bat and 'scripts/verify_installation.py' in readme
    assert 'taskkill' not in bat.lower() and 'ollama serve' not in bat.lower()
