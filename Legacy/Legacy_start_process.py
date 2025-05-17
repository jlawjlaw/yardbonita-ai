
import pandas as pd
import uuid
import sys
from datetime import datetime, timedelta

# === Argument Handling ===
try:
    max_articles_per_day = int(sys.argv[1])
except (IndexError, ValueError):
    max_articles_per_day = 4  # Default

try:
    days_to_cover = int(sys.argv[2])
except (IndexError, ValueError):
    days_to_cover = 30  # Default

# === Config ===
EXCEL_FILE = "planning.xlsx"
CITIES = ["Gilbert", "Chandler", "Mesa", "Queen Creek"]
REGIONAL_INSERT_RATE = 8  # Every 8th article gets "Southeast Valley"

# === Load Spreadsheet ===
df = pd.read_excel(EXCEL_FILE)
df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce").dt.date

# === Generate Date Range ===
today = datetime.now().date()
date_range = [today + timedelta(days=i) for i in range(days_to_cover)]

# === Count Existing Articles Per Date ===
existing_counts = df["publish_date"].value_counts().to_dict()

# === Create New Rows Where Needed ===
new_rows = []
city_counter = 0

for date in date_range:
    current_count = existing_counts.get(date, 0)
    needed = max_articles_per_day - current_count
    for _ in range(needed):
        if (len(new_rows) + city_counter) % REGIONAL_INSERT_RATE == 0:
            city = "Southeast Valley"
        else:
            city = CITIES[city_counter % len(CITIES)]
            city_counter += 1

        new_rows.append({
            "uuid": str(uuid.uuid4()),
            "post_title": "",
            "city": city,
            "category": "",
            "status": "Planned",
            "publish_date": date,
            "focus_keyphrase": "",
            "seo_title": "",
            "seo_description": "",
            "tags": "",
            "outline": "",
            "notes": "",
            "published_url": "",
            "author": "",
            "tier": "",
            "focus_keyword": "",
            "slug": "",
            "content": "",
            "image_filename": "",
            "image_alt": "",
            "image_caption": ""
        })

# === Append and Save ===
if new_rows:
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Added {len(new_rows)} new row(s) to {EXCEL_FILE}.")
else:
    print("✅ All dates already have sufficient articles. No rows added.")
