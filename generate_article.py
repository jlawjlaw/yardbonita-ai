# generate_article.py – YardBonita Article Generator Entry Point (DB Version)
# Version: v2.0.1 – Full SQLite Transition, utils_db integrated

import os, argparse, datetime, sqlite3
import pandas as pd
from sqlalchemy import create_engine
from utils_db import (
    get_author_persona,
    get_related_articles_from_db,
    generate_article_and_metadata,
    update_article_in_db
)

# === Paths ===
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
PERSONA_PATH = os.path.join(script_dir, "YardBonita_Author_Personas.xlsx")
PROMPT_PATH = os.path.join(script_dir, "canonical_prompt.txt")

def get_articles_to_process(conn, mode, count=None):
    cursor = conn.cursor()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if mode == "all_today":
        cursor.execute("""
            SELECT rowid, * FROM articles
            WHERE LOWER(status) = 'planned'
              AND publish_date = ?
              AND (article_html IS NULL OR TRIM(article_html) = '')
        """, (today_str,))
    elif mode == "create":
        cursor.execute("""
            SELECT rowid, * FROM articles
            WHERE LOWER(status) = 'planned'
              AND (article_html IS NULL OR TRIM(article_html) = '')
            LIMIT ?
        """, (count,))
    else:
        cursor.execute("""
            SELECT rowid, * FROM articles
            WHERE LOWER(status) = 'planned'
              AND (article_html IS NULL OR TRIM(article_html) = '')
            LIMIT 1
        """)
    return cursor.fetchall()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all_today", action="store_true", help="Generate all articles scheduled for today")
    parser.add_argument("--create", type=int, help="Number of articles to create regardless of publish date")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(DB_PATH)
        engine = create_engine(f"sqlite:///{DB_PATH}")
        persona_df = pd.read_excel(PERSONA_PATH, engine="openpyxl")
        with open(PROMPT_PATH, "r") as f:
            system_prompt = f.read()
    except Exception as e:
        print(f"❌ Failed to load required files: {e}")
        return

    mode = "all_today" if args.all_today else "create" if args.create else "single"
    count = args.create if args.create else None
    rows = get_articles_to_process(conn, mode, count)

    if not rows:
        print("⚠️ No eligible articles found.")
        return

    for row in rows:
        rowid = row[0]
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(articles)")
        columns = [col[1] for col in cursor.fetchall()]
        data = dict(zip(columns, row[1:]))

        try:
            related = get_related_articles_from_db(
                engine,
                data.get("city", ""),
                data.get("category", ""),
                data.get("publish_date", ""),
                data.get("post_title", "")
            )
            data["related_articles"] = related

            gpt_output = generate_article_and_metadata(
                data, persona_df, None, related, system_prompt
            )

            if not gpt_output:
                print("📉 GPT returned nothing. Flagging for rewrite.")
                update_article_in_db(conn, rowid, {
                    "status": "Draft",
                    "rewrite": "yes",
                    "notes": f"GPT failed to meet tier {data['tier']} minimum",
                    "article_html": "",
                    "focus_keyphrase": "",
                    "seo_title": "",
                    "seo_description": "",
                    "tags": ""
                }, data)
                continue

            if gpt_output.get("rewrite") == "yes":
                print(f"🟨 Short article flagged — {gpt_output['word_count']} words")

            for field in ["focus_keyphrase", "seo_title", "seo_description", "tags"]:
                print(f"  - {field}: {gpt_output.get(field, '')}")

            update_article_in_db(conn, rowid, gpt_output, data)

            print(f"✅ Written: {data['post_title']} scheduled for {data['publish_date']}")

        except Exception as e:
            print(f"❌ Error processing {data.get('uuid', 'unknown')}: {e}")

    conn.close()

if __name__ == "__main__":
    main()