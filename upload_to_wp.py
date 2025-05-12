# upload_to_wp.py – YardBonita WordPress Publisher
# Version: v1.0.7 (safe <img> src replacement + hardcoded category IDs + tag fallback + JSON safety)

import os
import requests
import pandas as pd
import re
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

PLANNING_PATH = "planning.xlsx"
IMAGE_FOLDER = "ai-images"

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
    "yard-planning-design": 610
}

def load_planning():
    return pd.read_excel(PLANNING_PATH, engine="openpyxl")

def save_planning(df):
    df.to_excel(PLANNING_PATH, index=False, engine="openpyxl")

def upload_image(image_path):
    url = f"{WP_URL}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/png"
    }
    with open(image_path, "rb") as img:
        response = requests.post(url, headers=headers, data=img, auth=auth)
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
            print(f"⚠️ Tag '{tag}' already exists, using term_id={existing[lower]}")
        else:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", json={"name": tag}, auth=auth)
            if r.status_code == 201:
                new_id = r.json()["id"]
                created_ids.append(new_id)
                print(f"✅ Created new tag '{tag}' with ID {new_id}")
            elif r.status_code == 400 and "term_exists" in r.text:
                try:
                    term_id = r.json()["data"]["term_id"]
                    created_ids.append(term_id)
                    print(f"⚠️ Tag '{tag}' already exists, using term_id={term_id}")
                except:
                    print(f"⚠️ Failed to extract tag ID for '{tag}' from fallback")
            else:
                print(f"⚠️ Failed to create tag '{tag}': {r.text}")
    return created_ids

def replace_image_src(html, original_filename, new_url):
    pattern = r'(<img[^>]+src=["\'])([^"\']*' + re.escape(original_filename) + r')(["\'])'
    replacement = r'\1' + new_url + r'\3'
    return re.sub(pattern, replacement, html)

def upload_post(row, image_id=None, category_ids=None, tag_ids=None):
    post_data = {
        "title": str(row.get("post_title") or ""),
        "slug": str(row.get("slug") or ""),
        "content": str(row.get("article_html") or ""),
        "status": "publish",
        "categories": category_ids or [],
        "tags": tag_ids or [],
        "meta": {
            "yoast_head_json": {
                "title": str(row.get("seo_title") or ""),
                "description": str(row.get("seo_description") or ""),
                "keywords": str(row.get("focus_keyphrase") or "")
            }
        }
    }
    try:
        url = f"{WP_URL}/wp-json/wp/v2/posts"
        
        if image_id:
            post_data["featured_media"] = image_id
    
        response = requests.post(url, headers=HEADERS, json=post_data, auth=auth)
        return response.json()["link"] if response.status_code == 201 else None
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None

def main():
    df = load_planning()
    ready = df[
        (df["status"].str.strip().str.lower() == "ready to upload") &
        (df["article_html"].notna()) & (df["post_title"].notna())
    ]

    if ready.empty:
        print("✅ No articles ready to upload.")
        return

    for idx in ready.index:
        row = df.loc[idx]
        print(f"\n📤 Publishing: {row['post_title']}")

        category_slug = str(row.get("category", "")).strip().lower()
        category_id = CATEGORY_SLUG_TO_ID.get(category_slug)
        if not category_id:
            print(f"❌ ERROR: Category slug '{category_slug}' not in hardcoded list. Skipping post.")
            df.at[idx, "status"] = "Category Error"
            continue
        category_ids = [category_id]

        tags = str(row.get("tags", "")).split(",") if row.get("tags") else []
        tag_ids = get_or_create_tags(tags)

        image_id = None
        image_url = None
        image_file = str(row.get("image_filename", "")).strip()
        if image_file:
            path = os.path.join(IMAGE_FOLDER, image_file)
            if os.path.isfile(path):
                print("🖼️ Uploading image...")
                image_id, image_url = upload_image(path)
                if image_url:
                    updated_html = replace_image_src(str(row["article_html"]), image_file, image_url)
                    df.at[idx, "article_html"] = updated_html
                    row["article_html"] = updated_html

        post_url = upload_post(row, image_id=image_id, category_ids=category_ids, tag_ids=tag_ids)
        if post_url:
            df.at[idx, "published_url"] = post_url
            df.at[idx, "status"] = "Published"
            print(f"✅ Success: {post_url}")
        else:
            df.at[idx, "status"] = "Error"
            print(f"❌ Failed to post: {row['post_title']}")

    save_planning(df)
    print("\n📁 planning.xlsx updated.")

if __name__ == "__main__":
    main()