# upload_to_wp_db.py – YardBonita WordPress Publisher (DB Version)
# Version: v1.2.0 – uses author table for correct capitalization

import os
import sqlite3
import requests
import re
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import argparse
from utils_db import (
    enforce_intro_paragraph,
    remove_intro_heading,
    fix_encoding_issues,
    fix_broken_emojis
)

# Paths
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
IMAGE_FOLDER = os.path.join(script_dir, "ai-images")

# Load .env
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
HEADERS = {"Content-Type": "application/json"}

CATEGORY_SLUG_TO_ID = {
    "composting": 582,
    "gardening": 676,
    "hardscaping": 602,
    "irrigation-watering": 679,
    "landscaping": 678,
    "lawn-care": 680,
    "monthly-checklists": 682,
    "newsletter-signup": 683,
    "outdoor-living": 590,
    "pest-control": 681,
    "rain-storm-management": 614,
    "seasonal-decor-lighting": 606,
    "tool-equipment-maintenance": 594,
    "tree-shrub-care": 586,
    "vegetable-gardening": 677,
    "wildlife-pollinators": 598,
    "yard-planning-design": 610,
    "desert-plant-spotlights": 826,
    "water-smart-landscaping": 827,
    "yard-pest-wildlife-control": 828,
    "functional-outdoor-spaces": 829,
    "tools-gear-product-reviews": 830,
    "gardening-for-beginners": 831,
    "yards-families-pets": 832,
    "sustainable-yard-living": 833,
    "extreme-weather-yard-prep": 834,
    "uncategorized": 1,
}

def load_authors():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT slug, author FROM authors")
    authors = {slug: author for slug, author in cursor.fetchall()}
    conn.close()
    return authors

def slug_to_name(slug):
    return ' '.join(part.capitalize() for part in slug.replace('-', ' ').split())

def get_ready_articles(limit=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT * FROM articles
        WHERE LOWER(status) = 'ready to upload'
          AND TRIM(article_html) != ''
          AND TRIM(post_title) != ''
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(colnames, row)) for row in rows]

def upload_image(image_path, alt_text=""):
    if image_path.lower().endswith(".png"):
        jpg_path = image_path.replace(".png", ".jpg")
        print(f"🔁 Converting PNG to JPG: {jpg_path}")
        convert_result = os.system(f'sips -s format jpeg "{image_path}" --out "{jpg_path}"')
        if convert_result == 0 and os.path.isfile(jpg_path):
            print(f"🩹 Deleting original PNG: {image_path}")
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"⚠️ Failed to delete original PNG: {e}")
            image_path = jpg_path
        else:
            print("❌ Failed to convert image to JPG. Skipping upload.")
            return None, None, None

    url = f"{WP_URL}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    try:
        with open(image_path, "rb") as img:
            mime_type = 'image/jpeg' if filename.lower().endswith(".jpg") else 'image/png'
            files = {'file': (filename, img, mime_type)}
            data = {'alt_text': alt_text}
            response = requests.post(url, headers=headers, files=files, data=data, auth=auth)

        if response.status_code == 201:
            media = response.json()
            return media["id"], media["source_url"], filename
        else:
            print(f"❌ Failed to upload image: {response.text}")
            return None, None, None
    except Exception as e:
        print(f"❌ Exception during image upload: {e}")
        return None, None, None

def get_or_create_tags(tag_list):
    existing = {}
    created_ids = []
    response = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?per_page=100", auth=auth)
    if response.status_code == 200:
        for tag in response.json():
            existing[tag["name"].lower()] = tag["id"]
    for tag in tag_list:
        tag = tag.strip()
        lower = tag.lower()
        if lower in existing:
            created_ids.append(existing[lower])
        else:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", json={"name": tag}, auth=auth)
            if r.status_code == 201:
                created_ids.append(r.json()["id"])
            elif r.status_code == 400 and "term_exists" in r.text:
                try:
                    created_ids.append(r.json()["data"]["term_id"])
                except:
                    print(f"⚠️ Failed to extract tag ID for '{tag}'")
            else:
                print(f"⚠️ Failed to create tag '{tag}': {r.text}")
    return created_ids

def replace_image_src(html, original_filename, new_url):
    pattern = re.compile(rf'(<img[^>]+src=["\'][^"\']*{re.escape(original_filename)}[^"\']*["\'])', re.IGNORECASE)
    def replacer(match):
        tag = match.group(0)
        return re.sub(r'(src=["\'])([^"\']+)(["\'])', rf'\1{new_url}\3', tag, count=1)
    return pattern.sub(replacer, html, count=1)

def upload_post(row, author_lookup, image_id=None, category_ids=None, tag_ids=None):
    author_slug = str(row.get("author") or "").strip()
    author_name = author_lookup.get(author_slug, slug_to_name(author_slug))
    post_data = {
        "title": str(row.get("post_title") or ""),
        "slug": str(row.get("slug") or ""),
        "content": str(row.get("article_html") or ""),
        "status": "publish",
        "categories": category_ids or [],
        "tags": tag_ids or [],
        "meta": {
            "custom_author": author_name,
            "tier": str(row.get("tier") or "")
        },
        "meta_input": {
            "_yoast_wpseo_title": str(row.get("seo_title") or ""),
            "_yoast_wpseo_metadesc": str(row.get("seo_description") or ""),
            "_yoast_wpseo_focuskw": str(row.get("focus_keyphrase") or "")
        }
    }
    if image_id:
        post_data["featured_media"] = image_id

    try:
        print("\ud83d\udce4 Sending post data:", json.dumps(post_data, indent=2, ensure_ascii=False))
    except UnicodeEncodeError:
        print("⚠️ Post data includes invalid Unicode. Skipping print preview.")

        url = f"{WP_URL}/wp-json/wp/v2/posts"
        response = requests.post(url, headers=HEADERS, json=post_data, auth=auth)
        if response.status_code == 201:
            post_json = response.json()
            update_yoast_meta(post_json.get("id"), post_data["meta_input"]["_yoast_wpseo_title"], post_data["meta_input"]["_yoast_wpseo_metadesc"], post_data["meta_input"]["_yoast_wpseo_focuskw"])
            return post_json.get("link")
        else:
            print(f"❌ Failed to upload post: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None

def update_yoast_meta(post_id, seo_title, seo_description, focus_keyphrase):
    try:
        requests.post(f"{WP_URL}/wp-json/yardbonita/v1/yoast-meta/{post_id}", json={
            "title": seo_title,
            "metadesc": seo_description,
            "focuskw": focus_keyphrase
        }, auth=auth)
    except Exception as e:
        print(f"❌ Exception updating Yoast meta: {e}")

def mark_as_published(uuid):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE articles
        SET status = 'Published'
        WHERE uuid = ?
    """, (uuid,))
    conn.commit()
    conn.close()

def update_article_image_filename(uuid, new_filename):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE articles SET image_filename = ? WHERE uuid = ?", (new_filename, uuid))
    conn.commit()
    conn.close()

def insert_into_published(conn, row):
    cursor = conn.cursor()
    fields = ['uuid', 'post_title', 'city', 'category', 'publish_date', 'published_url', 'author', 'tier', 'seo_title', 'seo_description', 'focus_keyphrase', 'tags', 'slug']
    values = tuple(row.get(field, "") for field in fields)
    cursor.execute(f"INSERT OR IGNORE INTO published ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})", values)
    conn.commit()
    return cursor.rowcount

def main():
    parser = argparse.ArgumentParser(description="Upload YardBonita articles to WordPress from SQLite DB.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    authors = load_authors()
    articles = get_ready_articles(limit=args.limit)
    if not articles:
        print("✅ No articles ready to upload.")
        return

    for row in articles:
        print(f"\n📄 Publishing: {row['post_title']}")
        html = fix_broken_emojis(fix_encoding_issues(remove_intro_heading(enforce_intro_paragraph(row["article_html"]))))
        row["article_html"] = html

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get category slug from category_id
        cursor.execute("SELECT slug FROM categories WHERE category_id = ?", (row.get("category_id"),))
        cat_row = cursor.fetchone()
        if not cat_row:
            print(f"❌ ERROR: Unknown category_id '{row.get('category_id')}'. Skipping.")
            conn.close()
            continue

        cat_slug = cat_row[0].strip().lower()
        cat_id = CATEGORY_SLUG_TO_ID.get(cat_slug)
        if not cat_id:
            print(f"❌ ERROR: Category slug '{cat_slug}' not mapped to WP ID. Skipping.")
            conn.close()
            continue

        tag_ids = get_or_create_tags(row.get("tags", "").split(",") if row.get("tags") else [])

        image_id, image_url, updated_filename = None, None, None
        img_file = str(row.get("image_filename", "")).strip()
        if img_file:
            path = os.path.join(IMAGE_FOLDER, img_file)
            if os.path.isfile(path):
                print("🖼️ Uploading image...")
                image_id, image_url, updated_filename = upload_image(path, row.get("image_alt_text", ""))
                if image_url:
                    row["article_html"] = replace_image_src(row["article_html"], img_file, image_url)
                    if updated_filename and updated_filename != img_file:
                        row["image_filename"] = updated_filename
                        update_article_image_filename(row["uuid"], updated_filename)

        post_url = upload_post(row, authors, image_id=image_id, category_ids=[cat_id], tag_ids=tag_ids)
        if post_url:
            print(f"✅ Success: {post_url}")
            mark_as_published(row["uuid"])
            row["published_url"] = post_url  # ✅ For use in insert_into_published()

        conn = sqlite3.connect(DB_PATH)
        insert_into_published(conn, row)
        conn.close()

if __name__ == "__main__":
    main()
