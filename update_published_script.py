import sys
import pandas as pd
import os

# === Usage Check ===
if len(sys.argv) != 7:
    print("❌ Usage: python3 update_published_script.py \"uuid\" \"post_title\" \"city\" \"category\" \"author\" \"publish_date\"")
    sys.exit(1)

# === Parse Arguments ===
uuid = sys.argv[1]
post_title = sys.argv[2]
city = sys.argv[3]
category = sys.argv[4]
author = sys.argv[5]
publish_date = sys.argv[6]

# === Slug Conversion Helpers ===
def slugify(text):
    return text.lower().replace(" ", "-")

if "San Diego" in city:
    city_slug = slugify(city) + "-ca"
elif "Bellevue" in city:
    city_slug = slugify(city) + "-wa"
elif "Atlanta" in city:
    city_slug = slugify(city) + "-ga"
elif "Gilbert" in city:
    city_slug = slugify(city) + "-az"
else:
    city_slug = slugify(city)

category_slug = slugify(category) + "-" + city_slug
post_slug = slugify(post_title)

# === Build Published URL ===
published_url = f"https://yardbonita.com/{city_slug}/{category_slug}/{post_slug}/"

# === FILE PATH ===
published_file = "/Users/justinlaw/Desktop/Yardbonita/file for ai/published.xlsx"

# === LOAD EXISTING DATA ===
if not os.path.exists(published_file):
    print(f"❌ Error: File not found at {published_file}")
    sys.exit(1)

try:
    df = pd.read_excel(published_file)
except Exception as e:
    print(f"❌ Failed to read Excel file: {e}")
    sys.exit(1)

# === CREATE NEW ROW ===
new_row = {
    "uuid": uuid,
    "post_title": post_title,
    "city": city,
    "category": category,
    "author": author,
    "publish_date": publish_date,
    "published_url": published_url
}

# === APPEND NEW ROW ===
try:
    df.loc[len(df)] = new_row
except Exception as e:
    print(f"❌ Failed to append new row: {e}")
    sys.exit(1)

# === SAVE FILE ===
try:
    df.to_excel(published_file, index=False)
except Exception as e:
    print(f"❌ Failed to save Excel file: {e}")
    sys.exit(1)

print("✅ published.xlsx updated with:")
print(new_row)