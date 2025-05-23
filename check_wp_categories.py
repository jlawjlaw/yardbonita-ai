# check_wp_categories.py

import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)

def list_wp_categories():
    url = f"{WP_URL}/wp-json/wp/v2/categories?per_page=100"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
}
    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        print("\n📂 WordPress Categories:")
        for cat in response.json():
            print(f"- Name: '{cat['name']}' | Slug: '{cat['slug']}' | ID: {cat['id']}")
    else:
        print(f"❌ Failed to fetch categories: {response.status_code}\n{response.text}")
        
if __name__ == "__main__":
    list_wp_categories()