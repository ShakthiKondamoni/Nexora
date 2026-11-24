"""Compatibility entry point only. Implementation moved into backend/."""
from backend.main import app, run
from backend.database.connection import q

if __name__ == '__main__':
    run()
