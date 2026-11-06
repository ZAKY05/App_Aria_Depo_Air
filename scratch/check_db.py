import sqlite3

conn = sqlite3.connect('depo_air.db')
cursor = conn.cursor()

for t in ['expenses', 'courier_wages', 'couriers', 'courier_settlements', 'transactions']:
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,))
    row = cursor.fetchone()
    print(f"=== {t} ===")
    if row:
        print(row[0])
    else:
        print("Table does not exist")
