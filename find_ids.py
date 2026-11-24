import sqlite3
import os
import sys

# Set the path for the database
db_path = os.path.abspath(os.path.join(os.getcwd(), 'data', 'studio.db'))

def find_ids():
    try:
        # Connect in read-only mode
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check tables to find the sources table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")

        if 'sources' in tables:
            cursor.execute("SELECT id, title, type, status, error FROM sources")
            rows = cursor.fetchall()
            print("Sources:")
            for row in rows:
                print(f"ID: {row['id']}, Title: {row['title']}, Type: {row['type']}, Status: {row['status']}, Error: {row['error']}")
        else:
            print("Table 'sources' not found.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_ids()
