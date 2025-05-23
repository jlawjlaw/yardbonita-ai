# generate_batch_articles.py – Claude Batch Submission
# Version: 4.0.0 – Prepares & submits full Claude batch from DB using utils_db

import os, json, sqlite3, datetime, smtplib, argparse, sys
import requests
import uuid
from email.message import EmailMessage
from dotenv import load_dotenv
from sqlalchemy import create_engine
import hashlib

# === Setup Paths and DB ===
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "yardbonita.db")
PROMPT_PATH = os.path.join(BASE_DIR, "canonical_prompt.txt")
LOG_PATH = os.path.join(BASE_DIR, "logs", "batch_cron.log")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
# sys.stdout = open(LOG_PATH, "a")
# sys.stderr = sys.stdout

# === Imports ===
from utils_db import get_related_articles_from_db, generate_article_and_metadata

# === Load Environment ===
load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# === Claude Batch Endpoint ===
CLAUDE_BATCH_URL = "https://api.anthropic.com/v1/messages/batches"
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# === Notify ===
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

# === Fetch Planned Articles ===
def get_planned_articles(conn, limit):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, c.slug AS category_slug
        FROM articles a
        LEFT JOIN categories c ON a.category_id = c.category_id
        WHERE LOWER(a.status) = 'planned'
          AND (a.article_html IS NULL OR TRIM(a.article_html) = '')
        ORDER BY a.publish_date ASC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    return [dict(zip(colnames, row)) for row in rows]

# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max number of articles to batch")
    args = parser.parse_args()

    print("✅ Starting script...")
    conn = sqlite3.connect(DB_PATH)
    print("✅ Connected to DB")
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with open(PROMPT_PATH, "r") as f:
        system_prompt = f.read()
    print("✅ Loaded system prompt")

    articles = get_planned_articles(conn, limit=args.limit)
    print(f"✅ Retrieved {len(articles)} planned articles")
    
    if not articles:
        print("⚠️ No planned articles found.")
        exit(0)

    batch_items = []
    batch_log = []
    for article in articles:
        try:
            print(f"🔍 Building prompt for: {article['post_title']} ({article['uuid']})")
            related = get_related_articles_from_db(
                engine,
                article["city"],
                article["category_slug"],
                article["publish_date"],
                article["post_title"]
            )

            prompts = generate_article_and_metadata(
                article_data=article,
                related_articles=related,
                system_prompt=system_prompt,
                conn=conn,
                use_claude="batch_prep_only"
            )

            if not prompts:
                print(f"⚠️ Skipped {article['uuid']} (no prompt)")
                continue

            print(f"✅ Prompt ready for: {article['uuid']}")
            
            # ✅ Mark article as "In Batch"
            cursor = conn.cursor()
            cursor.execute("UPDATE articles SET status = ? WHERE uuid = ?", ("In Batch", article["uuid"]))
            if cursor.rowcount == 0:
                print(f"❌ Could not mark article {article['uuid']} as In Batch")
            else:
                print(f"📤 Marked article {article['uuid']} as In Batch")



            # === DEBUG: Log prompt diagnostics ===
            prompt_hash = hashlib.md5(system_prompt.encode()).hexdigest()
            user_prompt_text = json.dumps(prompts["user_prompt"])

            print(f"🧠 System prompt length: {len(system_prompt)} chars")
            print(f"🧠 System prompt MD5: {prompt_hash}")
            print(f"📤 User prompt length: {len(user_prompt_text)} chars")

            print(f"📄 Prompt preview for {article['uuid']} ({article['post_title']}):")
            print(user_prompt_text[:1000] + "..." if len(user_prompt_text) > 1000 else user_prompt_text)

            # === DEBUG: Write full prompt payload to debug file ===
            os.makedirs("debug_payloads", exist_ok=True)
            debug_payload_path = os.path.join("debug_payloads", f"{article['uuid']}.json")
            debug_payload = {
                "uuid": article["uuid"],
                "title": article["post_title"],
                "system_prompt_length": len(system_prompt),
                "system_prompt_hash": prompt_hash,
                "user_prompt_length": len(user_prompt_text),
                "system": system_prompt,
                "user_prompt": prompts["user_prompt"]
            }
            with open(debug_payload_path, "w") as f:
                json.dump(debug_payload, f, indent=2)
            print(f"📝 Debug payload written to: {debug_payload_path}")

            # === Claude message format ===
            nonce = f"<!-- NONCE {uuid.uuid4()} -->"
            batch_items.append({
                "custom_id": article["uuid"],
                "params": {
                    "model": "claude-3-opus-20240229",
                    "temperature": 0.5,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": json.dumps({
                                **prompts["user_prompt"],
                                "nonce": nonce  # 👈 Now this is valid
                            })
                        }
                    ]
                }
            })
            batch_log.append(f"{article['uuid']} – {article['post_title']}")
        except Exception as e:
            print(f"❌ Error building prompt for {article['uuid']}: {e}")   
    if not batch_items:
        print("⚠️ No prompts prepared.")
        exit(0)

    payload = {"requests": batch_items}
    print(f"📤 Submitting batch of {len(batch_items)} articles to Claude...")

    res = requests.post(CLAUDE_BATCH_URL, headers=HEADERS, data=json.dumps(payload))

    if res.status_code == 200:
        # ✅ Only commit once the batch is successfully submitted
        conn.commit()
    else:
        print("❌ Error creating batch:")
        print(response.status_code)
        print(response.text)
        exit(1)

    batch_id = res.json().get("id")
    # Save batch ID for reference
    batch_id_path = os.path.join(BASE_DIR, "batch_id.txt")
    with open(batch_id_path, "w") as f:
        f.write(batch_id)
        
    print(f"📎 Saved batch ID to {batch_id_path}")
    print(f"✅ Batch submitted: {batch_id}")

    summary = f"Batch ID: {batch_id}\nSubmitted at: {datetime.datetime.now().isoformat()}\n\nUUIDs:\n" + "\n".join(batch_log)
    send_notification("🟢 Claude Batch Submitted", summary)
    print("✅ Notification sent.")

    conn.close()