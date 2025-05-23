
import sqlite3
import re
from utils_db import get_author_persona, get_related_articles_from_db, build_article_footer

DB_PATH = "yardbonita.db"

def has_author_bio(html):
    return '<div class="author-byline">' in html

def fetch_articles_missing_bio(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM articles
        WHERE article_html IS NOT NULL
        AND TRIM(article_html) != ''
        AND LOWER(status) = 'image needed'
    """)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows if not has_author_bio(row[columns.index("article_html")])]

def patch_missing_bios():
    conn = sqlite3.connect(DB_PATH)
    engine = None
    try:
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{DB_PATH}")
    except:
        print("⚠️ Could not load SQLAlchemy engine for related articles.")

    articles = fetch_articles_missing_bio(conn)
    print(f"🔍 Found {len(articles)} articles missing author bio.")

    for article in articles:
        print(f"🛠 Patching article: {article['post_title']} ({article['uuid']})")
        author = article.get("author", "")
        persona = get_author_persona(conn, author)
        bio = persona.get("bio", "").strip()

        if not bio:
            print(f"⚠️ No bio found for author: {author}")
            continue

        related = []
        if engine:
            try:
                related = get_related_articles_from_db(engine, article["city"], article["category"], article["publish_date"], article["post_title"])
            except Exception as e:
                print(f"⚠️ Failed to fetch related articles: {e}")

        new_footer = build_article_footer(related, bio)
        html = article["article_html"].strip()

        if new_footer:
            html += "\n\n" + new_footer

        cursor = conn.cursor()
        cursor.execute("UPDATE articles SET article_html = ? WHERE uuid = ?", (html, article["uuid"]))
        conn.commit()
        print(f"✅ Updated article {article['uuid']}")

    conn.close()
    print("🏁 Done.")

if __name__ == "__main__":
    patch_missing_bios()
