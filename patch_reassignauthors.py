import sqlite3
import random
from tier_author_utils import CATEGORY_AUTHOR_POOLS

DB_PATH = "yardbonita.db"

def normalize_author_names(conn):
    print("🔧 Converting 'Marcus Wynn' to 'marcus-wynn'...")
    conn.execute("""
        UPDATE articles
        SET author = 'marcus-wynn'
        WHERE LOWER(author) = 'marcus wynn'
    """)
    conn.commit()

def reassign_uncategorized_authors(conn):
    print("🔄 Reassigning authors for uncategorized articles...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT uuid, category FROM articles
        WHERE category = 'uncategorized'
    """)
    articles = cursor.fetchall()
    updated = 0

    for uuid, category in articles:
        possible_authors = CATEGORY_AUTHOR_POOLS.get(category, [])
        if not possible_authors:
            continue
        new_author = random.choice(possible_authors)
        cursor.execute("UPDATE articles SET author = ? WHERE uuid = ?", (new_author, uuid))
        updated += 1

    conn.commit()
    print(f"✅ Reassigned {updated} articles with uncategorized category.")

def main():
    conn = sqlite3.connect(DB_PATH)
    normalize_author_names(conn)
    reassign_uncategorized_authors(conn)
    conn.close()
    print("🏁 Done.")

if __name__ == "__main__":
    main()