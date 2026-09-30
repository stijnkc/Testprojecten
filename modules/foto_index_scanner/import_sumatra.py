import sqlite3
import pandas as pd
import re
import os
import shutil
import tempfile

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kc_foto_index.db")
EXCEL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Data KC projecten"))
EXCEL_FILE_1 = os.path.join(EXCEL_DIR, "1. Data KC projecten Sumatra tm juni 2026.xlsx")
EXCEL_FILE_2 = os.path.join(EXCEL_DIR, "2. Data KC projecten Sumatra tm juni 2026.xlsx")

def read_excel_resilient(file_path, skiprows=2):
    try:
        return pd.read_excel(file_path, skiprows=skiprows)
    except Exception:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "temp_import_" + os.path.basename(file_path))
        try:
            shutil.copy2(file_path, temp_file)
            df = pd.read_excel(temp_file, skiprows=skiprows)
            try:
                os.remove(temp_file)
            except Exception:
                pass
            return df
        except Exception as e:
            raise PermissionError(f"Kan Excel-bestand niet openen: {file_path}. Fout: {e}")

def import_sumatra():
    print(f"Connecting to database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create sumatra_projecten table with begindatum
    cursor.execute("DROP TABLE IF EXISTS sumatra_projecten;")
    cursor.execute("""
        CREATE TABLE sumatra_projecten (
            projectnummer TEXT PRIMARY KEY,
            projectnaam TEXT,
            plaats TEXT,
            projectleider TEXT,
            opdrachtgever TEXT,
            status TEXT,
            werkveld TEXT,
            begindatum TEXT
        );
    """)
    
    # Load Excel File 2 (Workfields)
    print("Loading Excel File 2...")
    df_excel2 = read_excel_resilient(EXCEL_FILE_2, skiprows=2)
    df_excel2.columns = [str(c).strip() for c in df_excel2.columns]
    df_excel2 = df_excel2.dropna(subset=['Project code'])
    
    code_to_werkveld = {}
    for _, row in df_excel2.iterrows():
        raw_code = str(row['Project code']).replace('.0', '').strip()
        clean_code = re.sub(r'[^a-zA-Z0-9]', '', raw_code).lower()
        werkveld = str(row['werkveld']).strip() if not pd.isna(row['werkveld']) else None
        if werkveld and werkveld.lower() != 'nan' and werkveld.lower() != 'nvt':
            code_to_werkveld[clean_code] = werkveld
            
    # Load Excel File 1 (Sumatra Metadata)
    print("Loading Excel File 1...")
    df_excel1 = read_excel_resilient(EXCEL_FILE_1, skiprows=2)
    df_excel1.columns = [str(c).strip() for c in df_excel1.columns]
    df_excel1 = df_excel1.dropna(subset=['Projectnummer'])
    
    # Map and prepare for database insertion
    batch_data = []
    seen_numbers = set()
    
    for _, row in df_excel1.iterrows():
        raw_num = str(row['Projectnummer']).strip()
        clean_num = re.sub(r'[^a-zA-Z0-9]', '', raw_num).lower()
        
        if not raw_num or raw_num in seen_numbers:
            continue
        seen_numbers.add(raw_num)
        
        werkveld = code_to_werkveld.get(clean_num, 'Onbekend')
        proj_name = str(row['Omschrijving']).strip() if not pd.isna(row['Omschrijving']) else 'Onbekend'
        plaats = str(row['Plaats']).strip() if not pd.isna(row['Plaats']) else 'Onbekend'
        leader = str(row['Projectleider']).strip() if not pd.isna(row['Projectleider']) else 'Onbekend'
        client = str(row['Opdrachtgever']).strip() if not pd.isna(row['Opdrachtgever']) else 'Onbekend'
        status = str(row['Status']).strip() if not pd.isna(row['Status']) else 'Onbekend'
        
        # Parse Begindatum cleanly
        if not pd.isna(row['Begindatum']):
            val = row['Begindatum']
            if isinstance(val, pd.Timestamp):
                begindatum = val.strftime('%Y-%m-%d')
            else:
                begindatum = str(val).split(' ')[0]
        else:
            begindatum = 'Onbekend'
        
        batch_data.append((
            raw_num,
            proj_name,
            plaats,
            leader,
            client,
            status,
            werkveld,
            begindatum
        ))
        
    print(f"Inserting {len(batch_data)} Sumatra projects into database...")
    cursor.executemany("""
        INSERT INTO sumatra_projecten (
            projectnummer, projectnaam, plaats, projectleider, opdrachtgever, status, werkveld, begindatum
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, batch_data)
    
    conn.commit()
    print("Import completed successfully!")
    conn.close()

if __name__ == "__main__":
    import_sumatra()
