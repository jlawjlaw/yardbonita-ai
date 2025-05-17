import pandas as pd
from datetime import datetime

# === Load Spreadsheets ===
df_planning = pd.read_excel("/Users/justinlaw/Desktop/Yardbonita/file for ai/2025planning.xlsx")
df_published = pd.read_excel("/Users/justinlaw/Desktop/Yardbonita/file for ai/published.xlsx")

# === Identify Unwritten Articles ===
written_titles = df_published["post_title"].tolist()
unwritten_articles = df_planning[~df_planning["post_title"].isin(written_titles)]

# === Sort by Date ===
unwritten_articles = unwritten_articles.sort_values(by="publish_date")

# === Pick the Next Article ===
next_article = unwritten_articles.iloc[0]

# === Extract Related Articles (Same City) ===
city = next_article["city"]
df_published_city = df_published[df_published["city"] == city]

def score_related(row):
    score = 0
    if row["category"] == next_article["category"]:
        score += 2
    if next_article["post_title"].split()[0] in row["post_title"]:
        score += 1
    return score

df_published_city.loc[:, "score"] = df_published_city.apply(score_related, axis=1)
related_articles = df_published_city.sort_values(by="score", ascending=False).head(3)

# === Construct Result ===
result = {
    "post_title": next_article["post_title"],
    "city": next_article["city"],
    "category": next_article["category"],
    "author": next_article["author"],
    "publish_date": next_article["publish_date"].strftime("%Y-%m-%d") if not isinstance(next_article["publish_date"], str) else next_article["publish_date"],
    "tier": next_article["tier"],
    "outline": next_article["outline"],
    "related_articles": [
        {"title": row["post_title"], "url": row["published_url"]}
        for _, row in related_articles.iterrows()
        if pd.notna(row["published_url"])
    ]
}

print("Next Article to Write:")
print(result)