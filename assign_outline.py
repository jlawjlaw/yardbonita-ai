import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
import pandas as pd
import openai
import httpx

# === File Paths ===
base_path = os.path.dirname(__file__)
planning_path = os.path.join(base_path, "planning.xlsx")
author_path = os.path.join(base_path, "YardBonita_Author_Personas.xlsx")
cache_path = os.path.join(base_path, "outline_cache.json")

# === OpenAI Setup ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Load Data ===
planning_df = pd.read_excel(planning_path)
author_df = pd.read_excel(author_path)

planning_df.columns = planning_df.columns.str.lower()
author_df.columns = author_df.columns.str.lower()

# === Load or Init Cache ===
if os.path.exists(cache_path):
    with open(cache_path, "r", encoding="utf-8") as f:
        outline_cache = json.load(f)
else:
    outline_cache = {}

# === GPT Outline Generator (Async) ===
async def gpt_outline_async(title, category, author, client):
    key = f"{title}||{category}"
    if key in outline_cache:
        print(f"✅ Cached: {title}")
        return outline_cache[key]

    author_message = f"You are {author}, writing for YardBonita." if author else "You are a contributor to YardBonita."
    system_prompt = (
        f"{author_message} YardBonita is a home and yard care blog focused on seasonal, regional advice for U.S. homeowners. "
        "Generate a 5–6 part article outline based on the title and category provided. Focus on clarity and structure. Skip intro/conclusion."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Title: {title}\nCategory: {category}"}
    ]

    retries = 5
    for attempt in range(retries):
        try:
            print(f"🌐 Sending request for: {title}")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            outline = data["choices"][0]["message"]["content"].strip()
            outline_cache[key] = outline
            print(f"✅ Received response for: {title}")
            return outline
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 10 + attempt * 5
                print(f"⏳ Rate limit hit. Retrying {title} in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"❌ Error for '{title}': {e}")
                return ""
        except Exception as e:
            print(f"❌ Unexpected error for '{title}': {e}")
            return ""
    print(f"⚠️ Failed after retries: {title}")
    return ""

# === Main Async Logic ===
async def process_outlines(days=1, max_per_day=5, concurrency=1):
    eligible = planning_df[
        (planning_df["status"].str.lower() == "planned") &
        (planning_df["outline"].isna() | (planning_df["outline"].str.strip() == "")) &
        (planning_df["category"].notna())
    ].copy()

    eligible = eligible.sort_values("publish_date")
    grouped = eligible.groupby("publish_date")
    processed = []
    summaries = {}

    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        tasks = []

        for i, (date, group) in enumerate(grouped):
            if i >= days:
                break
            print(f"📅 Processing outlines for: {date.strftime('%Y-%m-%d')}")
            summaries[date] = 0
            count = 0
            for idx, row in group.iterrows():
                if count >= max_per_day:
                    break

                title = row["post_title"]
                category = row["category"]

                async def bound_task(index=idx, title=title, category=category, date=date):
                    async with sem:
                        row = planning_df.loc[index]
                        author = row.get("author", "").strip()
                        print(f"✏️  Generating: {title}")
                        outline = await gpt_outline_async(title, category, author, client)
                        uuid_val = planning_df.loc[index, "uuid"]
                        print(f"🆔 UUID: {uuid_val}")
                        print("📋 Outline:")
                        print(outline + "\n" + "-"*60)
                        planning_df.loc[index, "outline"] = outline
                        processed.append(title)
                        summaries[date] += 1

                tasks.append(bound_task())
                count += 1

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=600)
        except asyncio.TimeoutError:
            print("⚠️ Timeout: Some outlines took too long.")

    if processed:
        planning_df.to_excel(planning_path, index=False)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(outline_cache, f, indent=2)
        print(f"✅ Added outlines to {len(processed)} articles")
        print("📄 Saved: planning.xlsx + outline_cache.json")
        print("📅 Outline summary by date:")
        for date, count in summaries.items():
            print(f"  {date}: {count} outlines")
    else:
        print("✅ No articles updated.")

# === CLI Entrypoint ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("days", type=int, nargs="?", default=1)
    parser.add_argument("max_per_day", type=int, nargs="?", default=5)
    args = parser.parse_args()

    asyncio.run(process_outlines(args.days, args.max_per_day))
