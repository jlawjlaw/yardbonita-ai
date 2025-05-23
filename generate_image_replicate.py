# generate_image_replicate.py – YardBonita Replicate Image Generator
# Canonical Version: v1.0.0 with Replicate API + filename deduplication support

import os
import sqlite3
import argparse
import requests
import base64
from dotenv import load_dotenv

# === Load environment ===
load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
DB_PATH = os.path.join(os.path.dirname(__file__), "yardbonita.db")
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), "ai-images")
REPLICATE_MODEL = "ideogram-ai/ideogram-v3-turbo"

# === Ensure output folder ===
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# === Utility: Ensure filename uniqueness ===
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

# === Generate image with Replicate ===
def generate_image(prompt):
    response = requests.post(
        f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions",
        headers={
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "input": {
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "style_type": "Realistic",
                "magic_prompt_option": "Off"
            }
        }
    )
    if response.status_code != 201:
        raise RuntimeError(f"Failed to start generation: {response.text}")
    prediction = response.json()
    prediction_url = prediction.get("urls", {}).get("get")
    if not prediction_url or not prediction_url.startswith("http"):
        raise RuntimeError(f"Invalid prediction URL: {prediction_url}")

    # Poll until complete
    while True:
        poll = requests.get(prediction_url, headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"}).json()
        if poll["status"] == "succeeded":
            output = poll["output"]
            if isinstance(output, list):
                return output[0]
            return output
        elif poll["status"] == "failed":
            raise RuntimeError("Image generation failed")

# === Main function ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1, help="Number of images to generate")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT uuid, image_prompt, image_filename
        FROM articles
        WHERE LOWER(status) = 'image needed'
          AND TRIM(image_prompt) != ''
          AND TRIM(image_filename) != ''
        ORDER BY publish_date ASC
        LIMIT ?
    """, (args.limit,))

    rows = cursor.fetchall()
    if not rows:
        print("✅ No image prompts found needing generation.")
        return

    for uuid, prompt, image_filename in rows:
        print(f"\n🎯 Generating image for UUID: {uuid}\nPrompt: {prompt}\n")

        try:
            image_url = generate_image(prompt)
            img_data = requests.get(image_url).content
            filename = ensure_unique_filename(image_filename)
            save_path = os.path.join(IMAGE_FOLDER, filename)

            with open(save_path, "wb") as f:
                f.write(img_data)

            cursor.execute("""
                UPDATE articles
                SET image_filename = ?, status = 'Ready to Upload'
                WHERE uuid = ?
            """, (filename, uuid))
            conn.commit()

            print(f"✅ Image saved: {filename}")

        except Exception as e:
            print(f"❌ Failed for UUID {uuid}: {str(e)}")

    conn.close()

if __name__ == "__main__":
    main()
