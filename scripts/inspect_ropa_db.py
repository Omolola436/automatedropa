import sqlite3
import json
import sys
from pathlib import Path

paths = [Path('instance') / 'ropa_system.db', Path('ropa_system.db')]
found = []
for p in paths:
    if p.exists():
        found.append(p)

if not found:
    print('No DB file found at expected locations:', paths)
    sys.exit(1)

for DB_PATH in found:
    print('\n--- DB file:', DB_PATH, 'size=', DB_PATH.stat().st_size)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print('  Tables:', tables)
    except Exception as e:
        print('  Error listing tables:', e)
    conn.close()

# Prefer instance DB if present
DB_PATH = Path('instance') / 'ropa_system.db'
if not DB_PATH.exists():
    DB_PATH = Path('ropa_system.db')

print('\nUsing DB for further inspection:', DB_PATH)
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# List excel_files
try:
    cur.execute("SELECT id, filename, total_sheets, upload_timestamp FROM excel_files ORDER BY id")
    files = cur.fetchall()
    print('\nFound excel_files:')
    for f in files:
        print(f"  id={f['id']}, filename={f['filename']}, total_sheets={f['total_sheets']}, upload_timestamp={f['upload_timestamp']}")
except Exception as e:
    print('\nCould not query excel_files:', e)
    conn.close()
    sys.exit(0)

# Try to locate ROPA.xlsx
cur.execute("SELECT id, filename, total_sheets, upload_timestamp FROM excel_files WHERE filename LIKE '%ROPA%'")
ropa_files = cur.fetchall()
if not ropa_files:
    print('\nNo excel_file with filename LIKE "%ROPA%" found.')
    conn.close()
    sys.exit(0)

for rf in ropa_files:
    fid = rf['id']
    print(f"\nROPA candidate: id={fid}, filename={rf['filename']}, total_sheets={rf['total_sheets']}, upload_timestamp={rf['upload_timestamp']}")
    cur.execute('SELECT id, sheet_name, row_count, column_count, created_at FROM excel_sheets WHERE excel_file_id = ? ORDER BY id', (fid,))
    sheets = cur.fetchall()
    print(f"  Sheets count: {len(sheets)}")
    for s in sheets:
        print(f"    sheet id={s['id']}, name={s['sheet_name']}, rows={s['row_count']}, cols={s['column_count']}, created_at={s['created_at']}")

    # Detect duplicates by sheet_name + sheet_data
    cur.execute('''
        SELECT sheet_name, sheet_data, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM excel_sheets
        WHERE excel_file_id = ?
        GROUP BY sheet_name, sheet_data
        HAVING cnt > 1
    ''', (fid,))
    dups = cur.fetchall()
    if dups:
        print('\n  Duplicate groups found:')
        for d in dups:
            print(f"    sheet_name={d['sheet_name']} count={d['cnt']} ids={d['ids']}")
    else:
        print('\n  No exact duplicate sheet_name+sheet_data groups found.')

conn.close()
print('\nDone')
