# import_missing_from_excel.py – YardBonita Planning Merge Script
# Version: v1.0.0

import os
import sqlite3
import pandas as pd

# Resolve paths safely relative to this script location
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
EXCEL_PATH = os.path.join(script_dir, "planning.xlsx")

def load_existing_uuids(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT uuid FROM articles")
    return set(row[0] for row in cursor.fetchall())

def import_missing_rows():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing_uuids = load_existing_uuids(conn)

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df = df[~df["uuid"].isin(existing_uuids)]

    if df.empty:
        print("✅ No new rows to import.")
        return

    print(f"🚀 Importing {len(df)} new rows...")

    columns = [
        'uuid', 'post_title', 'city', 'category', 'status', 'publish_date',
        'focus_keyphrase', 'seo_title', 'seo_description', 'rewrite', 'tags',
        'article_html', 'notes', 'published_url', 'author', 'tier',
        'focus_keyword', 'slug', 'content', 'image_filename', 'image_alt',
        'image_caption', 'gpt_status', 'raw_gpt_output', 'image_alt_text',
        'outline', 'rewrite_flag', 'retry_html', 'retry_word_count',
        'initial_word_count', 'rewrite_reason', 'needs_review', 'duplicate',
        'high_traffic_seasonal'
    ]

    insert_query = f"""
        INSERT INTO articles ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
    """

    for _, row in df.iterrows():
        values = [row.get(col, None) for col in columns]# import_missing_from_excel.py – YardBonita Planning Merge Script
# Version: v1.0.1 – With value cleaning for SQLite compatibility

import os
import sqlite3
import pandas as pd
from pandas import Timestamp, isna

# Resolve paths safely relative to this script location
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
EXCEL_PATH = os.path.join(script_dir, "planning.xlsx")

def clean_value(val):
    if isinstance(val, Timestamp):
        return val.strftime("%Y-%m-%d")
    if isna(val):
        return None
    return val

def load_existing_uuids(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT uuid FROM articles")
    return set(row[0] for row in cursor.fetchall())

def import_missing_rows():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing_uuids = load_existing_uuids(conn)

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df = df[~df["uuid"].isin(existing_uuids)]

    if df.empty:
        print("✅ No new rows to import.")
        return

    print(f"🚀 Importing {len(df)} new rows...")

    columns = [
        'uuid', 'post_title', 'city', 'category', 'status', 'publish_date',
        'focus_keyphrase', 'seo_title', 'seo_description', 'rewrite', 'tags',
        'article_html', 'notes', 'published_url', 'author', 'tier',
        'focus_keyword', 'slug', 'content', 'image_filename', 'image_alt',
        'image_caption', 'gpt_status', 'raw_gpt_output', 'image_alt_text',
        'outline', 'rewrite_flag', 'retry_html', 'retry_word_count',
        'initial_word_count', 'rewrite_reason', 'needs_review', 'duplicate',
        'high_traffic_seasonal'
    ]

    insert_query = f"""
        INSERT INTO articles ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
    """

    for _, row in df.iterrows():
        values = [clean_value(row.get(col, None)) for col in columns]
        cursor.execute(insert_query, values)

    conn.commit()
    conn.close()
    print("✅ Done importing new rows.")

if __name__ == "__main__":
    import_missing_rows()
   