import streamlit as st
import pandas as pd
import sqlite3
import os
import re


# Set page configuration with premium title and icon
st.set_page_config(
    page_title="KuiperCompagnons Foto-Indexering & Zoekmodule",
    page_icon="📸",
    layout="wide"
)

# Setup path to database
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "kc_foto_index.db")

# Custom CSS for rich professional branding and styling
st.markdown("""
    <style>
    /* Main Body & Background */
    .reportview-container {
        background: #f8f9fa;
    }
    
    /* Main Title Styling */
    .main-title {
        background: linear-gradient(135deg, #1f4068, #162447);
        padding: 2.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
    }
    .main-title h1 {
        margin: 0;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .main-title p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.85;
    }
    
    /* Stat Cards */
    .stat-card {
        background-color: #ffffff;
        border-left: 5px solid #1f4068;
        padding: 1.5rem;
        border-radius: 6px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1f4068;
    }
    .stat-label {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #6c757d;
        margin-top: 0.3rem;
    }
    
    /* Folder items (Regular Projects) */
    .folder-item-container {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* Folder items (Theme Archives / Photographer Selections) */
    .folder-item-container-theme {
        background-color: #faf5ff;
        border: 1px solid #e9d5ff;
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(107, 33, 168, 0.05);
    }
    
    /* Drive Badges */
    .badge-p {
        background-color: #007acc;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .badge-k {
        background-color: #28a745;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .badge-j {
        background-color: #e83e8c;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 6px;
    }
    
    /* Content Type Badges */
    .badge-type-photo {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        border: 1px solid #bbdefb;
    }
    .badge-type-drawing {
        background-color: #fff3e0;
        color: #e65100;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        border: 1px solid #ffe0b2;
    }
    .badge-type-other {
        background-color: #f5f5f5;
        color: #616161;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        border: 1px solid #e0e0e0;
    }
    
    /* Context Badge */
    .badge-context {
        background-color: #e2e8f0;
        color: #4a5568;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    
    /* Metadata Box */
    .meta-box {
        background-color: #f1f3f5;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper function to get clean project numbers for mapping
def clean_proj_num(val):
    if pd.isna(val):
        return ""
    return re.sub(r'\D', '', str(val))

def clean_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

# Load database tables with Streamlit caching (TTL 5 minutes for auto-refresh, manual button available)
@st.cache_data(ttl=300)
def load_photos_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM projecten", conn)
    conn.close()
    
    # Preprocessing
    df['plaats'] = df['plaats'].fillna('Onbekend')
    df['projectnaam'] = df['projectnaam'].fillna('Onbekend')
    df['foto_datum'] = df['foto_datum'].fillna('Onbekend')
    df['locatie_context'] = df['locatie_context'].fillna('')
    df['projectnummer'] = df['projectnummer'].fillna('')
    df['projectleider'] = df['projectleider'].fillna('')
    df['opdrachtgever'] = df['opdrachtgever'].fillna('')
    df['status'] = df['status'].fillna('')
    df['werkveld'] = df['werkveld'].fillna('')
    df['clean_projectnummer'] = df['projectnummer'].apply(clean_proj_num)
    return df

@st.cache_data(ttl=300)
def load_sumatra_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM sumatra_projecten", conn)
    conn.close()
    
    # Preprocessing
    df['plaats'] = df['plaats'].fillna('Onbekend')
    df['projectnaam'] = df['projectnaam'].fillna('Onbekend')
    df['projectnummer'] = df['projectnummer'].fillna('')
    df['projectleider'] = df['projectleider'].fillna('')
    df['opdrachtgever'] = df['opdrachtgever'].fillna('')
    df['status'] = df['status'].fillna('')
    df['werkveld'] = df['werkveld'].fillna('')
    df['begindatum'] = df['begindatum'].fillna('')
    df['clean_projectnummer'] = df['projectnummer'].apply(clean_proj_num)
    return df

# Main Header
st.markdown("""
    <div class="main-title">
        <h1>📸 KuiperCompagnons Foto-Indexering & Zoekmodule</h1>
        <p>Doorzoek projectbestanden van de P-, K- en J-schijf met Sumatra-projectleider en werkveldinformatie</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar Navigation controls
st.sidebar.header("🎯 Instellingen")

# Manual Cache Clear button
if st.sidebar.button("🔄 Data Verversen", help="Klik hier om de database handmatig opnieuw in te laden"):
    st.cache_data.clear()
    st.toast("Database-cache succesvol gewist!")

search_scope = st.sidebar.radio(
    "Zoekmodus:",
    options=[
        "📸 Foto-Zoeker (Alleen mappen met beelden)",
        "📁 Project-Zoeker (Alle 27.766 Sumatra-projecten)"
    ]
)

search_mode = st.sidebar.radio(
    "Zoekmethode:",
    options=["🔍 Vrij Zoeken", "🌳 Bladeren per Gemeente"]
)

only_selecties = False
if search_scope == "📸 Foto-Zoeker (Alleen mappen met beelden)":
    only_selecties = st.sidebar.checkbox("Alleen projecten met Selecties (⭐)", value=False)

# Load data (using cached functions)
df_photos = load_photos_data()
df_sumatra = load_sumatra_data()

# Helper to construct theoretical J and P drive folders based on 8-digit project number
def get_standard_paths(proj_num):
    digits = clean_proj_num(proj_num)
    if len(digits) >= 8:
        part1 = digits[0:3]
        part2 = digits[3:6]
        part3 = digits[6:8]
        rel_path = f"{part1}\\{part2}\\{part3}"
        
        paths = {
            'J-Schijf Projectmap': f"J:\\{rel_path}",
            'P-Schijf J-Archief (na 2010)': f"P:\\Archief J-schijf na 2010\\{rel_path}",
            'P-Schijf J-Archief (voor 2010)': f"P:\\Archief J-schijf voor 2010\\{rel_path}",
            'P-Schijf DTP Archief (na 2010)': f"P:\\Archief DTP na 2010\\{rel_path}"
        }
        return paths
    return {}

if df_photos.empty:
    st.warning("⚠️ De database is momenteel leeg. Draai eerst de scanner via `start_kc_zoekmodule.bat` of `python scanner.py`.")
else:
    # Filter variables
    filtered_df = pd.DataFrame()
    text_filtered_df = pd.DataFrame()
    
    if search_scope == "📸 Foto-Zoeker (Alleen mappen met beelden)":
        source_df = df_photos
    else:
        source_df = df_sumatra
        
    if search_mode == "🔍 Vrij Zoeken":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Vrij Zoeken")
        search_query = st.sidebar.text_input("Zoek op project, plaats, werkveld, nummer, leider of klant:", "").strip().lower()
        
        # Sortering dropdown — default is "Selecties eerst" zo dat mappen met fotoselecties bovenaan komen
        if search_scope.startswith("📸"):
            sort_options = ["⭐ Selecties eerst", "Aantal foto's (hoog-laag)", "Alfabetisch (A-Z)", "Meest recente foto (nieuw-oud)"]
        else:
            sort_options = ["Nieuwste projecten eerst", "Oudste projecten eerst", "Alfabetisch (A-Z)"]
            
        sort_option = st.sidebar.selectbox("Sorteer projecten op:", options=sort_options)
        
        # Apply Text Query Search (AND search)
        if search_query:
            stop_words = {'de', 'het', 'een', 'der', 'den', 'in', 'op', 'van', 'te'}
            search_words = [w for w in search_query.split() if w not in stop_words]
            
            if search_words:
                # Combine all searchable text per row
                if search_scope.startswith("📸"):
                    combined_text_series = (
                        source_df['projectnaam'].str.lower() + " " +
                        source_df['plaats'].str.lower() + " " +
                        source_df['locatie_context'].str.lower() + " " +
                        source_df['projectnummer'].str.lower() + " " +
                        source_df['projectleider'].str.lower() + " " +
                        source_df['opdrachtgever'].str.lower() + " " +
                        source_df['netwerk_pad'].str.lower() + " " +
                        source_df['werkveld'].str.lower() + " " +
                        source_df['mapnaam_origineel'].str.lower()
                    )
                else:
                    combined_text_series = (
                        source_df['projectnaam'].str.lower() + " " +
                        source_df['plaats'].str.lower() + " " +
                        source_df['projectnummer'].str.lower() + " " +
                        source_df['projectleider'].str.lower() + " " +
                        source_df['opdrachtgever'].str.lower() + " " +
                        source_df['status'].str.lower() + " " +
                        source_df['werkveld'].str.lower()
                    )
                
                # Check that ALL query words match the combined fields of a row
                mask = pd.Series(True, index=source_df.index)
                for word in search_words:
                    mask = mask & combined_text_series.str.contains(word, regex=False)
                text_filtered_df = source_df[mask]
            else:
                text_filtered_df = source_df
        else:
            text_filtered_df = source_df
            
    else:  # "🌳 Bladeren per Gemeente"
        st.sidebar.markdown("---")
        st.sidebar.subheader("Bladeren per Gemeente")
        
        # Get unique places (excluding empty, sorting alphabetically, placing 'Onbekend' at the end)
        raw_places = source_df['plaats'].unique()
        places_clean = sorted([p for p in raw_places if p and p != 'Onbekend' and p != ''])
        if 'Onbekend' in raw_places:
            places_clean.append('Onbekend')
            
        selected_place = st.sidebar.selectbox("Kies een Gemeente / Plaats:", options=places_clean)
        
        # Filter by selected place
        text_filtered_df = source_df[source_df['plaats'] == selected_place]
        
        # Sort option within this place
        if search_scope.startswith("📸"):
            sort_options = ["⭐ Selecties eerst", "Aantal foto's (hoog-laag)", "Alfabetisch (A-Z)"]
        else:
            sort_options = ["Nieuwste projecten eerst", "Oudste projecten eerst", "Alfabetisch (A-Z)"]
            
        sort_option = st.sidebar.selectbox("Sorteer projecten op:", options=sort_options)

    # DYNAMIC Projectleider Filter (Extract unique leaders ONLY from currently filtered search results!)
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 Projectleider")
    raw_leaders = text_filtered_df['projectleider'].unique()
    leaders_clean = sorted([str(l).strip() for l in raw_leaders if l and str(l).strip() not in ['', 'Onbekend', 'ONBEKEND', 'nan']])
    leader_options = ["Alle projectleiders"] + leaders_clean
    selected_leader = st.sidebar.selectbox("Filter op projectleider:", options=leader_options)

    # Apply Projectleider Filter to get final list
    if selected_leader != "Alle projectleiders":
        filtered_df = text_filtered_df[text_filtered_df['projectleider'] == selected_leader]
    else:
        filtered_df = text_filtered_df.copy()

    # Keywords to classify project priority tiers
    LOW_PRIORITY_KEYWORDS = [
        "bestemmingsplan", "bestemmingsplannen", "wijzigingsplan", "wijzigingsplannen", 
        "wijzigingsverzoek", "wijzigingsverzoeken", "rapportage", "rapportages", 
        "rapport", "rapporten", "milieu", "milieueffect", "vergunning", "vergunningen", 
        "bestemmings", "omgevingsplan", "omgevingsplannen", "omgevingsvergunning", 
        "planologisch", "planologische", "toelichting", "bp ", "wp ", "toelichtingen", "advies"
    ]
    
    LOW_PRIORITY_WERKVELDEN = [
        "milieuonderzoek", "bestemmingsplan", "juridische", "geluidsbelast", 
        "stikstof", "beleid", "actualisatie", "nvt"
    ]

    THEME_ARCHIVE_KEYWORDS = [
        "thema", "archief", "beeldenbank", "website", "portfolio", "pr-", "pr ", 
        "algemeen", "algemene", "referenties", "projectbladen", "fotoselecties", "fotograaf"
    ]

    # Calculate and Display Stats
    if search_scope.startswith("📸"):
        # We must compute group_key for filtered_df to show correct count of unique project groups
        # Define grouping key: projects with same projectnummer are unified. Otherwise fallback to name/place.
        def make_group_key(row):
            p_num = str(row['projectnummer']).strip()
            if p_num and p_num != 'Onbekend' and p_num != 'nan' and p_num != '':
                return f"NUM_{clean_proj_num(p_num)}"
            else:
                return f"NAME_{clean_text(row['projectnaam'])}_{clean_text(row['plaats'])}"

        if not filtered_df.empty:
            filtered_df['group_key'] = filtered_df.apply(make_group_key, axis=1)
            total_projects = filtered_df['group_key'].nunique()
            total_folders = len(filtered_df)
            total_photos = filtered_df['aantal_fotos'].sum()
        else:
            total_projects = 0
            total_folders = 0
            total_photos = 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{total_projects:,}</div><div class="stat-label">Gevonden Projecten</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{total_folders:,}</div><div class="stat-label">Submappen</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{total_photos:,}</div><div class="stat-label">Totale Foto\'s</div></div>', unsafe_allow_html=True)
    else:
        total_projects = len(filtered_df)
        st.markdown(f'<div class="stat-card" style="border-left: 5px solid #1f4068;"><div class="stat-value">{total_projects:,}</div><div class="stat-label">Gevonden Projectnummers in Sumatra</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Group results
    grouped_list = []
    
    if search_scope.startswith("📸"):
        if not filtered_df.empty:
            for g_key, group in filtered_df.groupby('group_key'):
                total_group_photos = group['aantal_fotos'].sum()
                valid_dates = group[group['foto_datum'] != 'Onbekend']['foto_datum']
                latest_date = valid_dates.max() if not valid_dates.empty else 'Onbekend'
                has_selectie = (group['is_selectie'] == 1).any()
                
                p_num = ""
                p_leader = ""
                p_client = ""
                p_status = ""
                p_werkveld = ""
                proj = ""
                plt = ""
                
                # Retrieve official Sumatra project info if project number is present
                valid_nums = group[group['projectnummer'] != '']
                if not valid_nums.empty:
                    p_num = valid_nums.iloc[0]['projectnummer']
                    clean_num = clean_proj_num(p_num)
                    
                    sumatra_match = df_sumatra[df_sumatra['clean_projectnummer'] == clean_num]
                    if not sumatra_match.empty:
                        proj = sumatra_match.iloc[0]['projectnaam']
                        plt = sumatra_match.iloc[0]['plaats']
                        p_leader = sumatra_match.iloc[0]['projectleider']
                        p_client = sumatra_match.iloc[0]['opdrachtgever']
                        p_status = sumatra_match.iloc[0]['status']
                        p_werkveld = sumatra_match.iloc[0]['werkveld']
                    else:
                        proj = valid_nums.iloc[0]['projectnaam']
                        plt = valid_nums.iloc[0]['plaats']
                        p_leader = valid_nums.iloc[0]['projectleider']
                        p_client = valid_nums.iloc[0]['opdrachtgever']
                        p_status = valid_nums.iloc[0]['status']
                        p_werkveld = valid_nums.iloc[0]['werkveld']
                else:
                    # Fallback for reference folders without project code
                    proj = group.iloc[0]['projectnaam']
                    plt = group.iloc[0]['plaats']
                
                combined_text = f"{proj} {plt} {p_client} {p_werkveld} ".lower() + " ".join(group['mapnaam_origineel'].astype(str).tolist()).lower()
                combined_paths = " ".join(group['netwerk_pad'].astype(str).tolist()).lower()
                
                is_theme = any(kw in combined_text for kw in THEME_ARCHIVE_KEYWORDS) or any(kw in combined_paths for kw in ["beeldenbank", "pr arch", "website kc", "portfolio", "referenties"])
                is_report = any(kw in combined_text for kw in LOW_PRIORITY_KEYWORDS) or any(kw in p_werkveld.lower() for kw in LOW_PRIORITY_WERKVELDEN)
                
                project_tier = "project"
                priority_score = 0
                if is_theme:
                    project_tier = "theme"
                    priority_score = -1
                elif is_report:
                    project_tier = "report"
                    priority_score = 1

                grouped_list.append({
                    'projectnaam': proj,
                    'plaats': plt,
                    'total_photos': total_group_photos,
                    'latest_date': latest_date,
                    'has_selectie': has_selectie,
                    'projectnummer': p_num,
                    'projectleider': p_leader,
                    'opdrachtgever': p_client,
                    'status': p_status,
                    'werkveld': p_werkveld,
                    'project_tier': project_tier,
                    'priority_score': priority_score,
                    'records': group
                })
                
            if only_selecties:
                grouped_list = [g for g in grouped_list if g['has_selectie']]
                
            # Apply sorting for Foto-Zoeker
            if sort_option == "⭐ Selecties eerst":
                # Projecten met selecties bovenaan, daarna op aantal foto's; theme-mappen onderaan
                grouped_list = sorted(grouped_list, key=lambda x: (x['priority_score'], not x['has_selectie'], -x['total_photos']))
            elif sort_option == "Alfabetisch (A-Z)":
                grouped_list = sorted(grouped_list, key=lambda x: (x['priority_score'], x['projectnaam'].lower(), x['plaats'].lower()))
            elif sort_option == "Aantal foto's (hoog-laag)":
                grouped_list = sorted(grouped_list, key=lambda x: (x['priority_score'], -x['total_photos']))
            elif sort_option == "Meest recente foto (nieuw-oud)":
                grouped_list = sorted(grouped_list, key=lambda x: (-x['priority_score'], x['latest_date'] == 'Onbekend', x['latest_date']), reverse=True)
            
    else: # "📁 Project-Zoeker"
        for _, row in filtered_df.iterrows():
            proj = str(row['projectnaam'])
            plt = str(row['plaats'])
            p_num = str(row['projectnummer'])
            p_leader = str(row['projectleider'])
            p_client = str(row['opdrachtgever'])
            p_status = str(row['status'])
            p_werkveld = str(row['werkveld'])
            p_begindatum = str(row['begindatum']) if 'begindatum' in row else ''
            
            grouped_list.append({
                'projectnaam': proj,
                'plaats': plt,
                'projectnummer': p_num,
                'projectleider': p_leader,
                'opdrachtgever': p_client,
                'status': p_status,
                'werkveld': p_werkveld,
                'begindatum': p_begindatum
            })
            
        # Apply Chronological sorting based on Begindatum (not project number string!)
        if sort_option == "Nieuwste projecten eerst":
            grouped_list = sorted(
                grouped_list, 
                key=lambda x: x['begindatum'] if (x['begindatum'] and x['begindatum'] != 'Onbekend' and x['begindatum'] != 'nan') else '0000-00-00', 
                reverse=True
            )
        elif sort_option == "Oudste projecten eerst":
            grouped_list = sorted(
                grouped_list, 
                key=lambda x: x['begindatum'] if (x['begindatum'] and x['begindatum'] != 'Onbekend' and x['begindatum'] != 'nan') else '9999-12-31'
            )
        elif sort_option == "Alfabetisch (A-Z)":
            grouped_list = sorted(grouped_list, key=lambda x: x['projectnaam'].lower())

    # Render results
    st.subheader(f"Projecten Overzicht ({len(grouped_list)})")
    
    if not grouped_list:
        st.info("Geen projecten gevonden die voldoen aan de zoekcriteria.")
    else:
        # Use loop index `idx` to construct globally unique keys for child widgets
        for idx, project in enumerate(grouped_list):
            proj = project['projectnaam']
            plt = project['plaats']
            p_num = project['projectnummer']
            p_leader = project['projectleider']
            p_werkveld = project['werkveld']
            
            # Form header indicators
            place_indicator = f" - {plt}" if plt != 'Onbekend' else ""
            leader_indicator = f" | PL: {p_leader}" if p_leader else ""
            wv_indicator = f" | {p_werkveld}" if p_werkveld else ""
            
            if search_scope.startswith("📸"):
                tier = project['project_tier']
                total_photos = project['total_photos']
                latest_date = project['latest_date']
                has_selectie = project['has_selectie']
                star_indicator = " ⭐" if has_selectie else ""
                
                num_indicator = f" | Nr: {p_num}" if p_num else ""
                if tier == "theme":
                    type_prefix = "🌟 **[FOTO-ARCHIEF / REFERENTIES]** "
                elif tier == "report":
                    type_prefix = "📄 [Rapport/Plan] "
                else:
                    type_prefix = "📸 "
                header_title = f"{type_prefix}{proj}{place_indicator}{num_indicator}{leader_indicator}{wv_indicator} | {total_photos} foto's | Laatste: {latest_date}{star_indicator}"
            else:
                # Retrieve and format begindatum for Project-Zoeker header (e.g. [2021-03])
                p_begindatum = project.get('begindatum', '')
                date_indicator = ""
                if p_begindatum and p_begindatum != 'Onbekend' and p_begindatum != 'nan':
                    date_indicator = f" [{p_begindatum[:7]}]"
                
                # Clean, uniform chronological index headers for Project-Zoeker
                header_title = f"📁 {p_num}{date_indicator} | {proj}{place_indicator}{leader_indicator}{wv_indicator}"

            with st.expander(header_title):
                # Render Theme Info Alert (only in Foto-Zoeker mode)
                if search_scope.startswith("📸") and tier == "theme":
                    st.markdown('<p style="background:#faf5ff;color:#6b21a8;padding:6px 10px;border-radius:4px;font-size:0.85rem;border:1px solid #d8b4fe;margin-bottom:0.75rem;">🌟 <strong>Algemeen Foto-Archief:</strong> Thematische fotocollecties, PR-bestanden of fotograaf-selecties van meerdere projecten.</p>', unsafe_allow_html=True)
                
                # Compacte Sumatra-samenvatting: alleen gevulde velden tonen
                meta_parts = []
                if p_num:
                    meta_parts.append(f'<span style="font-weight:600;">Nr:</span> <code style="font-size:0.8rem;">{p_num}</code>')
                if p_werkveld:
                    meta_parts.append(f'<span style="font-weight:600;">Werkveld:</span> {p_werkveld}')
                if project['projectleider']:
                    meta_parts.append(f'<span style="font-weight:600;">PL:</span> {project["projectleider"]}')
                if project['opdrachtgever']:
                    meta_parts.append(f'<span style="font-weight:600;">Opdrachtgever:</span> {project["opdrachtgever"]}')
                if project['status']:
                    meta_parts.append(f'<span style="font-weight:600;">Status:</span> {project["status"]}')
                if meta_parts:
                    meta_html = ' &nbsp;·&nbsp; '.join(meta_parts)
                    st.markdown(f'<p style="background:#f1f3f5;border:1px solid #dee2e6;border-radius:4px;padding:5px 10px;font-size:0.82rem;color:#495057;margin-bottom:0.5rem;">{meta_html}</p>', unsafe_allow_html=True)
                
                # Function to render folder list with drive badges, content type badges, and direct open buttons
                def render_folder_list(folders, section_title, key_prefix):
                    st.markdown(section_title)
                    for _, row in folders.iterrows():
                        drive_badge = ""
                        pad_upper = row['netwerk_pad'].upper()
                        if pad_upper.startswith('P:'):
                            drive_badge = '<span class="badge-p">[P-Drive]</span>'
                        elif pad_upper.startswith('K:'):
                            drive_badge = '<span class="badge-k">[K-Drive]</span>'
                        elif pad_upper.startswith('J:'):
                            drive_badge = '<span class="badge-j">[J-Drive]</span>'
                        
                        folder_type = "Map (Overig)"
                        folder_icon = "📁"
                        badge_class = "badge-type-other"
                        
                        drawing_keywords = ['tekening', 'dwg', 'dxf', 'plattegrond', 'sectie', 'gevel', 'kaart', 'situatie', 'details', 'plot', 'ontwerptekening', 'bestek', 'pdf', 'links', 'illustrator', 'vector']
                        photo_keywords = ['foto', 'photo', 'beeld', 'lucht', 'impressie', 'camera', 'visu', 'render', 'picture', 'jpg', 'jpeg', 'png']
                        
                        path_lower = row['netwerk_pad'].lower()
                        folder_lower = row['mapnaam_origineel'].lower()
                        
                        is_dwg = any(kw in folder_lower for kw in drawing_keywords) or any(kw in path_lower for kw in drawing_keywords)
                        is_pic = any(kw in folder_lower for kw in photo_keywords) or any(kw in path_lower for kw in photo_keywords)
                        
                        if is_dwg:
                            folder_type = "Tekening / DTP / PDF"
                            folder_icon = "📐"
                            badge_class = "badge-type-drawing"
                        elif is_pic:
                            folder_type = "Foto / Visualisatie"
                            folder_icon = "📸"
                            badge_class = "badge-type-photo"
                        
                        context_badge = ""
                        if row['locatie_context']:
                            context_badge = f'<span class="badge-context">Context: {row["locatie_context"]}</span>'
                            
                        # Set container class based on search mode (only Foto-Zoeker gets lila highlighted theme folder boxes)
                        is_photo_scope = search_scope.startswith("📸")
                        container_class = "folder-item-container-theme" if (is_photo_scope and tier == "theme") else "folder-item-container"
                        
                        col_info, col_action = st.columns([5, 1])
                        with col_info:
                            clean_path = row['netwerk_pad'].replace('\\\\', '\\')
                            st.markdown(f"""
                                <div class="{container_class}">
                                    {folder_icon} <strong>{row['mapnaam_origineel']}</strong> {drive_badge} <span class="{badge_class}">{folder_type}</span> {context_badge}
                                    <span style="color:#6c757d;font-size:0.8rem;"> &nbsp;·&nbsp; {row['aantal_fotos']} foto's &nbsp;·&nbsp; {row['foto_datum']}</span><br/>
                                    <span style="font-family:monospace;font-size:0.78rem;color:#495057;word-break:break-all;">{clean_path}</span>
                                </div>
                            """, unsafe_allow_html=True)
                        with col_action:
                            st.write("")
                            st.write("")
                            btn_key = f"open_{key_prefix}_{row['id']}"
                            if st.button("📂 Open Verkenner", key=btn_key, help="Klik om deze map direct te openen in Windows Verkenner"):
                                import subprocess
                                clean_path = row['netwerk_pad'].replace('\\\\', '\\')
                                if not os.path.exists(clean_path):
                                    st.session_state[btn_key + "_msg"] = ("warn", f"Map niet bereikbaar ({clean_path[:3]})")
                                else:
                                    try:
                                        subprocess.Popen(['explorer', clean_path])
                                        st.session_state[btn_key + "_msg"] = ("ok", "Verkenner geopend!")
                                    except Exception as ex:
                                        st.session_state[btn_key + "_msg"] = ("err", str(ex))
                            msg_state = st.session_state.get(btn_key + "_msg")
                            if msg_state:
                                if msg_state[0] == "ok":
                                    st.success(msg_state[1])
                                elif msg_state[0] == "warn":
                                    st.warning(msg_state[1])
                                else:
                                    st.error(msg_state[1])

                # Render section based on search scope
                if search_scope.startswith("📸"):
                    group_df = project['records']
                    group_df['date_sort_helper'] = group_df['foto_datum'].apply(lambda x: '0000-00-00' if x == 'Onbekend' else x)
                    sorted_group = group_df.sort_values(by=['is_selectie', 'date_sort_helper'], ascending=[False, False])
                    
                    # Generate a unique prefix based on loop index for Foto-Zoeker
                    unique_prefix = f"foto_{idx}"
                    
                    unique_contexts = sorted_group['locatie_context'].unique()
                    if len(unique_contexts) == 1 and unique_contexts[0] == "":
                        selecties = sorted_group[sorted_group['is_selectie'] == 1]
                        hoofdmappen = sorted_group[sorted_group['is_selectie'] == 0]
                        if not selecties.empty:
                            render_folder_list(selecties, "##### 🌟 Handmatige Selecties (PR / Website)", f"{unique_prefix}_sel")
                        if not hoofdmappen.empty:
                            render_folder_list(hoofdmappen, "##### 📂 Projectmappen (Nieuw naar Oud)", f"{unique_prefix}_main")
                    else:
                        for ctx in unique_contexts:
                            ctx_group = sorted_group[sorted_group['locatie_context'] == ctx]
                            ctx_name = ctx if ctx else "Hoofdniveau / Overige deeluitwerking"
                            st.markdown(f"<div style='margin-top: 1.25rem; margin-bottom: 0.5rem; padding-bottom: 3px; border-bottom: 1.5px solid #1f4068; font-weight: 600; color: #1f4068;'>📍 Deeluitwerking: {ctx_name}</div>", unsafe_allow_html=True)
                            selecties = ctx_group[ctx_group['is_selectie'] == 1]
                            hoofdmappen = ctx_group[ctx_group['is_selectie'] == 0]
                            
                            safe_ctx = clean_proj_num(ctx)
                            if not selecties.empty:
                                render_folder_list(selecties, "##### 🌟 Handmatige Selecties (PR / Website)", f"{unique_prefix}_{safe_ctx}_sel")
                            if not hoofdmappen.empty:
                                render_folder_list(hoofdmappen, "##### 📂 Projectmappen (Nieuw naar Oud)", f"{unique_prefix}_{safe_ctx}_main")
                                
                else: # "📁 Project-Zoeker"
                    # 1. Check filesystem for standard root directories
                    std_paths = get_standard_paths(p_num)
                    existing_std_paths = {}
                    
                    if std_paths:
                        for label, path in std_paths.items():
                            if os.path.exists(path):
                                existing_std_paths[label] = path
                                
                    # Render theoretical explorer links
                    st.markdown("##### 📁 Snelkoppelingen naar Projectmappen (Windows Verkenner)")
                    if existing_std_paths:
                        cols = st.columns(len(existing_std_paths))
                        for path_idx, (label, path) in enumerate(existing_std_paths.items()):
                            with cols[path_idx]:
                                if st.button(f"📂 {label}", key=f"std_open_{idx}_{p_num}_{path_idx}", help=f"Open direct: {path}"):
                                    import subprocess
                                    try:
                                        subprocess.Popen(['explorer', path])
                                        st.success(f"{label} geopend!")
                                    except Exception as ex:
                                        st.error(f"Fout: {ex}")
                    else:
                        st.info("Geen standaard projectmappen gedetecteerd op de J- of P-schijf voor dit projectnummer.")
                        
                    # 2. Check if we also have scanned subfolders containing photos/drawings in the database
                    clean_num = clean_proj_num(p_num)
                    project_photos = df_photos[df_photos['clean_projectnummer'] == clean_num]
                    
                    if not project_photos.empty:
                        st.markdown("---")
                        project_photos['date_sort_helper'] = project_photos['foto_datum'].apply(lambda x: '0000-00-00' if x == 'Onbekend' else x)
                        sorted_photos = project_photos.sort_values(by=['is_selectie', 'date_sort_helper'], ascending=[False, False])
                        
                        unique_prefix = f"proj_{idx}"
                        
                        unique_contexts = sorted_photos['locatie_context'].unique()
                        if len(unique_contexts) == 1 and unique_contexts[0] == "":
                            selecties = sorted_photos[sorted_photos['is_selectie'] == 1]
                            hoofdmappen = sorted_photos[sorted_photos['is_selectie'] == 0]
                            if not selecties.empty:
                                render_folder_list(selecties, "##### 🌟 Gescande Fotoselecties (PR / Website)", f"{unique_prefix}_sel")
                            if not hoofdmappen.empty:
                                render_folder_list(hoofdmappen, "##### 📸 Gescande Mappen met beelden", f"{unique_prefix}_main")
                        else:
                            for ctx in unique_contexts:
                                ctx_group = sorted_photos[sorted_photos['locatie_context'] == ctx]
                                ctx_name = ctx if ctx else "Hoofdniveau / Overige deeluitwerking"
                                st.markdown(f"<div style='margin-top: 1.25rem; margin-bottom: 0.5rem; padding-bottom: 3px; border-bottom: 1.5px solid #1f4068; font-weight: 600; color: #1f4068;'>📍 Deeluitwerking: {ctx_name}</div>", unsafe_allow_html=True)
                                selecties = ctx_group[ctx_group['is_selectie'] == 1]
                                hoofdmappen = ctx_group[ctx_group['is_selectie'] == 0]
                                
                                safe_ctx = clean_proj_num(ctx)
                                if not selecties.empty:
                                    render_folder_list(selecties, "##### 🌟 Gescande Fotoselecties (PR / Website)", f"{unique_prefix}_{safe_ctx}_sel")
                                if not hoofdmappen.empty:
                                    render_folder_list(hoofdmappen, "##### 📸 Gescande Mappen met beelden", f"{unique_prefix}_{safe_ctx}_main")
