# generate_article.py – YardBonita Article Generator Entry Point
# Canonical Version: v1.3.3 (Updated with full error visibility and prompt fixes)

import os, pandas as pd, datetime, argparse
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
    parser.add_argument("--create", type=int, help="Number of articles to create regardless of publish date")
    args = parser.parse_args()

    try:
        planning_df = load_planning_data(PLANNING_PATH)
        persona_df = pd.read_excel(PERSONA_PATH, engine="openpyxl")
        published_df = pd.read_excel(PUBLISHED_PATH, engine="openpyxl")
    except Exception as e:
        print(f"❌ Failed to load input files: {e}")
        return

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if args.all_today:
        rows_to_process = planning_df[
            (planning_df["publish_date"].astype(str) == today_str) &
            (planning_df["status"].str.lower() == "planned")
        ]
    elif args.create:
        rows_to_process = planning_df[
            (planning_df["status"].str.lower() == "planned") &
            ((planning_df["article_html"].isna()) | (planning_df["article_html"].astype(str).str.strip() == ""))
        ].head(args.create)

        if rows_to_process.empty:
            print("❌ No eligible planned articles found for --create.")
            return

        already_filled = rows_to_process[
            rows_to_process["article_html"].notna() &
            rows_to_process["article_html"].astype(str).str.strip().ne("")
        ]
        if not already_filled.empty:
            print("🛑 One or more selected rows already have article_html filled. Aborting.")
            print(already_filled[["uuid", "post_title", "publish_date"]])
            return

        row_offsets = rows_to_process.index.tolist()
        rows_to_process["_row_offset"] = row_offsets
    else:
        single_row, row_offset = get_next_eligible_article(planning_df)
        if single_row is None:
            print("❌ No eligible article found.")
            return
        rows_to_process = pd.DataFrame([single_row])
        rows_to_process["_row_offset"] = [row_offset]

    if rows_to_process.empty:
        print("⚠️ No rows to process after filtering.")
        return

    for idx, article_data in rows_to_process.iterrows():
        try:
            print(f"🦪 Generating: {article_data['post_title']} ({article_data['uuid']})")

            row_offset = article_data.get("_row_offset")
            if pd.isna(row_offset):
                _, row_offset = get_next_eligible_article(planning_df)

            related_articles = get_related_articles(
                published_df,
                article_data.get("city", ""),
                article_data.get("category", ""),
                article_data.get("publish_date", ""),
                article_data.get("post_title", "")
            )
            article_data["related_articles"] = related_articles

            with open(PROMPT_PATH, "r") as f:
                system_prompt = f.read()

            gpt_output = generate_article_and_metadata(
                article_data, persona_df, published_df, related_articles, system_prompt
            )

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
                print(f"📉 Short article saved with rewrite flag — 0 words. Retry returned nothing.")
                continue

            print("🔑 Metadata:")
            for field in ["focus_keyphrase", "seo_title", "seo_description", "tags"]:
                print(f"  - {field}: {gpt_output.get(field, '')}")

            if not gpt_output.get("article_html"):
                raise Exception("❌ GPT returned no article_html — skipping save.")

            if gpt_output.get("rewrite") == "yes":
                print(f"🟨 Short article with rewrite flag — {gpt_output['word_count']} words.")

            save_article_to_planning(row_offset, article_data, gpt_output, PLANNING_PATH)
            print(f"✅ Written: {article_data['post_title']} scheduled for {article_data['publish_date']}")

        except Exception as e:
            print(f"❌ Exception while processing row {idx}: {e}")

if __name__ == "__main__":
    main()
