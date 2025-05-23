# tier_author_utils.py

import random
import sqlite3
import os

script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")

# Simple in-memory cache
_author_pool_cache = {}

def get_author_ids_for_category(category_slug):
    """
    Fetches author slugs for a given category slug from the database.
    Uses a cache to avoid redundant DB queries.
    """
    if category_slug in _author_pool_cache:
        return _author_pool_cache[category_slug]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT authors.slug
    FROM category_author_map
    JOIN categories ON category_author_map.category_id = categories.category_id
    JOIN authors ON category_author_map.author_id = authors.author_id
    WHERE categories.slug = ?
    """
    cursor.execute(query, (category_slug,))
    result = cursor.fetchall()
    conn.close()

    author_slugs = [row[0] for row in result]
    _author_pool_cache[category_slug] = author_slugs
    return author_slugs

def assign_tier_and_author(title, category_slug):
    """
    Assign a Tier and Author based on title and category.
    Tier defaults to '1'. Author is picked from DB + cache.
    """
    tier = "1"
    author_pool = get_author_ids_for_category(category_slug)
    if not author_pool:
        author_pool = ["marcus-wynn"]
    author = random.choice(author_pool)
    return tier, author

# Optional: test run
if __name__ == "__main__":
    print(assign_tier_and_author("Best Outdoor Lighting for Summer Nights", "outdoor-living"))