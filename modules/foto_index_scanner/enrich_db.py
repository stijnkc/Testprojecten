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

def clean_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

def read_excel_resilient(file_path, skiprows=2):
    try:
        return pd.read_excel(file_path, skiprows=skiprows)
    except Exception:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "temp_enrich_" + os.path.basename(file_path))
        try:
            shutil.copy2(file_path, temp_file)
            df = pd.read_excel(temp_file, skiprows=skiprows)
            try:
                os.remove(temp_file)
            except Exception:
                pass
            return df
        except Exception as e:
            raise PermissionError(f"Kan Excel-bestand niet openen (zelfs niet via temp-kopie): {file_path}. Fout: {e}")

def migrate_and_enrich():
    print(f"Connecting to database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Database schema migration: add new columns if they do not exist
    cursor.execute("PRAGMA table_info(projecten);")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_cols = {
        'projectnummer': 'TEXT',
        'projectleider': 'TEXT',
        'opdrachtgever': 'TEXT',
        'status': 'TEXT',
        'werkveld': 'TEXT'
    }
    
    for col_name, col_type in new_cols.items():
        if col_name not in columns:
            print(f"Adding column '{col_name}' to table 'projecten'...")
            cursor.execute(f"ALTER TABLE projecten ADD COLUMN {col_name} {col_type};")
            
    conn.commit()

    # 2. Check if Excel files exist
    if not os.path.exists(EXCEL_FILE_1) or not os.path.exists(EXCEL_FILE_2):
        print(f"Error: Missing one of the Excel files in {EXCEL_DIR}")
        print(f"File 1 exists: {os.path.exists(EXCEL_FILE_1)}")
        print(f"File 2 exists: {os.path.exists(EXCEL_FILE_2)}")
        conn.close()
        return
        
    print(f"Loading Excel File 2 (Workfields): {EXCEL_FILE_2}...")
    df_excel2 = read_excel_resilient(EXCEL_FILE_2, skiprows=2)
    df_excel2.columns = [str(c).strip() for c in df_excel2.columns]
    df_excel2 = df_excel2.dropna(subset=['Project code'])
    
    # Build mapping from clean project code to workfield
    code_to_werkveld = {}
    for _, row in df_excel2.iterrows():
        raw_code = str(row['Project code']).replace('.0', '').strip()
        clean_code = re.sub(r'[^a-zA-Z0-9]', '', raw_code).lower()
        werkveld = str(row['werkveld']).strip() if not pd.isna(row['werkveld']) else None
        if werkveld and werkveld.lower() != 'nan' and werkveld.lower() != 'nvt':
            code_to_werkveld[clean_code] = werkveld
            
    print(f"Loaded {len(code_to_werkveld)} project code to workfield mappings.")

    print(f"Loading Excel File 1 (Sumatra metadata): {EXCEL_FILE_1}...")
    df_excel1 = read_excel_resilient(EXCEL_FILE_1, skiprows=2)
    df_excel1.columns = [str(c).strip() for c in df_excel1.columns]
    df_excel1 = df_excel1.dropna(subset=['Projectnummer'])
    
    # Build lookup dictionaries from File 1 + File 2 mapping
    num_to_details = {}
    for _, row in df_excel1.iterrows():
        raw_num = str(row['Projectnummer'])
        clean_num = re.sub(r'[^a-zA-Z0-9]', '', raw_num).lower()
        
        # Retrieve mapped workfield
        werkveld = code_to_werkveld.get(clean_num, None)
        
        num_to_details[clean_num] = {
            'nummer': raw_num,
            'omschrijving': str(row['Omschrijving']),
            'leider': str(row['Projectleider']) if not pd.isna(row['Projectleider']) else None,
            'client': str(row['Opdrachtgever']) if not pd.isna(row['Opdrachtgever']) else None,
            'status': str(row['Status']) if not pd.isna(row['Status']) else None,
            'werkveld': werkveld
        }
        
    name_to_num = {}
    for _, row in df_excel1.iterrows():
        clean_name = clean_text(row['Omschrijving'])
        raw_num = str(row['Projectnummer'])
        clean_num = re.sub(r'[^a-zA-Z0-9]', '', raw_num).lower()
        if clean_name:
            name_to_num[clean_name] = clean_num

    # 3. Retrieve all scanned project records
    cursor.execute("SELECT id, projectnaam, plaats, netwerk_pad, mapnaam_origineel FROM projecten")
    db_rows = cursor.fetchall()
    
    # Regex patterns for project numbers (e.g. 101.006.80 or 10100680)
    regex_dotted = re.compile(r'\b(\d{3})\.(\d{3})\.(\d{2})\b')
    regex_flat = re.compile(r'\b(\d{8})\b')
    regex_dash = re.compile(r'\b(\d{3})-(\d{3})-(\d{2})\b')

    matched_count = 0
    updates = []

    print("Mapping database records to project metadata...")
    for row in db_rows:
        db_id, projectnaam, plaats, netwerk_pad, mapnaam_origineel = row
        
        proj_num = None
        
        # Normalize double backslashes which can occur depending on scan root args
        normalized_pad = netwerk_pad.replace('\\\\', '\\')
        
        # Check for [3-digits]\[3-digits]\[2-digits] path pattern anywhere in the path
        pad_for_regex = normalized_pad + '\\' if not normalized_pad.endswith('\\') else normalized_pad
        m_path = re.search(r'\\(\d{3})\\(\d{3})\\(\d{2})\\', pad_for_regex)
        if m_path:
            proj_num = "".join(m_path.groups())
        
        # Check mapnaam next
        if not proj_num:
            m_dotted = regex_dotted.search(mapnaam_origineel)
            m_flat = regex_flat.search(mapnaam_origineel)
            m_dash = regex_dash.search(mapnaam_origineel)
            
            if m_dotted:
                proj_num = "".join(m_dotted.groups())
            elif m_flat:
                proj_num = m_flat.group(1)
            elif m_dash:
                proj_num = "".join(m_dash.groups())
                
        # Check netwerk_pad next
        if not proj_num:
            m_dotted_p = regex_dotted.search(netwerk_pad)
            m_flat_p = regex_flat.search(netwerk_pad)
            m_dash_p = regex_dash.search(netwerk_pad)
            
            if m_dotted_p:
                proj_num = "".join(m_dotted_p.groups())
            elif m_flat_p:
                proj_num = m_flat_p.group(1)
            elif m_dash_p:
                proj_num = "".join(m_dash_p.groups())
                
        # Perform Sumatra query mapping if project code was determined
        details = None
        if proj_num and proj_num in num_to_details:
            details = num_to_details[proj_num]
            
        if not details and projectnaam:
            clean_proj_name = clean_text(projectnaam)
            if clean_proj_name in name_to_num:
                details = num_to_details[name_to_num[clean_proj_name]]
                
        if details:
            matched_count += 1
            updates.append((
                details['nummer'],
                details['leider'],
                details['client'],
                details['status'],
                details['werkveld'],
                db_id
            ))
            
    # Batch update metadata into SQLite
    if updates:
        cursor.executemany("""
            UPDATE projecten 
            SET projectnummer = ?, projectleider = ?, opdrachtgever = ?, status = ?, werkveld = ?
            WHERE id = ?
        """, updates)
        conn.commit()

    print(f"Enrichment completed successfully! Matched {matched_count} of {len(db_rows)} records ({matched_count/len(db_rows)*100:.2f}%)")
    conn.close()

if __name__ == "__main__":
    migrate_and_enrich()
