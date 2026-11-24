"""Create a consistent SQLite backup without overwriting either source or destination.
Run after stopping Studio and ingestion; copy uploaded files separately.
"""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def backup(source: Path, destination: Path) -> Path:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(f'Source database does not exist: {source}')
    if source == destination or destination.exists():
        raise FileExistsError(f'Backup destination already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation also guards against a race with another backup process.
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                result = dst.execute('PRAGMA quick_check').fetchone()[0]
                if result != 'ok':
                    raise RuntimeError(f'Backup integrity check failed: {result}')
    except Exception:
        destination.unlink(missing_ok=True)  # only our newly reserved failed output
        raise
    return destination

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,help='Source SQLite DB (default: configured Studio DB)')
    parser.add_argument('--output',type=Path,required=True,help='NEW backup file; existing files are refused')
    args=parser.parse_args()
    if args.database is None:
        from backend.core.config import DB_PATH
        args.database=DB_PATH
    try:
        print('Backup created:',backup(args.database,args.output))
    except Exception as exc:
        print(f'Backup failed: {exc}',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
