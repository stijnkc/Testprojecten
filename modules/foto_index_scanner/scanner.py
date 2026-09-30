import os
import re
import sqlite3
import time
import argparse
import logging
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import pandas as pd
import shutil
import tempfile

# Setup paths inside the isolated module directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "scanner.log")
DB_FILE = os.path.join(SCRIPT_DIR, "kc_foto_index.db")
EXCEL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "Data KC projecten"))
EXCEL_FILE_1 = os.path.join(EXCEL_DIR, "1. Data KC projecten Sumatra tm juni 2026.xlsx")
EXCEL_FILE_2 = os.path.join(EXCEL_DIR, "2. Data KC projecten Sumatra tm juni 2026.xlsx")

# Setup logging configuration
logger = logging.getLogger("foto_index_scanner")
logger.setLevel(logging.INFO)

# File handler
fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler for feedback
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff'}
SELECTIE_TERMS = {"website", "selectie", "publicatie", "highres", "fotoselectie", "fotograaf selectie", "beelden selectie"}
# Note: "pr" and "pers" are too broad (match "project", "april", "perspectief", etc.)
# Instead we use a dedicated regex below for PR as an exact path segment
SELECTIE_PR_REGEX = re.compile(r'(?:^|[\\/])pr(?:[\\/]|$)', re.IGNORECASE)

# Regex patterns for folder name metadata parsing
PATTERN_YEAR_PROJ_PLACE = re.compile(r"^(\d{4})_(.+?)_(.+)$")
PATTERN_PROJ_DASH_PLACE = re.compile(r"^(.+?)\s*-\s*(.+)$")

# Regex patterns for project numbers (e.g. 101.006.80 or 10100680)
REGEX_DOTTED = re.compile(r'\b(\d{3})\.(\d{3})\.(\d{2})\b')
REGEX_FLAT = re.compile(r'\b(\d{8})\b')
REGEX_DASH = re.compile(r'\b(\d{3})-(\d{3})-(\d{2})\b')

def read_excel_resilient(file_path, skiprows=2):
    try:
        return pd.read_excel(file_path, skiprows=skiprows)
    except Exception:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "temp_scan_" + os.path.basename(file_path))
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

def init_db(db_path, clean=False):
    """
    Initializes the SQLite database and creates/extends the projecten table.
    """
    logger.info(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if clean:
        logger.info("Clean run requested. Dropping existing table projecten.")
        cursor.execute("DROP TABLE IF EXISTS projecten;")
    
    # Create database table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projecten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projectnaam TEXT,
            plaats TEXT,
            netwerk_pad TEXT UNIQUE,
            aantal_fotos INTEGER,
            mapnaam_origineel TEXT,
            foto_datum TEXT,
            is_selectie INTEGER DEFAULT 0,
            locatie_context TEXT,
            projectnummer TEXT,
            projectleider TEXT,
            opdrachtgever TEXT,
            status TEXT,
            werkveld TEXT
        );
    """)
    
    # Perform schema migrations dynamically if columns do not exist
    cursor.execute("PRAGMA table_info(projecten);")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations = {
        'foto_datum': 'TEXT',
        'is_selectie': 'INTEGER DEFAULT 0',
        'locatie_context': 'TEXT',
        'projectnummer': 'TEXT',
        'projectleider': 'TEXT',
        'opdrachtgever': 'TEXT',
        'status': 'TEXT',
        'werkveld': 'TEXT'
    }
    
    for col_name, col_type in migrations.items():
        if col_name not in columns:
            logger.info(f"Migrating schema: Adding '{col_name}' column to table projecten.")
            cursor.execute(f"ALTER TABLE projecten ADD COLUMN {col_name} {col_type};")
            
    # Ensure index on netwerk_pad exists
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_netwerk_pad ON projecten(netwerk_pad);")
    
    conn.commit()
    conn.close()

def parse_folder_name(folder_name):
    """
    Parses folder name according to KC conventions:
    1. Jaar_Projectnaam_Plaats
    2. Projectnaam - Plaats
    Returns (projectnaam, plaats) or (folder_name, None) as fallback.
    """
    match1 = PATTERN_YEAR_PROJ_PLACE.match(folder_name)
    if match1:
        proj_name = match1.group(2).strip()
        place = match1.group(3).strip()
        return proj_name, place

    match2 = PATTERN_PROJ_DASH_PLACE.match(folder_name)
    if match2:
        proj_name = match2.group(1).strip()
        place = match2.group(2).strip()
        return proj_name, place

    return folder_name.strip(), None

def get_first_jpg_exif_date(folder_path):
    """
    Scans the folder for the first available .jpg/.jpeg image and returns
    its EXIF DateTimeOriginal parsed as YYYY-MM-DD. Returns None if not found/error.
    """
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.lower().endswith(('.jpg', '.jpeg')):
                try:
                    with Image.open(entry.path) as img:
                        exif_data = img._getexif()
                        if exif_data:
                            for tag_id, val in exif_data.items():
                                tag_name = TAGS.get(tag_id, tag_id)
                                if tag_name == 'DateTimeOriginal':
                                    date_str = str(val).strip()
                                    if len(date_str) >= 10 and date_str[4] == ':' and date_str[7] == ':':
                                        return date_str[:10].replace(':', '-')
                                    return date_str
                except Exception:
                    pass
    except Exception:
        pass
    return None

def get_folder_fallback_date(folder_path):
    """Returns folder modification date formatted as YYYY-MM-DD."""
    try:
        mtime = os.path.getmtime(folder_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')

def clean_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

def load_excel_lookup():
    """Loads Sumatra Excel export files and builds mapping lookups."""
    if not os.path.exists(EXCEL_FILE_1) or not os.path.exists(EXCEL_FILE_2):
        logger.warning(f"Sumatra Excel files not found at: {EXCEL_DIR}. Scan will run without project matching.")
        return {}, {}
        
    try:
        logger.info("Loading Excel File 2 (Workfields)...")
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

        logger.info("Loading Excel File 1 (Sumatra metadata)...")
        df_excel1 = read_excel_resilient(EXCEL_FILE_1, skiprows=2)
        df_excel1.columns = [str(c).strip() for c in df_excel1.columns]
        df_excel1 = df_excel1.dropna(subset=['Projectnummer'])
        
        num_to_details = {}
        for _, row in df_excel1.iterrows():
            raw_num = str(row['Projectnummer'])
            clean_num = re.sub(r'[^a-zA-Z0-9]', '', raw_num).lower()
            
            # Map workfield
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
                
        logger.info(f"Successfully loaded {len(num_to_details)} project metadata definitions.")
        return num_to_details, name_to_num
    except Exception as e:
        logger.error(f"Error loading Excel lookup data: {e}")
        return {}, {}

def prevent_sleep():
    try:
        if os.name == 'nt':
            import ctypes
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            # Keeps the system awake without forcing the screen to stay on
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            logger.info("Windows Thread Execution State ingesteld: Slaapstand gedeactiveerd tijdens scan.")
    except Exception as e:
        logger.warning(f"Kon Windows slaapstand niet deactiveren: {e}")

def restore_sleep():
    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            logger.info("Standaard Windows energie-instellingen hersteld.")
    except Exception:
        pass

def scan_directory(scan_path, db_path):
    prevent_sleep()
    try:
        scan_directory_impl(scan_path, db_path)
    finally:
        restore_sleep()

def scan_directory_impl(scan_path, db_path):
    """Scans the specified directory, extracts metadata/dates/tags/context/projects, and writes to SQLite."""
    start_time = time.time()
    logger.info(f"Starting scan of directory: {scan_path}")

    if not os.path.exists(scan_path):
        logger.error(f"Scan path does not exist: {scan_path}")
        return

    # Load Excel lookup
    num_to_details, name_to_num = load_excel_lookup()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    abs_scan_path = os.path.abspath(scan_path)
    folders_checked = 0
    folders_added = 0
    total_photos_count = 0
    error_count = 0

    # Batch write parameters
    batch_data = []
    batch_size = 100

    for root, dirs, files in os.walk(abs_scan_path):
        folders_checked += 1
        
        # Periodic progress logging
        if folders_checked % 1000 == 0:
            logger.info(f"Progress: Checked {folders_checked} directories. Found {folders_added} directories with photos.")
            
        try:
            # Count photo files
            photo_count = 0
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in IMAGE_EXTENSIONS:
                    photo_count += 1

            if photo_count > 0:
                folder_name = os.path.basename(root)
                projectnaam, plaats = parse_folder_name(folder_name)
                netwerk_pad = root

                # Determine EXIF or fallback date
                exif_date = get_first_jpg_exif_date(root)
                foto_datum = exif_date if exif_date else get_folder_fallback_date(root)

                # Set selection tag — check full path (lowercase) for any selectie keyword,
                # OR check if "pr" appears as an isolated path segment (not as part of "project", "april", etc.)
                path_lower = netwerk_pad.lower()
                is_selectie = 1 if (
                    any(term in path_lower for term in SELECTIE_TERMS)
                    or SELECTIE_PR_REGEX.search(netwerk_pad)
                ) else 0

                # Location Context Extraction
                locatie_context = None
                try:
                    abs_root = os.path.abspath(root)
                    rel_path = os.path.relpath(abs_root, abs_scan_path)
                    if rel_path and rel_path != '.':
                        parts = rel_path.split(os.sep)
                        if len(parts) > 1:
                            locatie_context = parts[0]
                except Exception as e:
                    logger.warning(f"Error determining locatie_context for {root}: {e}")

                # --- PROJECT METADATA MATCHING ---
                proj_num = None
                
                # Normalize double backslashes which can occur depending on scan root args
                normalized_pad = netwerk_pad.replace('\\\\', '\\')
                
                # Check for [3-digits]\[3-digits]\[2-digits] path pattern anywhere in the path
                pad_for_regex = normalized_pad + '\\' if not normalized_pad.endswith('\\') else normalized_pad
                import re
                m_path = re.search(r'\\(\d{3})\\(\d{3})\\(\d{2})\\', pad_for_regex)
                if m_path:
                    proj_num = "".join(m_path.groups())
                
                # Check mapnaam next
                if not proj_num:
                    m_dotted = REGEX_DOTTED.search(folder_name)
                    m_flat = REGEX_FLAT.search(folder_name)
                    m_dash = REGEX_DASH.search(folder_name)
                    
                    if m_dotted:
                        proj_num = "".join(m_dotted.groups())
                    elif m_flat:
                        proj_num = m_flat.group(1)
                    elif m_dash:
                        proj_num = "".join(m_dash.groups())
                        
                # Check netwerk_pad next
                if not proj_num:
                    m_dotted_p = REGEX_DOTTED.search(netwerk_pad)
                    m_flat_p = REGEX_FLAT.search(netwerk_pad)
                    m_dash_p = REGEX_DASH.search(netwerk_pad)
                    
                    if m_dotted_p:
                        proj_num = "".join(m_dotted_p.groups())
                    elif m_flat_p:
                        proj_num = m_flat_p.group(1)
                    elif m_dash_p:
                        proj_num = "".join(m_dash_p.groups())

                # Validate project code
                details = None
                if proj_num and proj_num in num_to_details:
                    details = num_to_details[proj_num]
                    
                # Match by exact name
                if not details and projectnaam:
                    clean_proj_name = clean_text(projectnaam)
                    if clean_proj_name in name_to_num:
                        details = num_to_details[name_to_num[clean_proj_name]]

                # Extract metadata attributes
                p_num = details['nummer'] if details else None
                p_leader = details['leider'] if details else None
                p_client = details['client'] if details else None
                p_status = details['status'] if details else None
                p_werkveld = details['werkveld'] if details else None

                batch_data.append((
                    projectnaam,
                    plaats,
                    netwerk_pad,
                    photo_count,
                    folder_name,
                    foto_datum,
                    is_selectie,
                    locatie_context,
                    p_num,
                    p_leader,
                    p_client,
                    p_status,
                    p_werkveld
                ))
                
                folders_added += 1
                total_photos_count += photo_count

                # Flush batch to database
                if len(batch_data) >= batch_size:
                    cursor.executemany("""
                        INSERT INTO projecten (
                            projectnaam, plaats, netwerk_pad, aantal_fotos, 
                            mapnaam_origineel, foto_datum, is_selectie, locatie_context,
                            projectnummer, projectleider, opdrachtgever, status, werkveld
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(netwerk_pad) DO UPDATE SET
                            projectnaam=excluded.projectnaam,
                            plaats=excluded.plaats,
                            aantal_fotos=excluded.aantal_fotos,
                            mapnaam_origineel=excluded.mapnaam_origineel,
                            foto_datum=excluded.foto_datum,
                            is_selectie=excluded.is_selectie,
                            locatie_context=excluded.locatie_context,
                            projectnummer=excluded.projectnummer,
                            projectleider=excluded.projectleider,
                            opdrachtgever=excluded.opdrachtgever,
                            status=excluded.status,
                            werkveld=excluded.werkveld;
                    """, batch_data)
                    conn.commit()
                    batch_data = []

        except Exception as e:
            error_count += 1
            logger.error(f"Error checking directory {root}: {e}")

    # Write remaining batch data
    if batch_data:
        try:
            cursor.executemany("""
                INSERT INTO projecten (
                    projectnaam, plaats, netwerk_pad, aantal_fotos, 
                    mapnaam_origineel, foto_datum, is_selectie, locatie_context,
                    projectnummer, projectleider, opdrachtgever, status, werkveld
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(netwerk_pad) DO UPDATE SET
                    projectnaam=excluded.projectnaam,
                    plaats=excluded.plaats,
                    aantal_fotos=excluded.aantal_fotos,
                    mapnaam_origineel=excluded.mapnaam_origineel,
                    foto_datum=excluded.foto_datum,
                    is_selectie=excluded.is_selectie,
                    locatie_context=excluded.locatie_context,
                    projectnummer=excluded.projectnummer,
                    projectleider=excluded.projectleider,
                    opdrachtgever=excluded.opdrachtgever,
                    status=excluded.status,
                    werkveld=excluded.werkveld;
            """, batch_data)
            conn.commit()
        except Exception as e:
            logger.error(f"Error executing final batch write: {e}")

    conn.close()
    duration = time.time() - start_time
    
    logger.info("Scan completed successfully.")
    logger.info("--- Summary Report ---")
    logger.info(f"Target Scan Path: {scan_path}")
    logger.info(f"Total Folders Checked: {folders_checked}")
    logger.info(f"Folders with Photos: {folders_added}")
    logger.info(f"Total Photos Counted: {total_photos_count}")
    logger.info(f"Errors/Permission Denied: {error_count}")
    logger.info(f"Execution Time: {duration:.2f} seconds")
    logger.info("----------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KuiperCompagnons Photo Indexer Scanner")
    parser.add_argument("--path", required=True, help="Network path directory to scan recursively")
    parser.add_argument("--clean", action="store_true", help="Drop and rebuild SQLite table before scanning")
    args = parser.parse_args()
    
    init_db(DB_FILE, clean=args.clean)
    scan_directory(args.path, DB_FILE)
