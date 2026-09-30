"""
fix_selectie_flags.py
---------------------
Repareer de is_selectie vlag in de bestaande database op basis van de
gecorrigeerde logica (geen brede 'pr' of 'pers' substrings meer).
Draait als standalone script.
"""
import sqlite3
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "kc_foto_index.db")

# Bijgewerkte logica (zelfde als in scanner.py na fix)
SELECTIE_TERMS = {"website", "selectie", "publicatie", "highres", "fotoselectie"}
SELECTIE_PR_REGEX = re.compile(r'(?:^|[\\/])pr(?:[\\/]|$)', re.IGNORECASE)

def is_selectie(path: str) -> int:
    path_lower = path.lower()
    if any(term in path_lower for term in SELECTIE_TERMS):
        return 1
    if SELECTIE_PR_REGEX.search(path):
        return 1
    return 0

print(f"Verbinden met database: {DB_FILE}")
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Laad alle paden op
c.execute("SELECT id, netwerk_pad, is_selectie FROM projecten")
rows = c.fetchall()
print(f"Totaal records geladen: {len(rows)}")

updates = []
changed_to_1 = 0
changed_to_0 = 0

for row_id, netwerk_pad, old_flag in rows:
    new_flag = is_selectie(netwerk_pad)
    if new_flag != old_flag:
        updates.append((new_flag, row_id))
        if new_flag == 1:
            changed_to_1 += 1
        else:
            changed_to_0 += 1

print(f"Wijzigingen: {len(updates)} records")
print(f"  - Nu als selectie gemarkeerd:   {changed_to_1}")
print(f"  - Niet langer als selectie:     {changed_to_0}")

if updates:
    c.executemany("UPDATE projecten SET is_selectie=? WHERE id=?", updates)
    conn.commit()
    print("Database bijgewerkt!")

# Controleer resultaat
c.execute("SELECT COUNT(*) FROM projecten WHERE is_selectie=1")
n_sel = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM projecten")
n_total = c.fetchone()[0]
print(f"\nNa fix: {n_sel} selecties van {n_total} records ({n_sel/n_total*100:.1f}%)")

# Toon enkele voorbeelden van échte selecties
print("\nVoorbeelden van als selectie gemarkeerde mappen:")
c.execute("SELECT netwerk_pad FROM projecten WHERE is_selectie=1 LIMIT 15")
for r in c.fetchall():
    print("  ", r[0][-100:])

conn.close()
print("\nKlaar!")
