# start_create_titles.py – Generate SEO Titles and Assign Normalized Categories
# Version: v1.1.0

import pandas as pd
import random
import openai
from dotenv import load_dotenv
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

PLANNING_PATH = "planning.xlsx"

CATEGORY_MAP = {
    "Lawn Care": "lawn-care",
    "Irrigation & Watering": "irrigation-watering",
    "Gardening": "gardening",
    "Composting & Soil Health": "composting",
    "Tree & Shrub Care": "tree-shrub-care",
    "Outdoor Living": "outdoor-living",
    "Yard Planning & Design": "yard-planning-design",
    "Monthly Checklists": "monthly-checklists",
    "Wildlife & Pollinators": "wildlife-pollinators",
    "Rain & Storm Management": "rain-storm-management",
    "Pest Control": "pest-control",
    "Seasonal Decor & Lighting": "seasonal-decor-lighting",
    "Tool & Equipment Maintenance": "tool-equipment-maintenance",
    "Hardscaping": "hardscaping",
    "Vegetable Gardening": "vegetable-gardening",
    "Yard Care": "lawn-care",
    "Needs Context": "needs-context"
}

def load_planning():
    return pd.read_excel(PLANNING_PATH, engine="openpyxl")

def save_planning(df):
    df.to_excel(PLANNING_PATH, index=False, engine="openpyxl")

def call_gpt_for_title_and_category(title_seed):
    prompt = f"Generate an SEO-optimized blog post title and category for a home and yard website based on: {title_seed}"
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def main():
    df = load_planning()
    rows_to_update = df[df["post_title"].isna() & df["status"].str.lower().eq("planned")]

    if rows_to_update.empty:
        print("✅ No new titles needed.")
        return

    for idx in rows_to_update.index:
        row = df.loc[idx]
        seed = row.get("slug", "seasonal yard idea")
        gpt_response = call_gpt_for_title_and_category(seed)

        # Naive parsing (you may want to improve this)
        lines = gpt_response.splitlines()
        title = lines[0].strip()
        category = lines[1].strip() if len(lines) > 1 else "Needs Context"

        # Normalize the category
        category_slug = CATEGORY_MAP.get(category, "needs-context")

        df.at[idx, "post_title"] = title
        df.at[idx, "category"] = category_slug
        print(f"📝 Title: {title} | Category: {category} → {category_slug}")

    save_planning(df)
    print("✅ planning.xlsx updated with new titles and normalized categories.")

if __name__ == "__main__":
    main()