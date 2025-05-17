import pandas as pd
import sqlite3
import os

# === Paths ===
DB_PATH = "/Users/justinlaw/Desktop/Yardbonita/file for ai/yardbonita.db"
SPREADSHEET_PATH = "/Users/justinlaw/Desktop/Yardbonita/file for ai/planning.xlsx"

# === Load city data from Excel ===
df = pd.read_excel(SPREADSHEET_PATH, engine="openpyxl")
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

if "uuid" not in df.columns or "city" not in df.columns:
    raise Exception("❌ Spreadsheet must contain both 'uuid' and 'city' columns.")

uuid_to_city = {
    row["uuid"]: row["city"]
    for _, row in df.iterrows()
    if pd.notna(row["city"])
}

print(f"🔍 Prepared to update {len(uuid_to_city)} rows with city data.")

# === Connect to SQLite and update city values ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

updated = 0
for uuid, city in uuid_to_city.items():
    cursor.execute("UPDATE articles SET city = ? WHERE uuid = ?", (city, uuid))
    updated += cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Restored city values for {updated} rows in {DB_PATH}.")