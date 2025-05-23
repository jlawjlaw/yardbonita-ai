# generate_monthly_titles.py 
# Version: v1.0.0 (Batch 30 Cap, Monthly Mode, Safe Commits)

import pandas as pd
import sqlite3
import uuid
import random
import calendar
from datetime import datetime, timedelta, date
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

# === Setup ===
load_dotenv()
client = OpenAI()
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
BASE_PROMPT = open(os.path.join(script_dir, "Title_Creation_Prompt_Unchained.txt")).read()

# === Config ===
CITIES = ["Gilbert", "Chandler", "Mesa", "Queen Creek"]
REGIONAL_INSERT_RATE = 8
GPT_BATCH_CAP = 30

FLAIR_OPTIONS = [
    "Add an emoji to the beginning of the title",
    "Include a playful pun or metaphor",
    "Reference local weather or desert imagery",
    "Suggest a time-based urgency",
    "Use a neighborly or casual tone",
    "Include a benefit callout (e.g., Save Water, Boost Growth)"
]

def pick_flair():
    n = random.choices([0, 1, 2], weights=[0.15, 0.65, 0.2])[0]
    return random.sample(FLAIR_OPTIONS, n)

def load_pool(name):
    with open(os.path.join(script_dir, name), "r") as f:
        return [line.strip() for line in f if line.strip()]

spring_words = load_pool("spring.txt")
summer_words = load_pool("summer.txt")
fall_words = load_pool("fall.txt")
winter_words = load_pool("winter.txt")

spring_seeds = load_pool("spring_seeds.txt")
summer_seeds = load_pool("summer_seeds.txt")
fall_seeds = load_pool("fall_seeds.txt")
winter_seeds = load_pool("winter_seeds.txt")

with open(os.path.join(script_dir, "cliche_phrases.json")) as f:
    CLICHES = set(json.load(f))

with open(os.path.join(script_dir, "category_phrases.json")) as f:
    CATEGORY_HINTS = json.load(f)

CATEGORY_MAP = {
    "Gardening": "gardening",
    "Vegetable Gardening": "vegetable-gardening",
    "Landscaping": "landscaping",
    "Irrigation & Watering": "irrigation-watering",
    "Lawn Care": "lawn-care",
    "Pest Control": "pest-control",
    "Monthly Checklists": "monthly-checklists",
    "Newsletter Signup": "newsletter",
    "Composting": "composting",
    "Tree & Shrub Care": "tree-shrub-care",
    "Outdoor Living": "outdoor-living",
    "Tool & Equipment Maintenance": "tool-maintenance",
    "Wildlife & Pollinators": "wildlife-pollinators",
    "Hardscaping": "hardscaping",
    "Seasonal Decor & Lighting": "seasonal-decor-lighting",
    "Yard Planning & Design": "yard-planning-design",
    "Rain & Storm Management": "rain-storm-management",
    "Yard Care": "lawn-care",
    "Needs Context": "needs-context"
}

def seasonal_wordpool_for(dt):
    return (
        winter_words if dt.month in [12, 1, 2] else
        spring_words if dt.month in [3, 4, 5] else
        summer_words if dt.month in [6, 7, 8] else
        fall_words
    )

def seasonal_seed_for(dt):
    return (
        winter_seeds if dt.month in [12, 1, 2] else
        spring_seeds if dt.month in [3, 4, 5] else
        summer_seeds if dt.month in [6, 7, 8] else
        fall_seeds
    )

def contains_cliche(title):
    return any(phrase.lower() in title.lower() for phrase in CLICHES)

# === GPT ===
def gpt_titles_batch(seeds_with_context):
    combined_prompt = BASE_PROMPT + "\n\n"
    for i, (seed, flair, pool) in enumerate(seeds_with_context, 1):
        flair_str = f"\nFlair suggestions: {', '.join(flair)}" if flair else ""
        seasonal = f"Try to include words like: {', '.join(random.sample(pool, min(5, len(pool))))}"
        combined_prompt += f"{i}. Seed: \"{seed}\"\n{seasonal}{flair_str}\n\n"

    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0.85
    )
    return res.choices[0].message.content.strip().splitlines()

# === Main Execution ===
if len(sys.argv) < 3:
    print("Usage: python generate_monthly_titles.py [articles_per_day] [month_number]")
    sys.exit(1)

TARGET_PER_DAY = int(sys.argv[1])
MONTH = int(sys.argv[2])

today = datetime.now().date()
year = today.year
start = date(year, MONTH, 1)
end = date(year, MONTH, calendar.monthrange(year, MONTH)[1])

dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
df = pd.read_sql_query("SELECT * FROM articles", conn)
df["publish_date"] = pd.to_datetime(df["publish_date"], errors='coerce').dt.date

# === Determine Gaps ===
needed = []
city_counter = 0
for dt in dates:
    count = df[df["publish_date"] == dt].shape[0]
    to_create = max(0, TARGET_PER_DAY - count)
    for _ in range(to_create):
        city = "Southeast Valley" if (len(needed) + city_counter) % REGIONAL_INSERT_RATE == 0 else CITIES[city_counter % len(CITIES)]
        city_counter += 1
        needed.append({
            "uuid": str(uuid.uuid4()),
            "publish_date": dt,
            "city": city,
            "status": "planned",
            "post_title": None,
            "category": "",
            "slug": ""
        })

needed = needed[:GPT_BATCH_CAP]
if not needed:
    print("✅ No new rows needed.")
    sys.exit(0)

# === Write Planning Rows ===
pd.DataFrame(needed).to_sql("articles", conn, if_exists="append", index=False)

# === Build GPT Input ===
gpt_input = []
for row in needed:
    dt = row["publish_date"]
    flair = pick_flair()
    pool = seasonal_wordpool_for(dt)
    seedpool = seasonal_seed_for(dt)
    seed = random.choice(seedpool)
    gpt_input.append((seed, flair, pool))

# === GPT Call ===
print(f"🚀 Requesting {len(gpt_input)} titles from GPT...")
gpt_lines = gpt_titles_batch(gpt_input)

# === Assign Results ===
assigned = 0
for i, row in enumerate(needed):
    try:
        title = gpt_lines[i].strip().strip('"')
        if contains_cliche(title) or "|" in title:
            print(f"⚠️ Skipped (cliche or junk): {title}")
            continue

        category_name = "Needs Context"
        slug = title.lower().replace(" ", "-").replace("?", "").replace(",", "").replace("'", "")
        category_slug = CATEGORY_MAP.get(category_name, "needs-context")

        cursor.execute("""
            UPDATE articles SET post_title = ?, category = ?, slug = ? WHERE uuid = ?
        """, (title, category_slug, slug, row["uuid"]))
        conn.commit()
        print(f"✅ {row['publish_date']}: {title}")
        assigned += 1
    except Exception as e:
        print(f"❌ Error assigning title: {e}")

print(f"\n✅ Created {len(needed)} planning rows, assigned {assigned} titles.")
conn.close()