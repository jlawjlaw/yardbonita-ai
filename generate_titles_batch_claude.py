# generate_titles_batch_claude.py
# Version: 1.4.0 – Adds month-based bulk generation with cap and year logic (no pandas)

import sqlite3
import uuid
import random
import calendar
from datetime import datetime, timedelta, date
import os
import sys
import json
from dotenv import load_dotenv
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from tier_author_utils import assign_tier_and_author
import argparse

print("🧪 Claude Title Generator (v1.4.0) with month & limit support")

# === Setup ===
load_dotenv()
client = Anthropic()
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
BASE_PROMPT = open(os.path.join(script_dir, "Title_Creation_Prompt_Unchained.txt")).read()

# === Config ===
CITIES = ["Gilbert", "Chandler", "Mesa", "Queen Creek"]
REGIONAL_INSERT_RATE = 8
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

CATEGORY_MAP = json.load(open(os.path.join(script_dir, "category_phrases.json")))
CATEGORY_MAP["Needs Context"] = "uncategorized"

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
    return text.strip().strip('"').strip("'").replace("“", "").replace("”", "").replace("‘", "").replace("’", "")

def gpt_titles_batch(seeds_with_context):
    combined_prompt = BASE_PROMPT + "\n\n"
    approved_categories = ", ".join([k for k in CATEGORY_MAP if k != "Needs Context"])
    combined_prompt += f"Choose one of the following categories for each title: {approved_categories}.\n\n"

    for seed, flair, pool in seeds_with_context:
        flair_str = f"\nFlair suggestions: {', '.join(flair)}" if flair else ""
        seasonal = f"Try to include words like: {', '.join(random.sample(pool, min(5, len(pool))))}"
        combined_prompt += f'Seed: "{seed}"\n{seasonal}{flair_str}\n\n'

    combined_prompt += "\nReturn each title and category in this format:\n[Title] | [Category]\nOne per line. No bullet points. No extra lines."
    full_prompt = f"{HUMAN_PROMPT} {combined_prompt}\n{AI_PROMPT}"

    response = client.completions.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        temperature=0.85,
        prompt=full_prompt
    )
    return [line.strip() for line in response.completion.strip().splitlines() if line.strip()]

# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int, required=True, help="Month number (1–12)")
    parser.add_argument("--per-day", type=int, required=True, help="Target number of titles per day")
    parser.add_argument("--limit", type=int, default=30, help="Total cap for new titles")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.now().date()
    year = today.year if args.month >= today.month else today.year + 1
    start = date(year, args.month, 1)
    end = date(year, args.month, calendar.monthrange(year, args.month)[1])
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    needed_rows = []
    city_counter = 0

    for dt in dates:
        cursor.execute("SELECT COUNT(*) FROM articles WHERE publish_date = ?", (dt.isoformat(),))
        existing_count = cursor.fetchone()[0]
        to_add = max(0, args.per_day - existing_count)

        for _ in range(to_add):
            city = "Southeast Valley" if (len(needed_rows) + city_counter) % REGIONAL_INSERT_RATE == 0 else CITIES[city_counter % len(CITIES)]
            flair = pick_flair()
            pool = seasonal_wordpool_for(dt)
            seedpool = seasonal_seed_for(dt)
            seed = random.choice(seedpool)
            needed_rows.append((dt, city, seed, flair, pool))
            city_counter += 1

    needed_rows = needed_rows[:args.limit]  # enforce limit

    if not needed_rows:
        print("✅ No new articles needed.")
        conn.close()
        sys.exit(0)

    gpt_response = gpt_titles_batch([(seed, flair, pool) for _, _, seed, flair, pool in needed_rows])
    print(f"📦 Claude returned {len(gpt_response)} lines total.")

    gpt_lines = [line for line in gpt_response if "|" in line]
    assigned = 0

    for i, (dt, city, seed, flair, pool) in enumerate(needed_rows):
        if i >= len(gpt_lines):
            print(f"❌ GPT response too short. Missing line {i}.")
            continue
        try:
            raw_title, raw_category = map(str.strip, gpt_lines[i].split("|", 1))
            title = clean_quotes(raw_title)
            category_name = clean_quotes(raw_category)
            slug = title.lower().replace(" ", "-").replace("?", "").replace(",", "").replace("'", "")
            category_slug = CATEGORY_MAP.get(category_name, "uncategorized")
            tier, author_slug = assign_tier_and_author(title, category_slug)

            uuid_str = str(uuid.uuid4())
            print(f"✅ Inserting: {title} | {category_name} | Tier {tier} | Author {author_slug}")
            cursor.execute("""
                INSERT INTO articles (uuid, publish_date, city, status, post_title, category, slug, tier, author)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uuid_str, dt.isoformat(), city, "planned", title, category_slug, slug, tier, author_slug))
            conn.commit()
            assigned += 1
        except Exception as e:
            print(f"❌ Error on row {i}: {e}")

    conn.close()
    print(f"🎯 {assigned} new articles inserted.")