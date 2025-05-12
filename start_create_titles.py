# === YardBonita :: start_create_titles.py :: Canonical v1.1.6 ===
# ✅ Single GPT call returns: title, category, tier
# ✅ GPT proposes its own category, then picks one from approved list
# ✅ Author assigned from approved category pool
# ✅ City mention randomized
# ✅ Seasonal wordpool + phrase deduplication
# ✅ Cliché phrase rejection with 1 retry
# ✅ Fully writes to planning.xlsx

import pandas as pd, uuid, sys, os, json, openai, random
from datetime import datetime, timedelta

# === File Paths ===
base_path = os.path.dirname(__file__)
planning_file = os.path.join(base_path, "planning.xlsx")
used_phrases_path = os.path.join(base_path, "used_phrases.json")
seasonal_word_files = {
    "winter": os.path.join(base_path, "winter.txt"),
    "spring": os.path.join(base_path, "spring.txt"),
    "summer": os.path.join(base_path, "summer.txt"),
    "fall": os.path.join(base_path, "fall.txt"),
}
cities = ["Gilbert", "Chandler", "Mesa", "Queen Creek"]
REGIONAL_INSERT_RATE = 8

# === Arguments ===
try: max_articles_per_day = int(sys.argv[1])
except: max_articles_per_day = 4
try: total_days_to_fill = int(sys.argv[2])
except: total_days_to_fill = 30

# === Load Helpers ===
def load_json(path): return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}
used_phrases = load_json(used_phrases_path)
season_words = {k: open(v, "r", encoding="utf-8").read().splitlines() if os.path.exists(v) else [] for k, v in seasonal_word_files.items()}

# === Spreadsheet ===
df = pd.read_excel(planning_file)
df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce").dt.date
today = datetime.now().date()

# === Article Planning Logic ===
filled_dates, new_rows, scanned = set(), [], 0
city_counter, check_ahead = 0, 180
current_date = today

while len(filled_dates) < total_days_to_fill and scanned < check_ahead:
    scanned += 1
    count = df[df["publish_date"] == current_date].shape[0]
    if count < max_articles_per_day:
        filled_dates.add(current_date)
        needed = max_articles_per_day - count
        for _ in range(needed):
            city = "Southeast Valley" if (len(new_rows) + city_counter) % REGIONAL_INSERT_RATE == 0 else cities[city_counter % len(cities)]
            city_counter += 1
            new_rows.append({
                "uuid": str(uuid.uuid4()), "post_title": "", "city": city, "category": "", "status": "Planned",
                "publish_date": current_date, "focus_keyphrase": "", "seo_title": "", "seo_description": "",
                "tags": "", "outline": "", "notes": "", "published_url": "", "author": "", "tier": "",
                "focus_keyword": "", "slug": "", "content": "", "image_filename": "", "image_alt": "", "image_caption": ""
            })
    current_date += timedelta(days=1)

if new_rows:
    df = pd.concat([pd.DataFrame(new_rows), df], ignore_index=True)

# === Canonical Categories + Author Pools ===
approved_categories = [
    "Lawn Care", "Irrigation & Watering", "Gardening", "Composting & Soil Health",
    "Tree & Shrub Care", "Outdoor Living", "Yard Planning & Design", "Monthly Checklists",
    "Wildlife & Pollinators", "Rain & Storm Management", "Pest Control",
    "Seasonal Decor & Lighting", "Yard Care"
]

author_pool = {
    "Lawn Care": ["Deshawn Hill", "Tina Delgado", "Derek Holt", "Marcus Wynn"],
    "Irrigation & Watering": ["Carlos Mendez", "Derek Holt", "Priya Shah", "Marcus Wynn"],
    "Gardening": ["Jamie Rivera", "Leah Tran", "Sofia Vargas", "Tina Delgado"],
    "Composting & Soil Health": ["Nina Patel", "Priya Shah", "Sofia Vargas", "Noah Redfeather"],
    "Tree & Shrub Care": ["Calvin Redd", "Rachel Gutierrez", "Tina Delgado", "Marcus Wynn"],
    "Outdoor Living": ["Ramon Ellis", "Derek Sloan", "Erin McBride", "Tasha Beaumont"],
    "Yard Planning & Design": ["Alicia Ortega", "Ramon Ellis", "Tasha Beaumont", "Jason Leung"],
    "Monthly Checklists": ["Leah Tran", "Sofia Vargas", "Jamie Rivera", "Tina Delgado"],
    "Wildlife & Pollinators": ["Maya Langston", "Rachel Gutierrez", "Priya Shah", "Nina Patel"],
    "Rain & Storm Management": ["Priya Shah", "Marcus Wynn", "Deshawn Hill", "Derek Holt"],
    "Pest Control": ["Marcus Wynn", "Carlos Mendez", "Calvin Redd"],
    "Seasonal Decor & Lighting": ["Alicia Ortega", "Erin McBride", "Tasha Beaumont", "Leah Tran"],
    "Yard Care": ["Deshawn Hill", "Tina Delgado", "Derek Holt", "Marcus Wynn"],
    "Needs Context": ["Marcus Wynn", "Priya Shah"]
}

def assign_author(category): return random.choice(author_pool.get(category, ["Marcus Wynn"]))

# === GPT Setup ===
client = openai.OpenAI()
banned_phrases = [
    "Ultimate Guide", "Top Tips", "Everything You Need", "Mastering", "Complete Guide",
    "Must-Know", "Key Tips", "Expert Advice", "All You Need", "Quick Tips"
]

system_prompt = (
    "You are a local content strategist for a seasonal home & yard website. "
    "Your job is to create a creative, SEO-viable blog title first, then shorten it to ≤75 characters. "
    "Then infer the raw category from the title and select the best match from this list:\n"
    f"{approved_categories}.\n"
    "Avoid cliché phrasing (e.g., 'Ultimate Guide', 'Top Tips'). Be specific and original. "
    "Return valid JSON: {\"title\": \"...\", \"category\": \"...\", \"tier\": \"Tier 2\"}"
)

def violates_banned(title):
    return any(p.lower() in title.lower() for p in banned_phrases)

# === Generation Loop ===
new_start_idx = len(df) - len(new_rows)
for offset, idx in enumerate(range(new_start_idx, len(df))):
    row = df.loc[idx]
    city, date = row["city"], row["publish_date"]
    season = "spring" if 3 <= date.month <= 5 else "summer" if 6 <= date.month <= 8 else "fall" if 9 <= date.month <= 11 else "winter"
    word_sample = ", ".join(random.sample(season_words[season], min(3, len(season_words[season]))))

    user_prompt = (
        f"Create a unique blog post title for a {season} yard/garden care article for homeowners in {city}. "
        f"Use inspiration like: {word_sample}. Follow instructions exactly."
    )

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.9,
                max_tokens=250
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw if raw.startswith("{") else "{}")

            title = result.get("short_title", result.get("title", f"{season.title()} Tips for {city}"))
            if violates_banned(title) and attempt == 0:
                continue  # Try once more if it violates banned phrasing

            category = result.get("category", "Needs Context")
            tier = result.get("tier", "Tier 2")
            author = assign_author(category)

            df.at[idx, "post_title"] = title
            df.at[idx, "category"] = category if category in approved_categories else "Needs Context"
            df.at[idx, "tier"] = tier
            df.at[idx, "author"] = author
            break

        except Exception as e:
            print(f"❌ GPT error on row {idx}: {e}")
            df.at[idx, "post_title"] = f"{season.title()} Tips for {city}"
            df.at[idx, "category"] = "Needs Context"
            df.at[idx, "tier"] = "Tier 2"
            df.at[idx, "author"] = "Marcus Wynn"
            break

# === Save Results ===
df.to_excel(planning_file, index=False)
print(f"✅ Canonical v1.1.6: Added {len(new_rows)} articles across {len(filled_dates)} days.")