
# generate_titles.py
# Version: v1.3.1 (Accurate GPT Batching, Clean Quote Handling, Verbose Logging)
print("🧪 THIS IS THE RIGHT SCRIPT (v1.3.1)")

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

from tier_author_utils import assign_tier_and_author

# === Setup ===
load_dotenv()
client = OpenAI()
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, help="Generate titles only for this date (YYYY-MM-DD)")
parser.add_argument("--target-count", type=int, default=10, help="How many titles should exist for that date")
args = parser.parse_args()

BASE_PROMPT = open(os.path.join(script_dir, "Title_Creation_Prompt_Unchained.txt")).read()

print("🔧 Running generate_titles.py v1.3.1 — accurate GPT batching applied.")

# === Config ===
CITIES = ["Gilbert", "Chandler", "Mesa", "Queen Creek"]
REGIONAL_INSERT_RATE = 8
GPT_BATCH_CAP = 30

FLAIR_OPTIONS = [
    "Include a playful pun or metaphor",
    "Reference local weather or desert imagery",
    "Suggest a time-based urgency",
    "Use a neighborly or casual tone",
    "Include a benefit callout (e.g., Save Water, Boost Growth)",
    "Highlight a common seasonal mistake to avoid",
    "Use alliteration for rhythm or punch",
    "Tie into a local event or cultural moment",
    "Pose a question or teaser",
    "Lead with a verb for urgency",
    "Lean into desert identity or pride",
    "Create contrast (e.g., before/after, wrong/right)"
]

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
    "Tool & Equipment Maintenance": "tool-equipment-maintenance",
    "Wildlife & Pollinators": "wildlife-pollinators",
    "Hardscaping": "hardscaping",
    "Seasonal Decor & Lighting": "seasonal-decor-lighting",
    "Yard Planning & Design": "yard-planning-design",
    "Rain & Storm Management": "rain-storm-management",
    "Yard Care": "lawn-care",
    "Needs Context": "uncategorized"
}

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

with open(os.path.join(script_dir, "category_phrases.json")) as f:
    CATEGORY_HINTS = json.load(f)

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

def pick_flair():
    n = random.choices([0, 1, 2], weights=[0.15, 0.65, 0.2])[0]
    return random.sample(FLAIR_OPTIONS, n)

def clean_quotes(text):
    return (
        text.strip()
            .strip('"')
            .strip("'")
            .replace("“", "")
            .replace("”", "")
            .replace("‘", "")
            .replace("’", "")
    )
def gpt_titles_batch(seeds_with_context):
    combined_prompt = BASE_PROMPT + "\n\n"
    approved_categories = ", ".join(CATEGORY_MAP.keys() - {"Needs Context"})
    combined_prompt += f"Choose one of the following categories for each title: {approved_categories}.\n\n"

    for seed, flair, pool in seeds_with_context:
        flair_str = f"\nFlair suggestions: {', '.join(flair)}" if flair else ""
        seasonal = f"Try to include words like: {', '.join(random.sample(pool, min(5, len(pool))))}"
        combined_prompt += f'Seed: "{seed}"\n{seasonal}{flair_str}\n\n'

    combined_prompt += "Return each title and category in this format:\n[Title] | [Category]\nOne per line. No bullet points. No extra lines."

    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0.85
    )
    lines = res.choices[0].message.content.strip().splitlines()
    return [line for line in lines if line.strip()]  # Removes blanks

# === Entry Point ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
df = pd.read_sql_query("SELECT * FROM articles", conn)
df["publish_date"] = pd.to_datetime(df["publish_date"], errors='coerce').dt.date

if args.date:
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    cursor.execute("SELECT COUNT(*) FROM articles WHERE publish_date = ?", (target_date,))
    existing_count = cursor.fetchone()[0]
    print(f"🔎 Found {existing_count} existing articles for {target_date}")

    if existing_count >= args.target_count:
        print(f"✅ Already have {existing_count} articles for {target_date}")
        conn.close()
        sys.exit(0)

    to_add = args.target_count - existing_count
    needed_rows = []
    city_counter = 0

    for _ in range(to_add):
        city = "Southeast Valley" if (len(needed_rows) + city_counter) % REGIONAL_INSERT_RATE == 0 else CITIES[city_counter % len(CITIES)]
        flair = pick_flair()
        pool = seasonal_wordpool_for(target_date)
        seedpool = seasonal_seed_for(target_date)
        seed = random.choice(seedpool)
        needed_rows.append((target_date, city, seed, flair, pool))
        city_counter += 1

else:
    if len(sys.argv) < 3:
        print("Usage: python generate_titles.py [articles_per_day] [month_number]")
        sys.exit(1)

    TARGET_PER_DAY = int(sys.argv[1])
    MONTH = int(sys.argv[2])
    today = datetime.now().date()
    year = today.year
    start = date(year, MONTH, 1)
    end = date(year, MONTH, calendar.monthrange(year, MONTH)[1])
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    needed_rows = []
    city_counter = 0

    for dt in dates:
        count = df[df["publish_date"] == dt].shape[0]
        to_add = max(0, TARGET_PER_DAY - count)
        for _ in range(to_add):
            city = "Southeast Valley" if (len(needed_rows) + city_counter) % REGIONAL_INSERT_RATE == 0 else CITIES[city_counter % len(CITIES)]
            flair = pick_flair()
            pool = seasonal_wordpool_for(dt)
            seedpool = seasonal_seed_for(dt)
            seed = random.choice(seedpool)
            needed_rows.append((dt, city, seed, flair, pool))
            city_counter += 1

    # Optional: enforce a global cap for safety
    needed_rows = needed_rows[:GPT_BATCH_CAP]

if not needed_rows:
    print("✅ No new articles needed.")
    conn.close()
    sys.exit(0)

gpt_response = gpt_titles_batch([(seed, flair, pool) for _, _, seed, flair, pool in needed_rows])

print(f"📦 GPT returned {len(gpt_response)} lines total.")
for i, line in enumerate(gpt_response):
    print(f"{i:>2}: {repr(line)}")

gpt_lines = [line.strip() for line in gpt_response if "|" in line]

assigned = 0


for i, (dt, city, seed, flair, pool) in enumerate(needed_rows):
    try:
        if i >= len(gpt_lines):
            print(f"❌ GPT response too short. Missing line {i}.")
            continue

        line = gpt_lines[i].strip()
        if "|" not in line:
            print(f"⚠️ Skipped line {i} — missing '|': {repr(line)}")
            continue

        raw_title, raw_category = map(str.strip, line.split("|", 1))
        title = clean_quotes(raw_title)
        category_name = clean_quotes(raw_category)

        if not title:
            print(f"⚠️ Skipped (empty title after cleaning): {line}")
            continue

        uuid_str = str(uuid.uuid4())
        slug = title.lower().replace(" ", "-").replace("?", "").replace(",", "").replace("'", "")
        category_slug = CATEGORY_MAP.get(category_name)
        if not category_slug:
            print(f"⚠️ Category not found in map: {category_name} → falling back to 'needs-context'")
            category_slug = "uncategorized"
        tier, author_slug = assign_tier_and_author(title, category_slug)

        print(f"🧪 Seed: {seed} | Flair: {', '.join(flair)}")
        print(f"✅ Inserting: {title} | Category: {category_name} | Tier: {tier} | Author: {author_slug} | {city}, {dt}")

        cursor.execute("""
            INSERT INTO articles (uuid, publish_date, city, status, post_title, category, slug, tier, author)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uuid_str,
            dt.isoformat(),
            city,
            "planned",
            title,
            category_slug,
            slug,
            tier,
            author_slug
        ))
        conn.commit()
        assigned += 1

    except Exception as e:
        print(f"❌ Error assigning title for index {i}: {e}")

print(f"\n✅ Inserted {assigned} articles.")
conn.close()
