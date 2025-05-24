# fetch_batch_titles_claude.py
# Version: 1.1.1 – Improved slug sanitization and fallback safety

import os, json, sqlite3, argparse, re
import requests
from datetime import datetime
from dotenv import load_dotenv
from tier_author_utils import assign_tier_and_author

# === Setup ===
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "yardbonita.db")
BATCH_ID_PATH = os.path.join(BASE_DIR, "batch_id.txt")
RESPONSES_PATH = os.path.join(BASE_DIR, "batch_responses")
os.makedirs(RESPONSES_PATH, exist_ok=True)

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")

CLAUDE_RESULTS_URL = "https://api.anthropic.com/v1/messages/batches/{}"
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# === Fetch Batch ===
def fetch_batch_results(batch_id):
    url = CLAUDE_RESULTS_URL.format(batch_id)
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Failed to fetch batch: {res.status_code}")
        print(res.text)
        return None
    return res.json()

# === Store Titles in DB ===
def parse_and_store(results):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0

    for item in results.get("requests", []):
        uuid = item.get("custom_id")
        output = item.get("response", {}).get("content")
        if not uuid or not output:
            print(f"⚠️ Skipping empty result for {uuid}")
            continue

        # Extract title and category
        lines = [line.strip() for line in output.split("\n") if "|" in line]
        if not lines:
            print(f"⚠️ No valid title|category line found for {uuid}")
            continue

        title, category_name = map(str.strip, lines[0].split("|", 1))
        slug = title.lower().replace(" ", "-").replace("?", "").replace(",", "").replace("'", "")
        slug = re.sub(r'[^a-z0-9-]', '', slug)  # strip non-alphanumerics except hyphens
        slug = re.sub(r'-+', '-', slug).strip('-')  # normalize multiple hyphens

        category_slug = category_name.lower().replace(" ", "-")
        category_slug = re.sub(r'[^a-z0-9-]', '', category_slug)

        # 🔥 Assign tier and author based on category
        tier, author = assign_tier_and_author(title, category_slug)

        # Safety fallback
        if not category_slug:
            category_slug = "uncategorized"
        if not author:
            author = "marcus-wynn"

        print(f"✅ Updating {uuid} with: {title} | {category_name} | Tier: {tier} | Author: {author}")

        cursor.execute("""
            UPDATE articles
            SET post_title = ?, slug = ?, category = ?, tier = ?, author = ?, status = 'titled'
            WHERE uuid = ?
        """, (title, slug, category_slug, tier, author, uuid))

        inserted += 1

        # Save response for debug
        with open(os.path.join(RESPONSES_PATH, f"{uuid}.txt"), "w") as f:
            f.write(output)

    conn.commit()
    conn.close()
    print(f"✅ Parsed and updated {inserted} articles.")

# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", type=str, help="Override batch ID")
    args = parser.parse_args()

    if args.batch_id:
        batch_id = args.batch_id
    elif os.path.exists(BATCH_ID_PATH):
        with open(BATCH_ID_PATH, "r") as f:
            batch_id = f.read().strip()
    else:
        print("❌ No batch ID found")
        exit(1)

    print(f"📥 Fetching batch results for ID: {batch_id}")
    results = fetch_batch_results(batch_id)
    if results:
        parse_and_store(results)