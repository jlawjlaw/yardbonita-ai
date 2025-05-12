
import os
import json
import random
import argparse
import uuid
import re
from datetime import datetime, timedelta
import pandas as pd
import openai

# === File Paths ===
base_path = os.path.dirname(__file__)
planning_file = os.path.join(base_path, "planning.xlsx")
used_phrases_path = os.path.join(base_path, "used_phrases.json")
category_phrases_path = os.path.join(base_path, "category_phrases.json")
cliche_path = os.path.join(base_path, "cliche_phrases.json")
seasonal_word_files = {
    "winter": os.path.join(base_path, "winter.txt"),
    "spring": os.path.join(base_path, "spring.txt"),
    "summer": os.path.join(base_path, "summer.txt"),
    "fall": os.path.join(base_path, "fall.txt"),
}

TITLE_STYLE_WEIGHTS = {
    "creative_gpt": 0.60,
    "cliche": 0.10,
    "seasonal_wordpool": 0.10,
    "seo_plain": 0.10,
    "question_action": 0.10
}
cities = ["Gilbert", "Chandler", "Queen Creek", "Mesa"]

# === Load Helpers ===
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_wordpool(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

used_phrases = load_json(used_phrases_path)
category_phrases = load_json(category_phrases_path)
cliche_phrases = load_json(cliche_path)
seasonal_words_all = {k: load_wordpool(v) for k, v in seasonal_word_files.items()}

fallback_questions = [
    "Is Your Yard Ready for the Season?",
    "Want a Greener Garden?",
    "Can Your Lawn Handle the Heat?",
    "Looking to Boost Curb Appeal?",
    "Tired of a Boring Backyard?",
    "How’s Your Yard Holding Up?",
    "Refresh Your Yard Without the Stress",
    "Need a Quick Yard Upgrade?",
    "Where Should You Start This Weekend?",
    "Is Your Garden Thriving?"
]

# === GPT Title Generation ===
def gpt_generate(prompt, city):
    system_message = {
    "role": "system",
    "content": (
        "You are a blog title generator for YardBonita — a seasonal home and yard care site for the Southeast Valley of Arizona, "
        "including Gilbert, Chandler, Queen Creek, and Mesa. "
        "Titles should be emotionally engaging, creative, and relevant to the selected city. "
        "Keep each title focused on one city only — do not mention multiple cities in the same title. "
        "Avoid overusing city names unless they add value. "
        "Try to stay under 75 characters, but go a bit longer if it improves flow."
    )
}
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[system_message, {"role": "user", "content": prompt}],
            temperature=1.2,
            max_tokens=60
        )
        return response.choices[0].message.content.strip().strip('"').strip("'")
    except Exception as e:
        print(f"⚠️ GPT generation failed: {e}")
        return f"Creative Yard Tip for {city}"

def generate_title(style, season, city):
    if style == "creative_gpt":
        prompt = f"Write a creative blog title about {season} yard or garden care in {city}. Keep it under 75 characters if possible."
        return gpt_generate(prompt, city)
    if style == "cliche":
        seasonal_cliches = [p for p, meta in cliche_phrases.items() if meta.get("season") in [None, season]]
        seed = random.choice(seasonal_cliches) if seasonal_cliches else "Winter Wonderland"
        prompt = f"Write a blog title about {season} yard care in {city} using a phrase like '{seed}'. Make it creative and under 75 characters."
        return gpt_generate(prompt, city)
    if style == "seasonal_wordpool":
        word = random.choice(seasonal_words_all[season]) if seasonal_words_all[season] else "season"
        prompt = f"Write a blog title using the phrase '{word}' to describe {season} yard care in {city}. Be vivid but concise."
        return gpt_generate(prompt, city)
    if style == "seo_plain":
        category = random.choice(list(category_phrases.keys()))
        phrase = random.choice(category_phrases[category]) if category_phrases[category] else "Seasonal Tips"
        prompt = f"Write an SEO-friendly blog title about '{category}' for {city} that includes a phrase like '{phrase}'. Keep it under 75 characters."
        return gpt_generate(prompt, city)
    if style == "question_action":
        example = random.choice(fallback_questions)
        prompt = f"Write a question-style blog title for {city} about {season} yard care, similar to '{example}'."
        return gpt_generate(prompt, city)
    return gpt_generate(f"Write a creative blog title for {city} about {season} yard care.", city)

def get_season(month):
    return (
        "winter" if month in [12, 1, 2] else
        "spring" if month in [3, 4, 5] else
        "summer" if month in [6, 7, 8] else
        "fall"
    )

def find_dates_needing_titles(df, days, min_articles):
    df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce").dt.date
    today = datetime.now().date()
    date_counts = df[df["status"].str.lower() == "planned"]["publish_date"].value_counts()
    target_dates = []
    scanned = 0
    d = today
    while len(set(target_dates)) < days and scanned < 365:
        count = date_counts.get(d, 0)
        if count < min_articles:
            target_dates.extend([d] * (min_articles - count))
        d += timedelta(days=1)
        scanned += 1
    return target_dates

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("days", type=int, help="Number of underfilled days to plan")
    parser.add_argument("min_articles", type=int, nargs="?", default=4)
    args = parser.parse_args()

    df = pd.read_excel(planning_file)
    target_dates = find_dates_needing_titles(df, args.days, args.min_articles)
    if not target_dates:
        print("✅ All upcoming days have 4+ planned articles.")
        return

    styles_pool = sum([[s] * int(w * len(target_dates)) for s, w in TITLE_STYLE_WEIGHTS.items()], [])
    random.shuffle(styles_pool)

    rows = []
    titles_seen = set()
    for pub_date, style in zip(target_dates, styles_pool):
        season = get_season(pub_date.month)
        city = random.choice(cities)
        title = generate_title(style, season, city)
        clean_title = re.sub(r'[^a-zA-Z0-9 ]', '', title).strip().lower()
        if clean_title in titles_seen:
            continue
        titles_seen.add(clean_title)
        row = {
            "uuid": str(uuid.uuid4()),
            "post_title": title,
            "city": city,
            "category": "",
            "status": "Planned",
            "publish_date": pub_date
        }
        rows.append(row)

    out_df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_path = os.path.join(base_path, f"title_output_{timestamp}.xlsx")
    out_df.to_excel(out_path, index=False)
    with open(used_phrases_path, "w", encoding="utf-8") as f:
        json.dump(used_phrases, f, indent=2)
    print(f"✅ Generated {len(rows)} GPT-powered titles and saved to: {out_path}")

if __name__ == "__main__":
    main()
