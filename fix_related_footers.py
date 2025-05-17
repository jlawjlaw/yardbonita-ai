# fix_related_links.py
import sqlite3
import re

# Path to your YardBonita SQLite DB
db_path = "yardbonita.db"

# UUIDs to fix
uuids_to_fix = [
    "546ae78a-e74f-4c87-8c6b-f59bf1db6cfe", "35ddccfa-7886-4512-92fd-2d2408051acc",
    "a5c1eeae-171d-4e6f-a143-c62751943d64", "1b128c3b-52c3-4e4f-a201-f754ec72ed4f",
    "dd9764a5-3b7b-42ee-864a-677ed8cd3bcd", "0ccac6f7-3c3a-4db1-a635-33a40946af88",
    "245f9771-8092-42dc-a8d6-0475e7e744da", "12d9949e-132e-410b-b794-0594b4c7428b",
    "56ccd7fc-7e61-46cd-b874-ff24dd68e3a1", "2971c87a-050f-4126-a58d-2df2e804faab",
    "61064add-78dc-4786-b68f-398f9a9a1074", "cbdcb7fe-f500-4ec9-ae3d-ea53ba27048b",
    "aad007f3-808d-441a-af9f-3e6451cd34fc", "a9f937c7-2e50-4cc3-97c7-83ebf68f1da4",
    "4fa474dd-bce8-46fc-998d-e072223fc52f", "eaf281d0-184b-4857-9323-cebd08557211",
    "e053b16b-6542-4a3d-b197-b633945e7634", "84b370a8-ec9b-47f1-90d2-396689940b65",
    "465a4dac-fef1-4811-aaa2-17b297f9e7e5", "e6406fb6-a585-407d-a30f-dcbfcaffbf4c"
]

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Load all published titles and URLs
cursor.execute("SELECT post_title, published_url FROM published WHERE published_url IS NOT NULL")
title_url_map = dict(cursor.fetchall())

updated_count = 0

for uuid in uuids_to_fix:
    cursor.execute("SELECT article_html FROM articles WHERE uuid = ?", (uuid,))
    row = cursor.fetchone()
    if not row:
        continue

    html = row[0] or ""
    updated_html = html

    # Replace <a href="None">Title</a> with correct <a href="URL">Title</a>
    for title, url in title_url_map.items():
        pattern = rf'<a href=["\']None["\']>{re.escape(title)}</a>'
        replacement = f'<a href="{url}">{title}</a>'
        updated_html = re.sub(pattern, replacement, updated_html)

    # Only update DB if HTML changed
    if updated_html != html:
        cursor.execute("UPDATE articles SET article_html = ? WHERE uuid = ?", (updated_html, uuid))
        print(f"✅ Updated: {uuid}")
        updated_count += 1

conn.commit()
conn.close()

print(f"\n🔧 Fix complete. {updated_count} article(s) updated.")