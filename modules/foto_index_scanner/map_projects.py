import sqlite3
import pandas as pd
import re
import os

DB_FILE = r"c:\Users\stijn\OneDrive - KuiperCompagnons B.V\Antigravity\Foto architef\modules\foto_index_scanner\kc_foto_index.db"
EXCEL_FILE = r"c:\Users\stijn\OneDrive - KuiperCompagnons B.V\Antigravity\Foto architef\1. Data KC projecten Sumatra tm juni 2026.xlsx"

def clean_text(text):
    if pd.isna(text):
        return ""
    # Lowercase and keep alphanumeric characters only
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

def run_mapping():
    # Load Excel master list
    df_excel = pd.read_excel(EXCEL_FILE, header=2)
    # Ensure columns are clean strings
    df_excel.columns = [str(c).strip() for c in df_excel.columns]
    
    # Filter rows with valid project numbers
    df_excel = df_excel.dropna(subset=['Projectnummer'])
    df_excel['proj_num_clean'] = df_excel['Projectnummer'].astype(str).str.replace('.', '', regex=False).str.strip()
    df_excel['omschrijving_clean'] = df_excel['Omschrijving'].apply(clean_text)
    
    # Create lookup dictionaries for quick matching
    num_to_details = {}
    for _, row in df_excel.iterrows():
        clean_num = row['proj_num_clean']
        num_to_details[clean_num] = {
            'nummer': str(row['Projectnummer']),
            'omschrijving': str(row['Omschrijving']),
            'leider': str(row['Projectleider']) if not pd.isna(row['Projectleider']) else None,
            'client': str(row['Opdrachtgever']) if not pd.isna(row['Opdrachtgever']) else None,
            'status': str(row['Status']) if not pd.isna(row['Status']) else None
        }
        
    name_to_num = {}
    for _, row in df_excel.iterrows():
        clean_name = row['omschrijving_clean']
        if clean_name:
            # Avoid overwriting with empty or generic names
            name_to_num[clean_name] = row['proj_num_clean']

    # Load database records
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, projectnaam, plaats, netwerk_pad, mapnaam_origineel FROM projecten")
    db_rows = c.fetchall()
    
    # Compile regex for 8-digit or dotted project numbers: e.g. 101.006.80 or 10100680
    regex_dotted = re.compile(r'\b(\d{3})\.(\d{3})\.(\d{2})\b')
    regex_flat = re.compile(r'\b(\d{8})\b')
    regex_dash = re.compile(r'\b(\d{3})-(\d{3})-(\d{2})\b')

    matched_by_num = 0
    matched_by_name = 0
    total_matched = 0
    total_rows = len(db_rows)

    matched_data = []

    for row in db_rows:
        db_id, projectnaam, plaats, netwerk_pad, mapnaam_origineel = row
        
        # 1. Try to find project number via Regex in path or folder name
        proj_num = None
        match_source = None
        
        # Search in mapnaam first
        m_dotted = regex_dotted.search(mapnaam_origineel)
        m_flat = regex_flat.search(mapnaam_origineel)
        m_dash = regex_dash.search(mapnaam_origineel)
        
        if m_dotted:
            proj_num = "".join(m_dotted.groups())
            match_source = "exif_path_dotted"
        elif m_flat:
            proj_num = m_flat.group(1)
            match_source = "exif_path_flat"
        elif m_dash:
            proj_num = "".join(m_dash.groups())
            match_source = "exif_path_dash"
            
        # Search in netwerk_pad if not found in mapnaam
        if not proj_num:
            m_dotted_p = regex_dotted.search(netwerk_pad)
            m_flat_p = regex_flat.search(netwerk_pad)
            m_dash_p = regex_dash.search(netwerk_pad)
            
            if m_dotted_p:
                proj_num = "".join(m_dotted_p.groups())
                match_source = "path_dotted"
            elif m_flat_p:
                proj_num = m_flat_p.group(1)
                match_source = "path_flat"
            elif m_dash_p:
                proj_num = "".join(m_dash_p.groups())
                match_source = "path_dash"
                
        # Validate if found number exists in our master list
        details = None
        if proj_num and proj_num in num_to_details:
            details = num_to_details[proj_num]
            matched_by_num += 1
            
        # 2. Try matching by Project Name if no number matched
        if not details and projectnaam:
            clean_proj_name = clean_text(projectnaam)
            if clean_proj_name in name_to_num:
                found_num = name_to_num[clean_proj_name]
                details = num_to_details[found_num]
                matched_by_name += 1
                
        # 3. Fallback matching (fuzzy search: if clean_proj_name is in a master description)
        if not details and projectnaam:
            clean_proj_name = clean_text(projectnaam)
            if len(clean_proj_name) > 4: # avoid short generic words
                for clean_name, found_num in name_to_num.items():
                    if clean_proj_name == clean_name or clean_proj_name in clean_name or clean_name in clean_proj_name:
                        details = num_to_details[found_num]
                        matched_by_name += 1
                        break

        if details:
            total_matched += 1
            matched_data.append((db_id, details))

    print(f"Total Database Rows: {total_rows}")
    print(f"Matched by Number Regex: {matched_by_num}")
    print(f"Matched by Name String: {matched_by_name}")
    print(f"Total Matched: {total_matched} ({total_matched/total_rows*100:.2f}%)")
    
    # Print a few samples of matched details
    print("\nSamples of matches:")
    for db_id, details in matched_data[:10]:
        print(f" ID {db_id}: Num: {details['nummer']} | Name: {details['omschrijving']} | Leader: {details['leider']}")

    conn.close()

if __name__ == "__main__":
    run_mapping()
