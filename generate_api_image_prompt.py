# generate_api_image_prompt.py – YardBonita API Prompt Extractor & Caller
# Version: v1.1.0

import pandas as pd
import argparse
import openai
import os

PLANNING_PATH = "planning.xlsx"
openai.api_key = os.getenv("OPENAI_API_KEY")

def safe_str(val):
    return str(val).strip() if pd.notna(val) else ""

def main():
    parser = argparse.ArgumentParser(description="Generate DALL·E image prompt and call API using row offset.")
    parser.add_argument("--offset", type=int, default=0, help="Row offset to extract")
    args = parser.parse_args()

    df = pd.read_excel(PLANNING_PATH, engine="openpyxl")
    if args.offset < 0 or args.offset >= len(df):
        print(f"❌ Invalid offset: {args.offset}")
        return

    row = df.iloc[args.offset]
    title = safe_str(row.get("post_title"))
    filename = safe_str(row.get("image_filename"))
    caption = safe_str(row.get("image_caption"))
    alt_text = safe_str(row.get("image_alt_text"))
    category = safe_str(row.get("category"))

    if not filename:
        print(f"❌ Skipping row {args.offset} — Missing image filename.")
        return

    print("\n🖼️ Image Generation Prompt:\n")
    print(f"Photorealistic image for a YardBonita.com blog titled “{title}”.")
    print("Scene shows a realistic residential yard or garden in the Southeast Valley of Arizona — desert climate, warm lighting, low-lush vegetation.")
    print("Avoid fantasy elements, green lawns, or non-native trees.")
    print("This image must look like a real editorial photograph, not a render or cartoon. Match the look of natural stock photography.\n")
    print(f"Category: {category}")
    print(f"Specific focus: {caption}")
    print(f"Visual emphasis: {alt_text}")
    print(f"\nFilename: {filename}\n")

    full_prompt = f"""
Photorealistic editorial image for a YardBonita.com blog post titled: '{title}'.
Scene: A real residential yard in the Southeast Valley of Arizona (Gilbert, Chandler, Mesa, Queen Creek).
Style: Realistic stock photo, warm lighting, desert-adapted plants, no fantasy or cartoon styling.
Avoid: Green lawns, overcast skies, overlays, text, or rendered/glossy textures.
Focus: {caption}
Visual emphasis: {alt_text}
""".strip()

    try:
        print("🎨 Calling DALL·E API...")
        response = openai.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            n=1,
            size="1024x1024",  # Most realistic size allowed by DALL·E-3 API
            quality="standard",
            response_format="url"
        )
        image_url = response.data[0].url
        print(f"✅ API returned image URL: {image_url}")
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    main()
