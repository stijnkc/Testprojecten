"""
fix_truncated_paths.py
----------------------
Detecteer en rapporteer paden in de database die niet beginnen met een
geldige schijfletter (X:\). Dit zijn afgeknipte/beschadigde paden.
"""
import sqlite3, os, re

DB = r'c:\Users\stijn\OneDrive - KuiperCompagnons B.V\Antigravity\FOTOARCHIEF_KC_DOORZOEKER\modules\foto_index_scanner\kc_foto_index.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

DRIVE_PATTERN = re.compile(r'^[A-Za-z]:\\')

c.execute("SELECT id, netwerk_pad FROM projecten")
rows = c.fetchall()

bad = [(row_id, pad) for row_id, pad in rows if not DRIVE_PATTERN.match(pad)]
good = [(row_id, pad) for row_id, pad in rows if DRIVE_PATTERN.match(pad)]

print(f"Totaal records: {len(rows)}")
print(f"Paden zonder geldige schijfletter: {len(bad)}")
print()

if bad:
    print("Voorbeelden van beschadigde paden:")
    for row_id, pad in bad[:20]:
        print(f"  ID {row_id}: '{pad[:100]}'")
    
    print()
    inp = input(f"Verwijder alle {len(bad)} beschadigde records? (j/n): ").strip().lower()
    if inp == 'j':
        ids = [r[0] for r in bad]
        c.executemany("DELETE FROM projecten WHERE id=?", [(i,) for i in ids])
        conn.commit()
        print(f"Verwijderd: {len(bad)} records.")
    else:
        print("Niet verwijderd.")
else:
    print("Geen beschadigde paden gevonden!")

conn.close()
