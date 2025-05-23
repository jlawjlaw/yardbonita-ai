# generate_images_one.py – YardBonita Single Image Generator (DB Version)
# Version: v1.4.0 – Adds --date argument support

import os
import sqlite3
import argparse
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

    existing_files = [f for f in os.listdir(IMAGE_FOLDER) if os.path.isfile(os.path.join(IMAGE_FOLDER, f))]
    existing_basenames = {os.path.splitext(f)[0] for f in existing_files}

    new_base = base
    while new_base in existing_basenames:
        new_base = f"{base}-{counter}"
        counter += 1

    return f"{new_base}{ext}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Only process articles with this publish date (YYYY-MM-DD)")
    args = parser.parse_args()

    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    base_query = """
        SELECT uuid, post_title, image_filename, image_caption, image_alt_text
        FROM articles
        WHERE LOWER(status) IN ('draft', 'image needed')
          AND TRIM(image_filename) != ''
    """

    if args.date:
        base_query += " AND publish_date = ? ORDER BY publish_date ASC LIMIT 1"
        cursor.execute(base_query, (args.date,))
    else:
        base_query += " ORDER BY publish_date ASC LIMIT 1"
        cursor.execute(base_query)

    row = cursor.fetchone()

    if not row:
        print("✅ No images need to be generated.")
        return

    uuid, post_title, image_filename, caption, alt_text = row
    original_filename = image_filename.strip()
    expected_path = os.path.join(IMAGE_FOLDER, original_filename)

    # Check if the exact file exists AND is already assigned to this UUID
    if os.path.exists(expected_path):
        final_filename = original_filename
    else:
        final_filename = ensure_unique_filename(original_filename)

    cursor.execute("""
        UPDATE articles
        SET image_filename = ?, status = 'Ready to Upload'
        WHERE uuid = ?
    """, (final_filename, uuid))
    conn.commit()
    conn.close()

    print("\n🖼️ GLOBAL IMAGE GENERATION PROMPT:\n")
    print("You are generating blog images for YardBonita.com, a home and garden site.\n")
    print("Create a realistic, high-quality photograph of a residential yard or garden scene that visually represents the article’s theme.")
    print("The scene must look authentic to the Southeast Valley of Arizona—reflecting a dry desert climate with warm lighting, low-lush vegetation, and desert-adapted landscaping.\n")
    print("Do not include fantasy elements, over-saturated colors, cartoon-like styles, overcast skies, or non-native trees.")
    print("Do not include text, overlays, borders, whitespace, or artificial visual effects.\n")
    print("Avoid green grass lawns, unless the article specifically focuses on live lawn care topics such as natural grass maintenance, fertilization, or weed prevention. In those cases, include healthy, well-maintained natural grass appropriate for the desert Southwest.")
    print("Avoid showing wooden materials in raised beds, fences, pergolas, benches, or sheds. These features must appear only in stone, concrete, metal, or composite materials.")
    print("Do not use raised beds as the central focus unless explicitly required by the article. If shown, raised beds must appear off to the side and clearly non-wood.\n")
    print("📸 Important Visual Rules:")
    print("- Show realistic backyard features common to the region: gravel, decomposed granite, artificial turf, pavers, cool decking, or in-ground pools")
    print("- Include appropriate desert plantings such as cacti, succulents, agaves, palo verde, ocotillo, or drought-tolerant flowering shrubs")
    print("- Use authentic materials and textures typically found in suburban yards in Gilbert, Chandler, Queen Creek, and Mesa")
    print("- Avoid visual clutter; keep the scene clean, local, and natural\n")
    print("🎯 Composition & Scene Diversity Guidance:")
    print("- Vary the layout and camera angle: alternate between wide yard views, side yard strips, patios, or zoomed-in planting zones")
    print("- Emphasize different backyard features across images. Suggestions:")
    print("  • Gravel or decomposed granite paths through desert plants")
    print("  • Side-yard planting zone against a stucco wall")
    print("  • Clean patios with potted succulents or herbs")
    print("  • Front yard with tiered desert landscaping")
    print("  • Soil prep or composting areas in natural context")
    print("  • Flowering drought-tolerant shrubs in bloom\n")
    print("✅ Format Requirements:")
    print("- 1200×675px resolution (16:9 ratio)")
    print("- PNG format")
    print("- File must be named exactly as specified in the image request list\n")

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