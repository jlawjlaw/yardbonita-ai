
import pandas as pd
import sys
from datetime import datetime, timedelta

# === CONFIG ===
DEFAULT_NUM_DATES = 30
MAX_ARTICLES_PER_DAY = 4
EXCEL_FILE = "/Users/justinlaw/Desktop/Yardbonita/file for ai/planning.xlsx"

# === Get number of days from CLI ===
try:
    num_dates = int(sys.argv[1])
except (IndexError, ValueError):
    num_dates = DEFAULT_NUM_DATES

# === Load spreadsheet ===
df = pd.read_excel(EXCEL_FILE)

# === Normalize dates ===
df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce")

# === Start from tomorrow ===
tomorrow = pd.to_datetime(datetime.now().date() + timedelta(days=1))

# === Filter to future dates ===
future_df = df[df["publish_date"] >= tomorrow]

# === Count articles per date ===
counts = future_df.groupby("publish_date").size().reset_index(name="article_count")

# === Add in missing dates (0 articles) ===
all_dates = pd.date_range(start=tomorrow, end=df["publish_date"].max())
date_df = pd.DataFrame({"publish_date": all_dates})
merged = date_df.merge(counts, on="publish_date", how="left").fillna(0)
merged["article_count"] = merged["article_count"].astype(int)

# === Filter for dates with fewer than max allowed ===
missing_titles = merged[merged["article_count"] < MAX_ARTICLES_PER_DAY].copy()
missing_titles["missing_count"] = MAX_ARTICLES_PER_DAY - missing_titles["article_count"]

# === Limit to requested number of dates ===
result = missing_titles.head(num_dates)

# === Output ===
print("\n📆 Next {} days needing article titles:\n".format(num_dates))
for _, row in result.iterrows():
    print(f"{row['publish_date'].date()} needs {row['missing_count']} more article(s)")
