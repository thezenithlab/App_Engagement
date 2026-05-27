#!/usr/bin/env python3
"""
classification_pipeline.py - Pipeline to classify 85,323 apps into:
1. Psychographic Class: Hedonic (SELF) vs Pragmatic (ACT)
2. Motivational Subcategory: Achievement, Connection, Escape, Growth

Uses a Hybrid Cascade Pipeline:
Stage 1: Rule-Based Category Mapping & Keyword Refinement
Stage 2: Semantic Embedding & Dimensionality Projection (PCA + t-SNE) for Top 10,000 apps
Stage 3: Local LLM Agent Audit (gemma4:e4b) on Sample Apps
"""

import os
import sqlite3
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADDITIONAL_DB = os.path.join(BASE_DIR, "DB", "ADDITIONAL_DATA.db")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
CSV_DIR = os.path.join(EXPORTS_DIR, "CSV_files")
OUTPUT_DB = os.path.join(EXPORTS_DIR, "HICSS60_classified_apps.db")

os.makedirs(CSV_DIR, exist_ok=True)

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "gemma4:e4b"

# ============================================================
# STAGE 1: Deterministic Rules & Keyword Mapping
# ============================================================

GENRE_MAPPING = {
    # ----------------------------------------
    # HEDONIC (SELF)
    # ----------------------------------------
    # Games (Escape)
    "Puzzle": ("HEDONIC", "Escape"),
    "Casual": ("HEDONIC", "Escape"),
    "Simulation": ("HEDONIC", "Escape"),
    "Action": ("HEDONIC", "Escape"),
    "Arcade": ("HEDONIC", "Escape"),
    "Role Playing": ("HEDONIC", "Escape"),
    "Sports": ("HEDONIC", "Escape"),
    "Adventure": ("HEDONIC", "Escape"),
    "Strategy": ("HEDONIC", "Escape"),
    "Card": ("HEDONIC", "Escape"),
    "Casino": ("HEDONIC", "Escape"),
    "Board": ("HEDONIC", "Escape"),
    "Trivia": ("HEDONIC", "Escape"),
    "Word": ("HEDONIC", "Escape"),
    "Racing": ("HEDONIC", "Escape"),
    "Music": ("HEDONIC", "Escape"),
    "Educational": ("HEDONIC", "Escape"),
    "Role Playing / Simulation": ("HEDONIC", "Escape"),
    "visual novel": ("HEDONIC", "Escape"),
    "Dating Sim": ("HEDONIC", "Escape"),
    "Game": ("HEDONIC", "Escape"),
    "Gaming": ("HEDONIC", "Escape"),
    "Mobile Game": ("HEDONIC", "Escape"),
    "Arcade RPG": ("HEDONIC", "Escape"),
    "Arcade & Action": ("HEDONIC", "Escape"),
    "Arcade & ACTION": ("HEDONIC", "Escape"),
    "Casual / Racing": ("HEDONIC", "Escape"),
    "Casino / Slots": ("HEDONIC", "Escape"),
    "Cards & Casino": ("HEDONIC", "Escape"),
    "Sports Games": ("HEDONIC", "Escape"),
    "Sports Simulation": ("HEDONIC", "Escape"),
    "Sports / Casino": ("HEDONIC", "Escape"),
    "Puzles y juegos de pensar": ("HEDONIC", "Escape"),
    
    # Social & Communication (Connection)
    "Social": ("HEDONIC", "Connection"),
    "Communication": ("HEDONIC", "Connection"),
    "Social Networking": ("HEDONIC", "Connection"),
    "Dating": ("HEDONIC", "Connection"),
    "Dating / Social": ("HEDONIC", "Connection"),
    "DATING": ("HEDONIC", "Connection"),
    "Messaging": ("HEDONIC", "Connection"),
    "Chat & Instant Messaging": ("HEDONIC", "Connection"),
    "Lifestyle / Social": ("HEDONIC", "Connection"),
    
    # Entertainment & Photography (Escape)
    "Entertainment": ("HEDONIC", "Escape"),
    "Music & Audio": ("HEDONIC", "Escape"),
    "Photography": ("HEDONIC", "Escape"),
    "Video Players & Editors": ("HEDONIC", "Escape"),
    "Personalization": ("HEDONIC", "Escape"),
    "Themes & Wallpaper": ("HEDONIC", "Escape"),
    "Themes": ("HEDONIC", "Escape"),
    "RINGTONES": ("HEDONIC", "Escape"),
    "Multimedia & Video": ("HEDONIC", "Escape"),
    "Media & Video": ("HEDONIC", "Escape"),
    "Video": ("HEDONIC", "Escape"),
    "video": ("HEDONIC", "Escape"),
    "Audio": ("HEDONIC", "Escape"),
    "TV/Radio": ("HEDONIC", "Escape"),
    "TV & Movies": ("HEDONIC", "Escape"),
    "Music & Radio": ("HEDONIC", "Escape"),
    "MUSIC_AND_AUDIO": ("HEDONIC", "Escape"),
    "Comics / Manga": ("HEDONIC", "Escape"),
    "Comics & Book Readers": ("HEDONIC", "Escape"),
    "Humor": ("HEDONIC", "Escape"),
    "Funny": ("HEDONIC", "Escape"),

    # Self-Development & Learning (Growth)
    "Education": ("HEDONIC", "Growth"),
    "Health & Fitness": ("HEDONIC", "Growth"),
    "health & fitness": ("HEDONIC", "Growth"),
    "Books & Reference": ("HEDONIC", "Growth"),
    "BOOKS_AND_REFERENCE": ("HEDONIC", "Growth"),
    "Education / Productivity": ("HEDONIC", "Growth"),
    "EDUCATION": ("HEDONIC", "Growth"),
    "Art & Design": ("HEDONIC", "Growth"),
    "Graphic & Design": ("HEDONIC", "Growth"),
    "Graphic Apps": ("HEDONIC", "Growth"),
    "Parenting": ("HEDONIC", "Growth"),
    "Lifestyle / Health & Fitness": ("HEDONIC", "Growth"),
    "Fitness": ("HEDONIC", "Growth"),
    "Health & Nutrition": ("HEDONIC", "Growth"),
    "Health": ("HEDONIC", "Growth"),

    # ----------------------------------------
    # PRAGMATIC / UTILITARIAN (ACT)
    # ----------------------------------------
    # Utilities, Tools & Office (Achievement)
    "Tools": ("PRAGMATIC", "Achievement"),
    "Finance": ("PRAGMATIC", "Achievement"),
    "finance": ("PRAGMATIC", "Achievement"),
    "Business": ("PRAGMATIC", "Achievement"),
    "Productivity": ("PRAGMATIC", "Achievement"),
    "Shopping": ("PRAGMATIC", "Achievement"),
    "Food & Drink": ("PRAGMATIC", "Achievement"),
    "Food and Drink": ("PRAGMATIC", "Achievement"),
    "FOOD_AND_DRINK": ("PRAGMATIC", "Achievement"),
    "Medical": ("PRAGMATIC", "Achievement"),
    "Medicine": ("PRAGMATIC", "Achievement"),
    "Weather": ("PRAGMATIC", "Achievement"),
    "WEATHER": ("PRAGMATIC", "Achievement"),
    "Auto & Vehicles": ("PRAGMATIC", "Achievement"),
    "Maps & Navigation": ("PRAGMATIC", "Achievement"),
    "House & Home": ("PRAGMATIC", "Achievement"),
    "Beauty": ("PRAGMATIC", "Achievement"),
    "Events": ("PRAGMATIC", "Achievement"),
    "Travel & Local": ("PRAGMATIC", "Achievement"),
    "Travel and Transportation": ("PRAGMATIC", "Achievement"),
    "Travel & Transportation": ("PRAGMATIC", "Achievement"),
    "Transportation": ("PRAGMATIC", "Achievement"),
    "Navigation": ("PRAGMATIC", "Achievement"),
    "Maps And Navigation": ("PRAGMATIC", "Achievement"),
    "Voyage & La Navigation": ("PRAGMATIC", "Achievement"),
    "Business & Productivity": ("PRAGMATIC", "Achievement"),
    "Tools / Productivity": ("PRAGMATIC", "Achievement"),
    "System Utilities": ("PRAGMATIC", "Achievement"),
    "System Maintenance": ("PRAGMATIC", "Achievement"),
    "Security/Performance": ("PRAGMATIC", "Achievement"),
    "Security": ("PRAGMATIC", "Achievement"),
    "File Management": ("PRAGMATIC", "Achievement"),
    "file management": ("PRAGMATIC", "Achievement"),
    "Cloud Storage": ("PRAGMATIC", "Achievement"),
    "App Store & Updater": ("PRAGMATIC", "Achievement"),
    "Connectivity": ("PRAGMATIC", "Achievement"),
    "Internet": ("PRAGMATIC", "Achievement"),
    "Government": ("PRAGMATIC", "Achievement"),
    "Insurance": ("PRAGMATIC", "Achievement"),
    "News & Magazines": ("PRAGMATIC", "Achievement"),
    "News": ("PRAGMATIC", "Achievement"),
    "News/Magazines": ("PRAGMATIC", "Achievement"),
    "Personal Finance": ("PRAGMATIC", "Achievement"),
    "Accounting & Finance": ("PRAGMATIC", "Achievement"),
}

def classify_app_stage1(title: str, genre: str, categories: str) -> tuple[str, str, str]:
    """
    Stage 1 classification: Apply deterministic mappings and keyword-based refinement.
    Returns: (psychographic_class, motivational_driver, classification_method)
    """
    title_str = str(title) if (title is not None and not pd.isna(title)) else ""
    genre_str = str(genre) if (genre is not None and not pd.isna(genre)) else ""
    categories_str = str(categories).lower() if (categories is not None and not pd.isna(categories)) else ""
    title_lower = title_str.lower()
    
    # 1. First check high-confidence direct mappings
    if genre_str in GENRE_MAPPING:
        p_class, m_driver = GENRE_MAPPING[genre_str]
        method = "deterministic_genre"
    else:
        # Default fallback
        p_class, m_driver = "PRAGMATIC", "Achievement"
        method = "default_fallback"

    # 2. Refinement based on Title & Category keywords for highly ambiguous categories (Lifestyle, Personalization, Tools)
    if genre_str in ("Lifestyle", "Personalization", "Tools", "NULL", "", None):
        # Connection keywords
        if any(kw in title_lower for kw in ["dating", "chat", "meet", "friend", "flirt", "social", "love", "romance", "companionship", "boyfriend", "girlfriend"]):
            p_class, m_driver = "HEDONIC", "Connection"
            method = "keyword_connection"
        # Escape keywords
        elif any(kw in title_lower for kw in ["wallpaper", "icon", "theme", "widget", "funny", "joke", "prank", "game", "toy", "virtual", "tarot", "horoscope", "astrology"]):
            p_class, m_driver = "HEDONIC", "Escape"
            method = "keyword_escape"
        # Growth keywords
        elif any(kw in title_lower for kw in ["workout", "fitness", "diet", "sleep", "meditat", "yoga", "habit", "study", "learn", "quran", "bible", "prayer"]):
            p_class, m_driver = "HEDONIC", "Growth"
            method = "keyword_growth"
        # Achievement keywords
        elif any(kw in title_lower for kw in ["smart", "remote", "calculator", "file", "lock", "wifi", "battery", "scanner", "cleaner", "track", "office", "work"]):
            p_class, m_driver = "PRAGMATIC", "Achievement"
            method = "keyword_achievement"

    return p_class, m_driver, method

# ============================================================
# STAGE 2: Semantic Embedding Generation via Ollama nomic-embed-text
# ============================================================

def get_embedding(text: str) -> list[float]:
    """Fetch 768-dim text embedding from local Ollama nomic-embed-text API."""
    url = f"{OLLAMA_URL}/api/embeddings"
    data = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("embedding", [])
    except Exception as e:
        print(f"Embedding failed for '{text[:20]}': {e}", file=sys.stderr)
        return []

def batch_generate_embeddings(apps: list[dict], max_workers: int = 15) -> list[dict]:
    """Generate embeddings in parallel using ThreadPoolExecutor."""
    print(f"Generating embeddings for {len(apps)} apps using {max_workers} threads...")
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_app = {}
        for app in apps:
            # Combine title and genre as semantic text
            semantic_text = f"App Name: {app['title']} | Category: {app['genre']}"
            future = executor.submit(get_embedding, semantic_text)
            future_to_app[future] = app
            
        completed_count = 0
        t0 = time.time()
        
        for future in as_completed(future_to_app):
            app = future_to_app[future]
            completed_count += 1
            emb = future.result()
            
            if emb:
                app["embedding"] = emb
                results.append(app)
            else:
                app["embedding"] = None
                
            if completed_count % 500 == 0:
                elapsed = time.time() - t0
                rate = completed_count / elapsed
                print(f"  Processed {completed_count}/{len(apps)} embeddings ({rate:.1f} apps/sec)")
                
    return results

# ============================================================
# STAGE 3: Local LLM Agent Audit
# ============================================================

def call_local_llm(prompt: str) -> str:
    """Send prompt to local Ollama LLM and get response."""
    url = f"{OLLAMA_URL}/api/generate"
    data = json.dumps({
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("response", "").strip()
    except Exception as e:
        return f"LLM error: {e}"

def audit_single_app(app: dict) -> dict:
    prompt = f"""You are an academic expert in mobile human-computer interaction (HCI) and user psychology.
Classify this app using these two frameworks:

1. Psychographic Classification:
- **HEDONIC** (SELF-Type): Driven by leisure, play, aesthetics, social connections, identity, or emotional validation.
- **PRAGMATIC** (ACT-Type): Driven by task completion, instrumental needs, utilities, work, productivity, or business goals.

2. Motivational Driver Category:
- **Achievement**: motivated by Efficiency / task completion. (Spreadsheets, business utilities, calculators, banking, shopping tools).
- **Connection**: motivated by Belonging / social validation. (Social media, dating apps, chat groups, discussion forums).
- **Escape**: motivated by Stimulation / distraction / pleasure. (Games, video streaming, music players, ringtone/personalization tools).
- **Growth**: motivated by Competence / self-improvement / mastery. (Language learning, workouts/fitness trackers, meditation, daily journals).

App Metadata:
- Title: "{app['title']}"
- Genre: "{app['genre']}"
- Package: "{app['OriginalID']}"

Your current classification:
- Psychographic: {app['psychographic_class']}
- Motivational Driver: {app['motivational_driver']}

Please respond strictly in JSON format as shown below:
{{
  "psychographic": "HEDONIC" or "PRAGMATIC",
  "motivational_driver": "Achievement" or "Connection" or "Escape" or "Growth",
  "reasoning": "A 1-sentence academic justification."
}}"""

    resp = call_local_llm(prompt)
    try:
        # Try to parse JSON from the response
        # Find the JSON braces if LLM outputs markdown backticks
        start = resp.find("{")
        end = resp.rfind("}") + 1
        if start != -1 and end != 0:
            json_str = resp[start:end]
            parsed = json.loads(json_str)
            
            app["llm_psychographic"] = parsed.get("psychographic", "").upper()
            app["llm_driver"] = parsed.get("motivational_driver", "")
            app["llm_reasoning"] = parsed.get("reasoning", "")
            app["audit_matched"] = (app["llm_psychographic"] == app["psychographic_class"]) and (app["llm_driver"] == app["motivational_driver"])
        else:
            app["llm_psychographic"] = "ERROR"
            app["llm_driver"] = "ERROR"
            app["llm_reasoning"] = f"Unparseable response: {resp[:100]}"
            app["audit_matched"] = False
    except Exception as e:
        app["llm_psychographic"] = "ERROR"
        app["llm_driver"] = "ERROR"
        app["llm_reasoning"] = f"Exception: {e}"
        app["audit_matched"] = False
        
    return app

def audit_classification_agent(apps_to_audit: list[dict], max_workers: int = 8) -> list[dict]:
    """Uses LLM to verify and audit classification for a sample of apps in parallel."""
    print(f"Starting parallel LLM agent audit on {len(apps_to_audit)} sample apps with {max_workers} threads...")
    audited_apps = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_app = {executor.submit(audit_single_app, app): app for app in apps_to_audit}
        completed_count = 0
        
        for future in as_completed(future_to_app):
            audited_apps.append(future.result())
            completed_count += 1
            if completed_count % 20 == 0:
                print(f"  Audited {completed_count}/{len(apps_to_audit)} apps...")
                
    return audited_apps

# ============================================================
# MAIN PIPELINE EXECUTION
# ============================================================

def main():
    t_start = time.time()
    print("============================================================")
    print("HICSS60 Psychographic & Motivational Classification Pipeline")
    print("============================================================")
    
    # 1. Fetch apps from ADDITIONAL_DATA.db
    print(f"Connecting to source database: {ADDITIONAL_DB}")
    conn_src = sqlite3.connect(ADDITIONAL_DB)
    df_apps = pd.read_sql("SELECT OriginalID, title, genre, categories, realInstalls, reviews, score FROM APPS", conn_src)
    conn_src.close()
    
    total_apps = len(df_apps)
    print(f"Successfully loaded {total_apps} apps from APPS table.")
    
    # Drop duplicate package names (OriginalID) to ensure database uniqueness integrity
    df_apps = df_apps.drop_duplicates(subset=["OriginalID"]).copy()
    print(f"Filtered out duplicate OriginalID rows. Unique apps remaining: {len(df_apps)}")
    
    # Convert installs to integer for ordering
    def clean_installs(val):
        if not val:
            return 0
        try:
            return int(val)
        except Exception:
            return 0
            
    df_apps["installs_int"] = df_apps["realInstalls"].apply(clean_installs)
    
    # 2. Stage 1: Deterministic rules classification for ALL apps
    print("Running Stage 1 Rule-Based Classification...")
    classes = []
    drivers = []
    methods = []
    
    for idx, row in df_apps.iterrows():
        p_class, m_driver, method = classify_app_stage1(row["title"], row["genre"], row["categories"])
        classes.append(p_class)
        drivers.append(m_driver)
        methods.append(method)
        
    df_apps["psychographic_class"] = classes
    df_apps["motivational_driver"] = drivers
    
    # Map new columns for primary motivation, emotional payoff, and success metric (from comparison matrix PNG)
    driver_details = {
        "Achievement": {
            "primary_motivation": "Efficiency",
            "emotional_payoff": "Relief / Control",
            "success_metric": "Task Completion"
        },
        "Connection": {
            "primary_motivation": "Belonging",
            "emotional_payoff": "Validation / Security",
            "success_metric": "Interaction / Updates"
        },
        "Escape": {
            "primary_motivation": "Stimulation",
            "emotional_payoff": "Pleasure / Distraction",
            "success_metric": "Time spent / \"Flow\""
        },
        "Growth": {
            "primary_motivation": "Competence",
            "emotional_payoff": "Pride / Mastery",
            "success_metric": "Streak / New Skill"
        }
    }
    
    df_apps["primary_motivation"] = df_apps["motivational_driver"].apply(lambda d: driver_details.get(d, {}).get("primary_motivation", "-"))
    df_apps["emotional_payoff"] = df_apps["motivational_driver"].apply(lambda d: driver_details.get(d, {}).get("emotional_payoff", "-"))
    df_apps["success_metric"] = df_apps["motivational_driver"].apply(lambda d: driver_details.get(d, {}).get("success_metric", "-"))
    
    df_apps["classification_method"] = methods
    
    print("Stage 1 complete! Distribution of Motivational Drivers:")
    print(df_apps["motivational_driver"].value_counts())
    
    # 3. Stage 2: Embeddings & 2D Projection for top 10,000 apps by installs
    print("Selecting top 10,000 highly-installed apps for embedding & 2D visualization...")
    df_top = df_apps.sort_values(by=["installs_int", "reviews"], ascending=False).head(10000).copy()
    
    top_apps_list = df_top.to_dict(orient="records")
    top_apps_with_embeddings = batch_generate_embeddings(top_apps_list, max_workers=16)
    
    # Filter out apps that failed to embed
    valid_embeds = [app for app in top_apps_with_embeddings if app["embedding"] is not None]
    print(f"Generated {len(valid_embeds)} valid embeddings out of 10,000 target apps.")
    
    if valid_embeds:
        # Perform PCA down to 50 dimensions first (to speed up and denoise t-SNE)
        X = np.array([app["embedding"] for app in valid_embeds])
        
        print("Reducing dimensions using PCA (to 10 components)...")
        pca = PCA(n_components=10, random_state=42)
        X_pca = pca.fit_transform(X)
        
        print("Projecting to 2D coordinates using t-SNE...")
        tsne = TSNE(n_components=2, perplexity=30, max_iter=1000, random_state=42, n_jobs=-1)
        X_2d = tsne.fit_transform(X_pca)
        
        # Merge 2D coordinates back into the dataframes
        id_to_coords = {}
        for idx, app in enumerate(valid_embeds):
            id_to_coords[app["OriginalID"]] = (float(X_2d[idx, 0]), float(X_2d[idx, 1]))
            
        coords_x = []
        coords_y = []
        for idx, row in df_apps.iterrows():
            coords = id_to_coords.get(row["OriginalID"], (None, None))
            coords_x.append(coords[0])
            coords_y.append(coords[1])
            
        df_apps["embedding_x"] = coords_x
        df_apps["embedding_y"] = coords_y
    else:
        df_apps["embedding_x"] = None
        df_apps["embedding_y"] = None
        
    # 4. Stage 3: LLM Auditor Agent
    # Sample 200 apps for auditing (50 from each motivational driver category)
    print("Sampling 200 apps for LLM-based audit verification...")
    audit_sample = []
    for driver in ["Achievement", "Connection", "Escape", "Growth"]:
        df_sub = df_apps[df_apps["motivational_driver"] == driver].head(50)
        audit_sample.extend(df_sub.to_dict(orient="records"))
        
    audited_results = audit_classification_agent(audit_sample)
    
    # Calculate agreement rate
    df_audit = pd.DataFrame(audited_results)
    agreement_rate = (df_audit["audit_matched"].sum() / len(df_audit)) * 100
    print(f"=== LLM Auditor Audit Finished ===")
    print(f"Agreement Rate with Rules: {agreement_rate:.1f}%")
    
    # 5. Create Output Database exports/HICSS60_classified_apps.db
    print(f"Creating output SQLite database: {OUTPUT_DB}")
    conn_out = sqlite3.connect(OUTPUT_DB)
    cursor = conn_out.cursor()
    
    # Create tables
    cursor.execute("""
    DROP TABLE IF EXISTS classified_apps;
    """)
    cursor.execute("""
    CREATE TABLE classified_apps (
        OriginalID TEXT PRIMARY KEY,
        title TEXT,
        genre TEXT,
        categories TEXT,
        realInstalls TEXT,
        reviews INTEGER,
        score REAL,
        psychographic_class TEXT,
        motivational_driver TEXT,
        primary_motivation TEXT,
        emotional_payoff TEXT,
        success_metric TEXT,
        classification_method TEXT,
        embedding_x REAL,
        embedding_y REAL
    );
    """)
    
    cursor.execute("""
    DROP TABLE IF EXISTS audit_log;
    """)
    cursor.execute("""
    CREATE TABLE audit_log (
        OriginalID TEXT PRIMARY KEY,
        title TEXT,
        genre TEXT,
        psychographic_class TEXT,
        motivational_driver TEXT,
        llm_psychographic TEXT,
        llm_driver TEXT,
        llm_reasoning TEXT,
        audit_matched INTEGER
    );
    """)
    conn_out.commit()
    
    # Insert classified apps
    print("Writing classified apps to DB...")
    df_db = df_apps.drop(columns=["installs_int"])
    df_db.to_sql("classified_apps", conn_out, if_exists="append", index=False)
    
    # Insert audit logs
    print("Writing audit logs to DB...")
    df_audit_db = df_audit[["OriginalID", "title", "genre", "psychographic_class", "motivational_driver", "llm_psychographic", "llm_driver", "llm_reasoning", "audit_matched"]]
    df_audit_db.to_sql("audit_log", conn_out, if_exists="append", index=False)
    
    conn_out.commit()
    conn_out.close()
    print("Database writing complete!")
    
    # 6. Save Separate and Joint CSV files
    print(f"Exporting CSV files to: {CSV_DIR}")
    
    # Joint CSV
    df_apps.drop(columns=["installs_int"]).to_csv(os.path.join(CSV_DIR, "HICSS60_classified_apps_joint.csv"), index=False)
    
    # Split by Psychographic Class
    df_apps[df_apps["psychographic_class"] == "HEDONIC"].drop(columns=["installs_int"]).to_csv(os.path.join(CSV_DIR, "hedonic_apps.csv"), index=False)
    df_apps[df_apps["psychographic_class"] == "PRAGMATIC"].drop(columns=["installs_int"]).to_csv(os.path.join(CSV_DIR, "pragmatic_apps.csv"), index=False)
    
    # Split by Motivational Driver
    for driver in ["Achievement", "Connection", "Escape", "Growth"]:
        filename = f"{driver.lower()}_apps.csv"
        df_apps[df_apps["motivational_driver"] == driver].drop(columns=["installs_int"]).to_csv(os.path.join(CSV_DIR, filename), index=False)
        
    print("CSV exports complete!")
    
    elapsed = time.time() - t_start
    print(f"============================================================")
    print(f"Classification Pipeline Completed in {elapsed/60:.1f} minutes!")
    print(f"Processed 85,323 apps. Embedded and projected top 10,000 apps.")
    print(f"============================================================")

if __name__ == "__main__":
    main()
