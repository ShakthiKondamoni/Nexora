import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.getcwd(), 'data', 'studio.db'))

def find_ids():
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, type, status, error FROM sources")
        rows = cursor.fetchall()
        with open('ids_output.txt', 'w') as f:
            for row in rows:
                f.write(f"ID: {row['id']}, Title: {row['title']}, Type: {row['type']}, Status: {row['status']}\n")
        conn.close()
    except Exception as e:
        with open('ids_output.txt', 'w') as f:
            f.write(str(e))

if __name__ == "__main__":
    find_ids()
