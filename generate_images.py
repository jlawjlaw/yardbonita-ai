# generate_images_one.py – YardBonita Single Image Generator
# Version: v1.2.2

import os
import pandas as pd
from datetime import datetime

PLANNING_PATH = "planning.xlsx"
IMAGE_FOLDER = "ai-images"

def load_planning():
    return pd.read_excel(PLANNING_PATH, engine="openpyxl")

def save_planning(df):
    df.to_excel(PLANNING_PATH, index=False, engine="openpyxl")

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
    df = load_planning()

    eligible = df[
        df["status"].str.lower().isin(["draft", "image needed"]) &
        df["image_filename"].notna() &
        df["image_filename"].astype(str).str.strip().ne("")
    ]

    if eligible.empty:
        print("✅ No images need to be generated.")
        return

    idx = eligible.index[0]
    row = df.loc[idx]
    uuid = row["uuid"]
    original_filename = row["image_filename"].strip()
    caption = row["image_caption"]
    alt_text = row["image_alt_text"]
    post_title = row["post_title"]

    # Ensure uniqueness
    final_filename = ensure_unique_filename(original_filename)

    # Update planning with new filename and new status
    df.at[idx, "image_filename"] = final_filename
    df.at[idx, "status"] = "Ready to Upload"
    save_planning(df)

    print("\n🖼️ GLOBAL IMAGE GENERATION PROMPT:\n")
    print("You are generating blog images for YardBonita.com, a home and garden site.")
    print("Create a realistic, high-quality photograph of a residential yard or garden scene that reflects the article's theme.")
    print("The image should look natural and grounded — no fantasy elements, no over-saturation, and no cartoon-like features.")
    print("Ensure the scene reflects the Southeast Valley of Arizona: dry climate, desert-adapted landscaping, warm lighting, and low-lush vegetation.")
    print("Avoid green grass lawns, overcast skies, or non-native trees.")
    print("Important: never include text, overlays, or whitespace.")
    print("All images must be: 1200×675px, 16:9 ratio, .png, and named as shown below.\n")

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