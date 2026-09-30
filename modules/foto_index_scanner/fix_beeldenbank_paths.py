import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kc_foto_index.db")

def fix_records():
    print(f"Connecting to database to fix Beeldenbank paths: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, netwerk_pad, projectnaam, plaats, mapnaam_origineel, locatie_context FROM projecten")
    rows = cursor.fetchall()
    
    updates = []
    
    for row in rows:
        db_id, netwerk_pad, current_proj, current_place, folder_name, current_ctx = row
        
        # We process any path containing 'Beeldenbank'
        if 'Beeldenbank' in netwerk_pad:
            parts = netwerk_pad.split(os.sep)
            
            new_place = current_place
            new_proj = current_proj
            new_ctx = current_ctx
            
            # Pattern 1: Projecten_KC (found under Beeldenbank Algemeen KC)
            if 'Projecten_KC' in parts:
                idx = parts.index('Projecten_KC')
                # Structure: Projecten_KC -> COUNTRY -> ALPHABET_GROUP -> MUNICIPALITY -> PROJECT_FOLDER -> [SUBFOLDERS...]
                if len(parts) > idx + 3:
                    new_place = parts[idx + 3]
                    
                if len(parts) > idx + 4:
                    new_proj = parts[idx + 4]
                    # Clean leading underscores
                    if new_proj.startswith('_'):
                        new_proj = new_proj[1:]
                    # Strip municipality name from project folder name if redundant
                    if new_place and new_proj.lower().startswith(new_place.lower()):
                        new_proj = new_proj[len(new_place):].lstrip('_ -')
                        
                # Determine sub-phase / context
                if len(parts) > idx + 5:
                    new_ctx = " / ".join(parts[idx + 5:])
                else:
                    new_ctx = ""
                    
            # Pattern 2: binnenland (found under Stedenbouw)
            elif 'binnenland' in parts:
                idx = parts.index('binnenland')
                # Structure: binnenland -> MUNICIPALITY -> PROJECT_FOLDER -> [SUBFOLDERS...]
                if len(parts) > idx + 1:
                    new_place = parts[idx + 1]
                    
                if len(parts) > idx + 2:
                    new_proj = parts[idx + 2]
                    if new_proj.startswith('_'):
                        new_proj = new_proj[1:]
                    if new_place and new_proj.lower().startswith(new_place.lower()):
                        new_proj = new_proj[len(new_place):].lstrip('_ -')
                        
                # Determine sub-phase / context
                if len(parts) > idx + 3:
                    new_ctx = " / ".join(parts[idx + 3:])
                else:
                    new_ctx = ""
            
            # Clean place name formatting
            if new_place:
                new_place = new_place.strip('_ -')
                if new_place.lower() in ('onbekend', ''):
                    new_place = 'Onbekend'
            else:
                new_place = 'Onbekend'
            
            # Clean project name formatting
            if new_proj:
                new_proj = new_proj.replace('_', ' ').strip()
                if not new_proj:
                    new_proj = folder_name
            else:
                new_proj = folder_name
                
            # Clean context name formatting
            if new_ctx:
                new_ctx = new_ctx.replace('_', ' ').strip()
            else:
                new_ctx = ""
                
            # Queue database update if values changed
            if (new_place != current_place) or (new_proj != current_proj) or (new_ctx != current_ctx):
                updates.append((new_proj, new_place, new_ctx, db_id))
                
    if updates:
        print(f"Updating {len(updates)} records with refined Beeldenbank project structure...")
        cursor.executemany("""
            UPDATE projecten
            SET projectnaam = ?,
                plaats = ?,
                locatie_context = ?
            WHERE id = ?
        """, updates)
        conn.commit()
        print("Database update complete!")
    else:
        print("No database updates needed.")
        
    conn.close()

if __name__ == "__main__":
    fix_records()
