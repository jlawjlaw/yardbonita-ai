# fetch_batch_results.py – YardBonita Batch Result Fetcher & Notifier
# Canonical Version: v2.4.0 – With Fetched Batch Tracking and Duplicate Protection

import os, json, requests, sqlite3, time, argparse, smtplib
from datetime import datetime
import random
import re
from dotenv import load_dotenv
from email.message import EmailMessage
from sqlalchemy import create_engine
from utils_db import (
    get_author_persona,
    select_flair,
    get_related_articles_from_db,
    validate_and_process,
    update_article_in_db,
    unslugify
)
BASE_DIR = os.path.dirname(__file__)
# === Load Env ===
load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
DB_PATH = os.path.join(BASE_DIR, "yardbonita.db")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01"
}


def parse_claude_response(raw_text):
    """
    Extract structured fields from Claude's raw text response.
    Expected keys: TIER, FOCUS_KEYPHRASE, SEO_TITLE, SEO_DESCRIPTION,
    TAGS, ARTICLE_HTML, IMAGE_FILENAME, IMAGE_ALT_TEXT, IMAGE_CAPTION, IMAGE_PROMPT
    """
    fields = {
        "tier": None,
        "focus_keyphrase": None,
        "seo_title": None,
        "seo_description": None,
        "tags": [],
        "article_html": None,
        "image_filename": None,
        "image_alt_text": None,
        "image_caption": None,
        "image_prompt": None,
        "image_placement": "",          # Usually added in post-processing
        "flair_used": 0,
        "flair_requested": 0,
    }

    def extract(key):
        pattern = f"=={key}==\\n(.+?)(?=\\n==|\\Z)"
        match = re.search(pattern, raw_text, re.DOTALL)
        return match.group(1).strip() if match else None

    fields["tier"] = extract("TIER")
    fields["focus_keyphrase"] = extract("FOCUS_KEYPHRASE")
    fields["seo_title"] = extract("SEO_TITLE")
    fields["seo_description"] = extract("SEO_DESCRIPTION")
    fields["tags"] = extract("TAGS")
    if fields["tags"]:
        fields["tags"] = [tag.strip() for tag in fields["tags"].split(",")]

    fields["article_html"] = extract("ARTICLE_HTML")
    fields["image_filename"] = extract("IMAGE_FILENAME")
    fields["image_alt_text"] = extract("IMAGE_ALT_TEXT")
    fields["image_caption"] = extract("IMAGE_CAPTION")
    fields["image_prompt"] = extract("IMAGE_PROMPT")

    return fields

# === Send Email Notification ===
def send_notification(subject, body):
    if not NOTIFY_EMAIL:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL
    msg.set_content(body)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

# === Claude Helpers ===
def fetch_batch_status(batch_id):
    url = f"https://api.anthropic.com/v1/messages/batches/{batch_id}"
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    status = data.get("processing_status")
    print(f"📦 Status: {status}")
    return status, data.get("results_url")

def download_results(results_url, out_path="batch_results.jsonl"):
    print("⬇️ Downloading results...")
    r = requests.get(results_url, headers=HEADERS)
    with open(out_path, "w") as f:
        f.write(r.text)
    print(f"✅ Results saved to {out_path}")
    return out_path

def fetch_article_by_uuid(conn, uuid):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles WHERE uuid = ?", (uuid,))
    row = cursor.fetchone()
    if not row:
        return None
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    return dict(zip(columns, row))

# === Main Processing ===

def process_results(results_path, batch_id):
    print(f"📂 Loading batch results from {results_path}...")
    
    try:
        with open(results_path, "r") as f:
            results = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Failed to parse JSON object: {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for item in results:
        uuid = item.get("custom_id")
        if not uuid:
            print("⚠️ Skipping response with no custom_id")
            continue

        print(f"\n🧪 Raw result for {uuid}:")

        try:
            raw_text = (
                item.get("result", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
            )
        except Exception as e:
            print(f"❌ Failed to parse Claude response for {uuid}: {e}")
            continue

        if not raw_text.strip():
            print(f"⚠️ No content returned for UUID {uuid}")
            continue

        # === Confirm UUID exists in DB ===
        cursor.execute("SELECT * FROM articles WHERE uuid = ?", (uuid,))
        row = cursor.fetchone()
        if row is None:
            print(f"\n❌ ERROR: UUID {uuid} was returned by Claude but is not found in the database.")
            print("💡 Possible causes: premature fetch, DB reset, batch mismatch.")
            print("🛑 Halting batch to avoid losing data.\n")
            exit(1)

        colnames = [desc[0] for desc in cursor.description]
        article_data = dict(zip(colnames, row))

        try:
            # Recalculate full article with image + footer
            author = article_data.get("author")
            flair_list = select_flair(author, article_data, conn)
            author_bio = get_author_persona(conn, author).get("bio", "")

            # 🔄 Get category slug using category_id
            cursor.execute("""
                SELECT slug FROM categories WHERE category_id = ?
            """, (article_data.get("category_id"),))
            cat_row = cursor.fetchone()
            category_slug = cat_row[0] if cat_row else ""

            related_articles = get_related_articles_from_db(
                create_engine(f"sqlite:///{DB_PATH}"),
                city=article_data.get("city", ""),
                category=category_slug,
                publish_date=article_data.get("publish_date", ""),
                post_title=article_data.get("post_title", "")
            )

            image_instruction = (
                "after_intro" if random.random() < 0.5 else f"after_section_{random.choice([2, 3, 4])}"
            )

            parsed, word_count, tier_min = validate_and_process(
                raw_output=raw_text,
                related_articles=related_articles,
                author_bio=author_bio,
                flair_list=flair_list,
                image_instruction=image_instruction
            )

            update_article_in_db(conn, parsed, article_data)
            print(f"✅ Article {uuid} saved to DB")
        except Exception as e:
            print(f"❌ Error saving article {uuid}: {e}")

    conn.commit()
    conn.close()
    print("\n✅ All batch results processed.")
    
def poll_until_ready(batch_id, interval_sec=120):
    print(f"⏳ Polling Claude batch {batch_id} every {interval_sec} seconds...\n")
    while True:
        status, results_url = fetch_batch_status(batch_id)
        if status == "ended" and results_url:
            print("🎉 Batch completed! Fetching results...")
            return results_url
        elif status in ["expired", "canceled"]:
            print(f"❌ Batch ended with terminal status: {status}")
            return None
        print(f"🕒 Sleeping for {interval_sec} seconds...\n")
        time.sleep(interval_sec)

# === Entry Point ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", help="Claude batch ID to fetch results from")
    args = parser.parse_args()

    batch_id = args.batch_id or os.getenv("CLAUDE_BATCH_ID")

    if not batch_id:
        batch_path = os.path.join(os.path.dirname(__file__), "batch_id.txt")
        if os.path.exists(batch_path):
            with open(batch_path) as f:
                batch_id = f.read().strip()
                print(f"📎 Loaded batch ID from file: {batch_id}")

    if not batch_id:
        print("❌ Missing batch ID. Use --batch-id, set CLAUDE_BATCH_ID in .env, or ensure batch_id.txt exists.")
        exit(1)

    results_url = poll_until_ready(batch_id)
    if not results_url:
        exit(1)

    results_path = download_results(results_url)
    process_results(results_path, batch_id)