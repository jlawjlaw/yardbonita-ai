import pandas as pd
import sys

# Load files
planning_path = "/Users/justinlaw/Desktop/Yardbonita/file for ai/planning.xlsx"
published_path = "/Users/justinlaw/Desktop/Yardbonita/file for ai/published.xlsx"

df_planning = pd.read_excel(planning_path)
df_published = pd.read_excel(published_path)

# Drop rows with missing UUIDs
df_planning = df_planning.dropna(subset=["uuid"])
df_published = df_published.dropna(subset=["uuid"])

# Convert UUIDs to string for reliable comparison
published_uuids = df_published["uuid"].astype(str).tolist()

# Filter for articles not yet published and with no outline
unwritten_df = df_planning[~df_planning["uuid"].astype(str).isin(published_uuids)]
unwritten_df = unwritten_df[unwritten_df["outline"].isna()]
unwritten_df = unwritten_df.sort_values(by="publish_date")

# Get how many outlines to generate from command-line
num_articles = int(sys.argv[1]) if len(sys.argv) > 1 else 1
selected = unwritten_df.head(num_articles)

# Output structured metadata for outlining
for _, row in selected.iterrows():
    print(f"🟩 Please generate an outline using annualcontentplanningstep2.txt for:")
    print(f"UUID: {row['uuid']}")
    print(f"Title: {row['post_title']}")
    print(f"City: {row['city']}")
    print(f"Category: {row['category']}")
    print(f"Tier: {row['tier']}")
    print()