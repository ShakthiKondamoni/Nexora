"""Never use a personal DB or a real Ollama endpoint in automated tests."""
import os
from pathlib import Path
import tempfile
import pytest
import requests

TEST_ROOT=Path(tempfile.mkdtemp(prefix='studio-tests-'))
os.environ['STUDIO_DB']=str(TEST_ROOT/'studio.db')
os.environ['STUDIO_FILES']=str(TEST_ROOT/'files')
os.environ['STUDIO_INIT_DB']='1'

@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    from backend.database.schema import initialize_database
    initialize_database()
    from backend.database.connection import q
    from backend.services.ollama_service import _caps
    # Every test sees defaults and no documents. Existing tests still use their
    # original TestClient/import hooks; all assertions are retained.
    for table in ['auth_sessions','auth_oauth_state','auth_reset_tokens','auth_rate_limits','auth_owner','github_messages','github_conversations','github_code_fts','github_code_chunks','github_project_files','github_jobs','github_projects','github_oauth_state','chunk_fts','chunks','fts','pages','sources','collections','messages','chats','projects','settings']:
        q('DELETE FROM '+table)
    _caps.clear()
    def unavailable(*args,**kwargs):
        raise requests.ConnectionError('Ollama intentionally unavailable in isolated tests')
    monkeypatch.setattr(requests,'get',unavailable)
    monkeypatch.setattr(requests,'post',unavailable)
