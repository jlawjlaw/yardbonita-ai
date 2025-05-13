# generate_article.py – YardBonita Article Generator Entry Point
# Canonical Version: v1.3.2
# Last Modified: 2025-05-11

"""
🔁 Updates:
- Fully aligned with Canonical Prompt v1.4+
- Graceful fallback if GPT returns None or retry fails
- Adds rewrite flag + notes to planning.xlsx if retry fails
"""

import os, pandas as pd, datetime, argparse

from utils import (
    load_planning_data,
    get_author_persona,
    get_related_articles,
    generate_article_and_metadata,
    generate_image_prompt,
    generate_image,
    save_image_from_url,
    get_next_eligible_article,
    save_article_to_planning,
)

PLANNING_PATH = "planning.xlsx"
PERSONA_PATH = "YardBonita_Author_Personas.xlsx"
PUBLISHED_PATH = "published.xlsx"
PROMPT_PATH = "canonical_prompt.txt"


import argparse
import datetime
import pandas as pd

from utils import (
    load_planning_data,
    get_author_persona,
    get_related_articles,
    generate_article_and_metadata,
    save_article_to_planning,
    get_next_eligible_article,
)

PLANNING_PATH = "planning.xlsx"
PERSONA_PATH = "YardBonita_Author_Personas.xlsx"
PUBLISHED_PATH = "published.xlsx"
PROMPT_PATH = "canonical_prompt.txt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all_today", action="store_true", help="Generate all articles scheduled for today")
    args = parser.parse_args()

    # Load planning and persona data
    planning_df = load_planning_data(PLANNING_PATH)
    persona_df = pd.read_excel(PERSONA_PATH, engine="openpyxl")
    published_df = pd.read_excel(PUBLISHED_PATH, engine="openpyxl")

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if args.all_today:
        rows_to_process = planning_df[
            (planning_df["publish_date"].astype(str) == today_str) &
            (planning_df["status"].str.lower() == "planned")
        ]
    else:
        single_row, row_offset = get_next_eligible_article(planning_df)
        if single_row is None:
            print("❌ No eligible article found.")
            return
        rows_to_process = pd.DataFrame([single_row])
        rows_to_process["_row_offset"] = [row_offset]

    for idx, article_data in rows_to_process.iterrows():
        try:
            print(f"\n🦪 Generating: {article_data['post_title']} ({article_data['uuid']})")

            # Show preview
            print("\n📁 First few planning rows:")
            print(planning_df.head(3).to_string(index=False))

            # If no row_offset (e.g., from --all_today), get it now
            row_offset = article_data.get("_row_offset")
            if pd.isna(row_offset):
                _, row_offset = get_next_eligible_article(planning_df)

            # Related articles
            related_articles = get_related_articles(
                published_df,
                article_data.get("city", ""),
                article_data.get("category", ""),
                article_data.get("publish_date", ""),
                article_data.get("post_title", "")
            )
            article_data["related_articles"] = related_articles

            # Load system prompt
            with open(PROMPT_PATH, "r") as f:
                system_prompt = f.read()

            # Generate article
            gpt_output = generate_article_and_metadata(
                article_data, persona_df, published_df, related_articles, system_prompt
            )

            # GPT failure fallback
            if not gpt_output:
                article_data["rewrite"] = "yes"
                article_data["status"] = "Draft"
                article_data["notes"] = f"GPT failed to meet {article_data['tier']} minimum (retry returned nothing)"
                article_data["article_html"] = ""
                article_da