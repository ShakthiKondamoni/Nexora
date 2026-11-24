"""One source of truth for paths and the existing environment configuration.
Relative environment paths are project-root relative, never working-directory relative.
The .env.example is documentation; no dotenv parser or new dependency is introduced.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / 'frontend'
OLLAMA = os.environ.get('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
CHAT_MAX_MB = 50
KNOWLEDGE_MAX_MB = 100
TEXT_EXT = {'.txt','.md','.csv','.json','.py','.js','.ts','.tsx','.html','.css','.log','.yaml','.yml','.sql','.java','.c','.cpp','.cs','.go','.rs','.xml','.ini','.bat','.sh'}
IMG_EXT = {'.png','.jpg','.jpeg','.webp'}
CTX_CHOICES = [1024, 2048, 4096, 8192, 16384, 32768]
DEFAULTS = {'chat_model':'', 'ctx':4096, 'ocr_model':'', 'ollama_url':OLLAMA, 'poll_ms':2000, 'theme_mode':'dark', 'web_provider':'searxng', 'web_instance_url':'', 'web_result_count':5, 'web_timeout':12, 'web_mode_default':'off'}

def configured_path(value: str) -> Path:
    p = Path(value).expanduser()
    return (p if p.is_absolute() else PROJECT_ROOT / p).resolve()

def database_path() -> Path:
    explicit = os.environ.get('STUDIO_DB')
    if explicit:
        return configured_path(explicit)
    legacy, current = PROJECT_ROOT/'studio.db', PROJECT_ROOT/'data'/'studio.db'
    if legacy.exists() and current.exists():
        raise RuntimeError('Both studio.db and data/studio.db exist. Set STUDIO_DB explicitly; no database was selected.')
    return legacy if legacy.exists() else current

DB_PATH = database_path()
FILES = configured_path(os.environ.get('STUDIO_FILES', str(PROJECT_ROOT/'files')))

def source_path(stored: str) -> Path:
    """Do not rewrite stored references. Legacy relative paths use the DB directory."""
    p = Path(stored)
    return p if p.is_absolute() else DB_PATH.parent / p
