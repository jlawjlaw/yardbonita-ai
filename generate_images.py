# generate_images_one.py – YardBonita Single Image Generator (DB Version)
# Version: v1.3.0

import os
import sqlite3
from datetime import datetime


# Resolve base path relative to this script
script_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(script_dir, "yardbonita.db")
IMAGE_FOLDER = os.path.join(script_dir, "ai-images")

def file_exists(filename):
    return os.path.isfile(os.path.join(IMAGE_FOLDER, filename))

def ensure_unique_filename(filename):
    base, ext = os.path.splitext(filename)
    counter = 2
    new_filename = filename
    while file_exists(new_filename):
        new_filename = f"{base}-{counter}{ext}"
        counter += 1
    return new_filename

def main():
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT uuid, post_title, image_filename, image_caption, image_alt_text
        FROM articles
        WHERE LOWER(status) IN ('draft', 'image needed')
          AND TRIM(image_filename) != ''
        LIMIT 1
    """)
    row = cursor.fetchone()

    if not row:
        print("✅ No images need to be generated.")
        return

    uuid, post_title, image_filename, caption, alt_text = row
    original_filename = image_filename.strip()
    final_filename = ensure_unique_filename(original_filename)

    # Update the database
    cursor.execute("""
        UPDATE articles
        SET image_filename = ?, status = 'Ready to Upload'
        WHERE uuid = ?
    """, (final_filename, uuid))
    conn.commit()
    conn.close()

    # Print image request block
    print("\n🖼️ GLOBAL IMAGE GENERATION PROMPT:\n")
    print("You are generating blog images for YardBonita.com, a home and garden site.\n")
    print("Create a realistic, high-quality photograph of a residential yard or garden scene that reflects the article's theme.")
    print("The scene must look authentic to the Southeast Valley of Arizona, capturing a dry desert climate with warm lighting, low-lush vegetation, and desert-adapted landscaping.\n")
    print("Do not include fantasy elements, over-saturated colors, cartoon-like styles, or green grass lawns, overcast skies, or non-native trees.")
    print("Avoid using wood as a construction material for elements like raised beds, fences, pergolas, benches, or sheds — these should appear only if built from stone, concrete, metal, or composite materials suitable for desert heat.\n")
    print("📸 Important Visual Rules:")
    print("- Reflect real local yard layouts (gravel, decomposed granite, cacti, succulents, native shrubs)")
    print("- Use realistic textures and desert-appropriate materials")
    print("- Never include text, overlays, or whitespace\n")
    print("✅ Format Requirements:")
    print("- 1200×675px (16:9 ratio)")
    print("- PNG format")
    print("- File must be named exactly as provided in the image request list\n")

    print("📋 IMAGE REQUEST LIST:")
    print(f" Post Title: {post_title}")
    print(f"- UUID: {uuid}")
    print(f"  Filename: {final_filename}")
    print(f"  Prompt: {caption}")
    print(f"  Alt Text: {alt_text}")
    print("\n✅ Please generate the image now.")
    print(f"✅ Saved image: {os.path.splitext(final_filename)[0]}")


if __name__ == "__main__":
    main()