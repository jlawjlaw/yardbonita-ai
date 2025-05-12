# generate_article.py – YardBonita Article Generator Entry Point
# Canonical Version: v1.3.2
# Last Modified: 2025-05-11

"""
🔁 Updates:
- Fully aligned with Canonical Prompt v1.4+
- Graceful fallback if GPT returns None or retry fails
- Adds rewrite flag + notes to planning.xlsx if retry fails
"""

import os, pandas as pd, datetime

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

def main():
    try:
        # Load planning and persona data
        planning_df = load_planning_data(PLANNING_PATH)
        persona_df = pd.read_excel(PERSONA_PATH, engine="openpyxl")
        published_df = pd.read_excel(PUBLISHED_PATH, engine="openpyxl")

        # Display planning preview
        print("\n📁 First few planning rows:")
        print(planning_df.head(3).to_string(index=False))

        # Select next eligible article
        article_data, row_offset = get_next_eligible_article(planning_df)
        if article_data is None:
            raise Exception("❌ No eligible article found for today or later.")

        print(f"\n📊 Pulled Article Row {row_offset}:")
        print(article_data)

        # Gather related articles
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

        print(f"\n🦪 Generating: {article_data['post_title']} ({article_data['uuid']})")

        # Call GPT to generate the article
        gpt_output = generate_article_and_metadata(
            article_data, persona_df, published_df, related_articles, system_prompt
        )

        # Handle GPT total failure
        if not gpt_output:
            article_data["rewrite"] = "yes"
            article_data["status"] = "Draft"
            article_data["notes"] = f"GPT failed to meet {article_data['tier']} minimum (retry returned nothing)"
            article_data["article_html"] = ""
            article_data["focus_keyphrase"] = ""
            article_data["seo_title"] = ""
            article_data["seo_description"] = ""
            article_data["tags"] = ""
            save_article_to_planning(row_offset, article_data, {}, PLANNING_PATH)
            print(f"\n📉 Short article saved with rewrite flag — 0 words. Retry returned nothing.")
            return

        # Display key metadata
        for field in ["focus_keyphrase", "seo_title", "seo_description", "tags"]:
            print(f"  - {field}: {gpt_output.get(field, '')}")

        print("\n✅ Image Metadata:")
        for key in ["image_filename", "image_caption", "image_alt_text"]:
            print(f"  - {key}: {gpt_output.get(key)}")

        # Validate final article
        if not gpt_output.get("article_html"):
            raise Exception("❌ GPT returned no article_html — skipping save.")

        if gpt_output.get("rewrite") == "yes":
            print(f"\n🟨 Saving short article with rewrite flag — {gpt_output['word_count']} words.")

        # Save back to spreadsheet
        save_article_to_planning(row_offset, article_data, gpt_output, PLANNING_PATH)
        print("\n📆 Article wr