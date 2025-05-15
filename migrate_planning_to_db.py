import pandas as pd
import sqlite3
import os

# Update this to your final, clean spreadsheet
PLANNING_PATH = "/Users/justinlaw/Desktop/Yardbonita/file for ai/planning.xlsx"
DB_PATH = "/Users/justinlaw/Desktop/Yardbonita/file for ai/yardbonita.db"
print("DB location:", os.path.abspath(DB_PATH))

# Load the spreadsheet
df = pd.read_excel(PLANNING_PATH, engine="openpyxl")
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

# Define required columns based on your schema
required_cols = [
    "uuid", "post_title", "slug", "category", "tier", "author", "publish_date", "outline",
    "focus_keyphrase", "seo_title", "seo_description", "image_filename", "image_alt_text",
    "image_caption", "status", "rewrite_needed", "notes"
]

# Add missing fields if needed
for col in required_cols:
    if col not in df.columns:
        df[col] = None

# Clean values for SQLite
def clean_sql_value(value, field_name=None):
    if pd.isna(value):
        return None
    if field_name == "rewrite_needed":
        return int(bool(value))
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Drop and recreate the articles table
cursor.execute("DROP TABLE IF EXISTS articles")
cursor.execute("""
CREATE TABLE articles (
    uuid TEXT PRIMARY KEY,
    post_title TEXT,
    slug TEXT,
    category TEXT,
    tier TEXT,
    author TEXT,
    publish_date TEXT,
    outline TEXT,
    focus_keyphrase TEXT,
    seo_title TEXT,
    seo_description TEXT,
    image_filename TEXT,
    image_alt_text TEXT,
    image_caption TEXT,
    status TEXT,
    rewrite_needed INTEGER,
    notes TEXT
);
""")

# Insert rows
for _, row in df.iterrows():
    values = [clean_sql_value(row.get(col), col) for col in required_cols]
    cursor.execute(f"""
        INSERT INTO articles (
            uuid, post_title, slug, category, tier, author, publish_date, outline,
            focus_keyphrase, seo_title, seo_description, image_filename, image_alt_text,
            image_caption, status, rewrite_needed, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, values)

conn.commit()
conn.close()

print(f"✅ Full migration complete: {len(df)} rows loaded into yardbonita.db")