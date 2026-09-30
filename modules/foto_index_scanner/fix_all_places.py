import sqlite3
import os
import re
import pandas as pd

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kc_foto_index.db")
EXCEL_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "1. Data KC projecten Sumatra tm juni 2026.xlsx"))

def clean_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

def fix_all():
    print(f"Connecting to database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Load Excel place metadata for matched projects
    num_to_place = {}
    if os.path.exists(EXCEL_FILE):
        print(f"Loading Excel file to match places: {EXCEL_FILE}...")
        df_excel = pd.read_excel(EXCEL_FILE, header=2)
        df_excel.columns = [str(c).strip() for c in df_excel.columns]
        df_excel = df_excel.dropna(subset=['Projectnummer'])
        
        for _, row in df_excel.iterrows():
            proj_num = str(row['Projectnummer'])
            place = str(row['Plaats']) if not pd.isna(row['Plaats']) else None
            if place:
                num_to_place[proj_num] = place
        print(f"Loaded {len(num_to_place)} project-to-place mappings from Sumatra.")
        
    cursor.execute("SELECT id, netwerk_pad, projectnaam, plaats, mapnaam_origineel, projectnummer FROM projecten")
    rows = cursor.fetchall()
    
    updates = []
    
    # Regex for Bouwkunde Documentatietekeningen pattern:
    # e.g., "524.004.XX Den Haag - VAHON school (documentatie)"
    # group 1 = place, group 2 = project
    regex_bouwkunde = re.compile(r'^\d{3}\.\d{3}\.XX\s+([a-zA-Z\s\-]+)\s*-\s*(.+)$', re.IGNORECASE)
    
    # Common Dutch cities for path scanning
    CITIES = [
        "Den Haag", "Rotterdam", "Amsterdam", "Utrecht", "Amersfoort", "Gorinchem",
        "Almere", "Apeldoorn", "Arnhem", "Assen", "Bergschenhoek", "Breda", "Cromstrijen",
        "De Ronde Venen", "Den Helder", "Heerenveen", "Heerhugowaard", "Hendrik-Ido-Ambacht",
        "Hoogeveen", "Hoorn", "Leiden", "Maassluis", "Nijkerk", "Nijmegen", "Noordwijk",
        "Rijnsburg", "Vlist", "Wervershoof", "Woerden", "Zaandam", "Zaltbommel", "Zwartwaterland",
        "Delft", "Dordrecht", "Gouda", "Schiedam", "Vlaardingen", "Zoetermeer", "Zwolle"
    ]
    city_lower_map = {c.lower(): c for c in CITIES}
    
    for row in rows:
        db_id, netwerk_pad, current_proj, current_place, folder_name, projectnummer = row
        
        new_place = current_place
        new_proj = current_proj
        
        # Rule 1: Use Sumatra Excel Place if projectnummer is matched
        if projectnummer and projectnummer in num_to_place:
            new_place = num_to_place[projectnummer]
            
        # Rule 2: Fix Bouwkunde folder names that were parsed backwards
        m_bk = regex_bouwkunde.match(folder_name)
        if m_bk:
            new_place = m_bk.group(1).strip()
            new_proj = m_bk.group(2).strip()
            
        # Rule 3: Check for Documentatie/Nederland/<City> pattern in path
        parts = netwerk_pad.split(os.sep)
        parts_lower = [p.lower() for p in parts]
        if 'nederland' in parts_lower:
            idx = parts_lower.index('nederland')
            if len(parts) > idx + 1:
                city_dir = parts[idx + 1]
                # Avoid generic subfolders like "A tm F" as cities
                if city_dir not in ("A tm F", "G tm L", "M tm R", "S tm Z", "T tm Z"):
                    new_place = city_dir.replace('_', ' ').strip()
                    
        # Rule 4: General keyword scan in path components for missing places
        if not new_place or new_place == 'Onbekend' or new_place == 'None':
            # Scan path parts for any known city names
            for p in parts_lower:
                for c_low, c_real in city_lower_map.items():
                    if c_low in p:
                        new_place = c_real
                        break
                if new_place and new_place != 'Onbekend':
                    break
                    
        # Clean place name format
        if new_place:
            new_place = new_place.strip('_ -')
            # Normalize common names
            if 'den haag' in new_place.lower() or 'gravenhage' in new_place.lower():
                new_place = 'DEN HAAG'
            elif 'rotterdam' in new_place.lower():
                new_place = 'ROTTERDAM'
            elif 'amsterdam' in new_place.lower():
                new_place = 'AMSTERDAM'
            elif 'utrecht' in new_place.lower():
                new_place = 'UTRECHT'
            elif 'amersfoort' in new_place.lower():
                new_place = 'AMERSFOORT'
            else:
                new_place = new_place.upper()
        else:
            new_place = 'ONBEKEND'
            
        if new_proj:
            if new_proj.startswith('_'):
                new_proj = new_proj[1:]
            new_proj = new_proj.replace('_', ' ').strip()
            
        if (new_place != current_place) or (new_proj != current_proj):
            updates.append((new_proj, new_place, db_id))
            
    if updates:
        print(f"Updating {len(updates)} records with refined project names and place classifications...")
        cursor.executemany("""
            UPDATE projecten
            SET projectnaam = ?,
                plaats = ?
            WHERE id = ?
        """, updates)
        conn.commit()
        print("Database update complete!")
    else:
        print("No database updates needed.")
        
    conn.close()

if __name__ == "__main__":
    fix_all()
