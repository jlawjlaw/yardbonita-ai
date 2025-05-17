# upload_to_wp_db.py – YardBonita WordPress Publisher (DB Version)
# Version: v1.1.0

import os
import sqlite3
import requests
import re
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import argparse
from utils import (
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

    # 🆕 Newly added categories
    "desert-plant-spotlights": 826,
    "water-smart-landscaping": 827,
    "yard-pest-wildlife-control": 828,
    "functional-outdoor-spaces": 829,
    "tools-gear-product-reviews": 830,
    "gardening-for-beginners": 831,
    "yards-families-pets": 832,
    "sustainable-yard-living": 833,
    "extreme-weather-yard-prep": 834
}

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
    url = f"{WP_URL}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    with open(image_path, "rb") as img:
        files = {'file': (filename, img, 'image/png')}
        data = {'alt_text': alt_text}
        response = requests.post(url, headers=headers, files=files, data=data, auth=auth)

    if response.status_code == 201:
        media = response.json()
        return media["id"], media["source_url"]
    else:
        print(f"❌ Failed to upload image: {response.text}")
        return None, None

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
                new_id = r.json()["id"]
                created_ids.append(new_id)
            elif r.status_code == 400 and "term_exists" in r.text:
                try:
                    term_id = r.json()["data"]["term_id"]
                    created_ids.append(term_id)
                except:
                    print(f"⚠️ Failed to extract tag ID for '{tag}' from fallback")
            else:
                print(f"⚠️ Failed to create tag '{tag}': {r.text}")
    return created_ids

def replace_image_src(html, original_filename, new_url):
    def replacer(match):
        figure_html = match.group(0)
        updated = re.sub(
            r'(<img[^>]+src=["\'])([^"\']+)(["\'])',
            r'\1' + new_url + r'\3',
            figure_html,
            count=1,
            flags=re.IGNORECASE
        )
        return updated
    return re.sub(r'<figure>.*?</figure>', replacer, html, count=1, flags=re.DOTALL | re.IGNORECASE)

def upload_post(row, image_id=None, category_ids=None, tag_ids=None):
    post_data = {
        "title": str(row.get("post_title") or ""),
        "slug": str(row.get("slug") or ""),
        "content": str(row.get("article_html") or ""),
        "status": "publish",
        "categories": category_ids or [],
        "tags": tag_ids or [],
        "meta_input": {
            "_yoast_wpseo_title": str(row.get("seo_title") or ""),
            "_yoast_wpseo_metadesc": str(row.get("seo_description") or ""),
            "_yoast_wpseo_focuskw": str(row.get("focus_keyphrase") or "")
        }
    }

    if image_id:
        post_data["featured_media"] = image_id

    try:
        url = f"{WP_URL}/wp-json/wp/v2/posts"
        response = requests.post(url, headers=HEADERS, json=post_data, auth=auth)
        if response.status_code == 201:
            post_json = response.json()
            post_id = post_json.get("id")
            post_url = post_json.get("link")
            update_yoast_meta(
                post_id,
                post_data["meta_input"]["_yoast_wpseo_title"],
                post_data["meta_input"]["_yoast_wpseo_metadesc"],
                post_data["meta_input"]["_yoast_wpseo_focuskw"]
            )
            return post_url
        else:
            print(f"❌ Failed to upload post: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None

def update_yoast_meta(post_id, seo_title, seo_description, focus_keyphrase):
    yoast_url = f"{WP_URL}/wp-json/yardbonita/v1/yoast-meta/{post_id}"
    payload = {
        "title": seo_title,
        "metadesc": seo_description,
        "focuskw": focus_keyphrase
    }
    try:
        requests.post(yoast_url, json=payload, auth=auth)
    except Exception as e:
        print(f"❌ Exception updating Yoast meta: {e}")

def mark_as_published(uuid, url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE articles
        SET status = 'Published', published_url = ?
        WHERE uuid = ?
    """, (url, uuid))
    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Upload YardBonita articles to WordPress from SQLite DB.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    articles = get_ready_articles(limit=args.limit)

    if not articles:
        print("✅ No articles ready to upload.")
        return

    for row in articles:
        print(f"\n📄 Publishing: {row['post_title']}")

        html = enforce_intro_paragraph(row["article_html"])
        html = remove_intro_heading(html)
        html = fix_encoding_issues(html)
        html = fix_broken_emojis(html)
        row["article_html"] = html

        category_slug = (row.get("category") or "").strip().lower()
        category_id = CATEGORY_SLUG_TO_ID.get(category_slug)
        if not category_id:
            print(f"❌ ERROR: Unknown category '{category_slug}'. Skipping.")
            continue
        category_ids = [category_id]

        tags = row.get("tags", "")
        tag_ids = get_or_create_tags(tags.split(",") if tags else [])

        image_id = None
        image_url = None
        image_file = str(row.get("image_filename", "")).strip()
        if image_file:
            path = os.path.join(IMAGE_FOLDER, image_file)
            if os.path.isfile(path):
                print("🖼️ Uploading image...")
                image_id, image_url = upload_image(path, row.get("image_alt_text", ""))
                if image_url:
                    row["article_html"] = replace_image_src(row["article_html"], image_file, image_url)

        post_url = upload_post(row, image_id=image_id, category_ids=category_ids, tag_ids=tag_ids)
        if post_url:
            print(f"✅ Success: {post_url}")
            mark_as_published(row["uuid"], post_url)
        else:
            print(f"❌ Failed to post: {row['post_title']}")

if __name__ == "__main__":
    main()