import sqlite3
from pathlib import Path

DB_PATH = Path('instance') / 'ropa_system.db'
if not DB_PATH.exists():
    DB_PATH = Path('ropa_system.db')

print('Using DB:', DB_PATH)
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute("SELECT id, filename, upload_timestamp FROM excel_files WHERE filename LIKE '%ROPA%' ORDER BY upload_timestamp")
files = cur.fetchall()
if not files:
    print('No ROPA files found; nothing to do.')
    conn.close()
    exit(0)

print('Found ROPA excel_files:')
for f in files:
    print('  id=', f[0], ' filename=', f[1], ' uploaded=', f[2])

# Keep the latest by upload_timestamp
cur.execute("SELECT id FROM excel_files WHERE filename LIKE '%ROPA%' ORDER BY upload_timestamp DESC LIMIT 1")
keep = cur.fetchone()[0]
ids = [f[0] for f in files]
ids_to_delete = [i for i in ids if i != keep]

if not ids_to_delete:
    print('No duplicates to delete; only one ROPA file present.')
    conn.close()
    exit(0)

print('\nKeeping id=', keep)
print('Deleting ids=', ids_to_delete)

# Delete sheets for these files
placeholders = ','.join('?' for _ in ids_to_delete)
cur.execute(f"DELETE FROM excel_sheets WHERE excel_file_id IN ({placeholders})", ids_to_delete)
deleted_sheets = cur.rowcount
cur.execute(f"DELETE FROM excel_files WHERE id IN ({placeholders})", ids_to_delete)
deleted_files = cur.rowcount
conn.commit()
conn.close()
print(f'Deleted {deleted_files} excel_files and {deleted_sheets} excel_sheets')
