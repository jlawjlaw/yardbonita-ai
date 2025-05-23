# utils_db.py – YardBonita Unified Utilities (Database Version)
# Canonical Version: v2.0.0
# Last Modified: 2025-05-15

import os, json, datetime, re, random, requests, uuid
from sqlalchemy import text
import pandas as pd


# === Flair Configuration ===
FLAIR_POOL ={
    "Marcus Wynn": ["emoji_paragraph_starts", "expert_quote", "high_value_external_link", "bold_first_sentence"],
    "Sofia Vargas": ["emoji_paragraph_starts", "fun_friendly_language", "inline_definitions", "diy_tip_boxes"],
    "Priya Shah": ["science_fact_boxes", "external_high_quality_link", "clarity_quotes", "graphical_comparison"],
    "Tina Delgado": ["gardening_emoji_flair", "latin_desert_reference", "step_by_step_blocks", "watering_icons"],
    "Ramon Ellis": ["visual_description_flair", "casual_tone", "quote_a_neighbor", "pro_tip_flags"],
    "Derek Holt": ["tech_tip_flair", "troubleshooting_blocks", "gear_icon_headers", "compressed_checklist"],
    "Deshawn Hill": ["straightforward_icons", "southern_voice_flair", "contractor_quotes", "watering_chart_flair"],
    "Leah Tran": ["mom_voice_tips", "kid_friendly_boxes", "emoji_title_flair", "bullet_flair_sections"],
    "Carlos Mendez": ["contractor_tone_boxes", "before_after_tips", "bold_summary_lines", "emoji_summary_icons"],
    "Jamie Rivera": ["native_plant_highlight", "coastal_soil_facts", "emoji_headers", "seasonal_color_callouts"],
    "Derek Sloan": ["techy_inline_stats", "calendar_blocks", "smart_device_mentions", "bullet_experiment_notes"],
    "Tasha Beaumont": ["design_tip_boxes", "visual_flair_descriptions", "container_garden_callouts", "bold_title_rules"]
}

FLAIR_GLOSSARY = {
    "before_after_tips": "Present a visual before/after comparison or transformation tip.",
    "emoji_summary_icons": "Use an emoji to close a key idea or recap an action.",
    "emoji_paragraph_starts": "Start key paragraphs with a relevant emoji to set the tone or theme.",
    "expert_quote": "Include a short, authoritative quote from a fictional expert to support your point.",
    "high_value_external_link": "Link to a high-quality external source that supports the advice given.",
    "bold_first_sentence": "Begin sections with a bolded sentence that summarizes the main takeaway.",
    "fun_friendly_language": "Use playful, upbeat language that keeps the tone light and conversational.",
    "inline_definitions": "Define key terms directly in the paragraph using simple, clear language.",
    "diy_tip_boxes": "Add callout boxes with quick DIY tips readers can try immediately.",
    "science_fact_boxes": "Insert a short box explaining the science behind a key concept or result.",
    "external_high_quality_link": "Add a trustworthy external resource that deepens the topic.",
    "clarity_quotes": "Use a quote that brings clarity or a fresh perspective to the advice.",
    "graphical_comparison": "Describe a visual or chart-style comparison to highlight changes or differences.",
    "latin_desert_reference": "Make culturally grounded references to desert plant traditions or practices.",
    "step_by_step_blocks": "Break down a task into clear numbered steps or blocks.",
    "watering_icons": "Use simple icons or symbols to visually represent watering needs or schedules.",
    "quote_a_neighbor": "Include a fictional quote from a neighbor sharing a relatable tip or reaction.",
    "pro_tip_flags": "Add labeled 'Pro Tips' to emphasize expert-level guidance.",
    "tech_tip_flair": "Highlight smart or technical yard care tips in a gadget-savvy tone.",
    "troubleshooting_blocks": "Offer common problems and how to fix them in a structured block.",
    "gear_icon_headers": "Start section headers with gear or tool icons to set context.",
    "compressed_checklist": "Include a short, punchy checklist of what to do or avoid.",
    "straightforward_icons": "Use simple visual icons to reinforce plain-spoken guidance.",
    "contractor_quotes": "Include a fictional quote from a local contractor offering insight.",
    "watering_chart_flair": "Describe watering needs as if in a table or visual schedule.",
    "kid_friendly_boxes": "Add side tips for how to involve or teach kids in the task.",
    "emoji_title_flair": "Add emojis to section titles to boost clarity and appeal.",
    "bullet_flair_sections": "Use bullet points with flair or icons to guide the reader clearly.",
    "bold_summary_lines": "End sections with a strong, bolded summary takeaway.",
    "native_plant_highlight": "Call attention to a native plant and its benefits.",
    "coastal_soil_facts": "Include a fact related to coastal or sandy soils.",
    "emoji_headers": "Start each section with an emoji-based title for emphasis.",
    "seasonal_color_callouts": "Describe seasonal color changes and how to use them.",
    "techy_inline_stats": "Mention a statistic or data point with a geeky angle.",
    "calendar_blocks": "Use calendar-based callouts to suggest timing or scheduling.",
    "smart_device_mentions": "Mention smart irrigation or monitoring tools.",
    "bullet_experiment_notes": "Use bulleted observations or tips from a fictional home experiment.",
    "design_tip_boxes": "Insert a tip box focused on visual appeal or layout.",
    "visual_flair_descriptions": "Use language that paints a scene and evokes the look of a space.",
    "container_garden_callouts": "Add quick hits related to container garden choices or care.",
    "bold_title_rules": "Include bolded subheaders or title-like phrases within paragraphs."
}

def unslugify(slug):
    return " ".join(word.capitalize() for word in slug.strip().replace("-", " ").split())
    
def load_planning_data(path):
    return pd.read_excel(path)

def get_author_persona(conn, author_name):

    true_name = unslugify(author_name)

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT author, city, specialty, tone, bio
            FROM authors
            WHERE TRIM(LOWER(author)) = TRIM(LOWER(?))
            LIMIT 1
        """, (true_name.lower(),))
        row = cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "city": row[1],
                "specialty": row[2] or "yard care",
                "tone": row[3] or "natural and helpful",
                "bio": row[4] or ""
            }
    except Exception as e:
        print(f"⚠️ Failed to fetch author persona from DB: {e}")

    # fallback if no match
    return {
        "name": author_name,
        "city": "Gilbert",
        "specialty": "seasonal yard care",
        "tone": "natural and helpful",
        "bio": ""
    }

def select_flair(author, article_data=None, conn=None):

    # If flair already cached for this article, use it
    if article_data and conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT flair_styles FROM articles WHERE uuid = ?", (article_data["uuid"],))
            row = cursor.fetchone()
            if row and row[0]:
                return [s.strip() for s in row[0].split(",") if s.strip()]
        except Exception as e:
            print(f"⚠️ Failed to read flair from DB: {e}")

    # Normalize author name in case it's a slug (e.g., 'marcus-wynn' → 'Marcus Wynn')
    true_name = unslugify(author)
    flair_options = FLAIR_POOL.get(true_name, [])
    if not flair_options:
        return []

    roll = random.random()
    flair_list = random.sample(flair_options, 2 if roll > 0.80 else 1) if roll > 0.10 else []

    # Save to DB immediately
    if article_data and conn:
        try:
            cursor = conn.cursor()
            flair_str = ", ".join(flair_list)
            cursor.execute("UPDATE articles SET flair_styles = ? WHERE uuid = ?", (flair_str, article_data["uuid"]))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Failed to save flair to DB: {e}")

    return flair_list


def get_related_articles_from_db(engine, city, category, publish_date, post_title):
    import pandas as pd
    from sqlalchemy import text
    import random

    publish_date = pd.to_datetime(publish_date)
    start_date = publish_date - pd.DateOffset(months=2)
    end_date = publish_date + pd.DateOffset(months=2)

    query = text("""
        SELECT post_title, published_url
        FROM published
        WHERE LOWER(category) = LOWER(:category)
          AND LOWER(post_title) != LOWER(:post_title)
          AND publish_date BETWEEN :start AND :end""")

    with engine.connect() as conn:
        result = conn.execute(query, {
            "category": category,
            "post_title": post_title,
            "start": start_date.date(),
            "end": end_date.date()
        })
        articles = [dict(row._mapping) for row in result.fetchall()]

    random.shuffle(articles)
    return articles[:4]

def clean_internal_links(text):
    return re.sub(r'\[INTERNAL LINK\]', '', text)

def generate_image_prompt(author, specialty, city, title):
    return f"Photorealistic yard care scene in {city}, inspired by '{title}'"

def generate_image(prompt, date_str, size="1024x1024"):
    fallback_caption = prompt or "Seasonal yard care scene"
    try:
        filename = re.sub(r"\W+", "-", prompt)[:40].strip("-") + f"-{date_str}.png"
        # Store it directly in image_filename
        return {
            "filename": filename,
            "url": None,
            "caption": fallback_caption,
            "alt_text": fallback_caption,
            "prompt": prompt,
        }
    except Exception as e:
        print("❌ Exception during image generation:", e)
        fallback_filename = "fallback-" + date_str + ".png"
        return {
            "filename": fallback_filename,
            "url": None,
            "caption": fallback_caption,
            "alt_text": fallback_caption,
            "prompt": prompt,
        }

def save_image_from_url(image_url, filename, folder="ai-images"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    if not image_url:
        print("⚠️ No image URL provided — skipping download.")
        return None
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(os.path.join(folder, filename), 'wb') as f:
            f.write(response.content)
        return filename
    return None

def build_article_footer(related_articles, author_bio):
    blocks = []

    if related_articles:
        related_html = '<div class="related-articles">\n'
        related_html += "<p><strong>Related</strong></p>\n<ul>"
        for item in related_articles:
            related_html += f'<li><a href="{item["published_url"]}">{item["post_title"]}</a></li>'
        related_html += "</ul>\n</div>"
        blocks.append(related_html)

    if author_bio:
        blocks.append(
            f"""
<div class="author-byline">
  <p><strong>About the Author</strong></p>
  <div>{author_bio.strip()}</div>
</div>
""".strip()
        )

    return "\n\n".join(blocks).strip() if blocks else None

def inject_image_tag(html: str, image_tag: str, placement: str) -> str:
    """
    Injects an <img> tag into the article HTML based on the placement strategy.
    Options:
        - "after_intro"
        - "after_section_2", "after_section_3", etc.
    """
    html = html.strip()

    if placement == "after_intro":
        # Insert after first <p> block
        return re.sub(r"(<p>.*?</p>)", r"\1\n" + image_tag, html, count=1, flags=re.DOTALL)

    elif placement.startswith("after_section_"):
        section_number = int(placement.split("_")[-1])
        matches = list(re.finditer(r"<h2>.*?</h2>", html))

        if len(matches) >= section_number:
            insert_pos = matches[section_number - 1].end()
            return html[:insert_pos] + "\n" + image_tag + html[insert_pos:]
        else:
            # Fallback: append to end
            return html + "\n" + image_tag

    else:
        # Unknown or fallback strategy
        return html + "\n" + image_tag


def parse_delimited_response(raw_response):
    # Define the expected structure
    expected_sections = {
        "tier": "",
        "focus_keyphrase": "",
        "seo_title": "",
        "seo_description": "",
        "tags": "",
        "article_html": "",
        "image_filename": "",
        "image_alt_text": "",
        "image_caption": "",
        "image_prompt": ""
}

    # Regex to match: ==SECTION==\n(optional content)\n==NEXT_SECTION==
    pattern = re.compile(r"==([A-Z_]+)==\n(.*?)(?=(?:\n==[A-Z_]+==)|\Z)", re.DOTALL)

    # Find and assign matches
    for key, value in pattern.findall(raw_response):
        normalized_key = key.lower()
        if normalized_key in expected_sections:
            expected_sections[normalized_key] = value.strip()

    return expected_sections

    current = None
    for line in raw_response.splitlines():
        line = line.strip()
        if line.startswith("==") and line.endswith("=="):
            key = line.strip("=").strip().lower()
            if key in expected_sections:
                current = key
            else:
                print(f"⚠️ Unknown section key in GPT response: '{key}'")
                current = None
        elif current:
            expected_sections[current] += line + "\n"

    for key in expected_sections:
        expected_sections[key] = expected_sections[key].strip()

    if expected_sections["tags"]:
        expected_sections["tags"] = [t.strip() for t in expected_sections["tags"].split(",")]

    return expected_sections


def generate_article_and_metadata(article_data, related_articles, system_prompt, conn=None, use_claude=True):
    import re, json, random
    from claude_client import call_claude

    title = article_data.get("post_title", "")
    author = article_data.get("author", "")
    flair_list = select_flair(author, article_data, conn)

    persona = get_author_persona(conn, author)
    author_bio = persona["bio"]  # Always include, Claude will decide usage

    image_instruction = (
        "after_intro" if random.random() < 0.5 else f"after_section_{random.choice([2, 3, 4])}"
    )

    # Inject persona and flair
    persona_block = f"""
🎨 Persona and Flair Instructions

Write in the voice of **{persona['name']}**, a {persona['city']}-based expert in {persona['specialty'].lower()}.
Use a tone that is {persona['tone'].lower()}. Reflect their background, communication style, and local knowledge.
""".strip()

    if flair_list:
        persona_block += "\n\nApply the following flair styles naturally and consistently throughout the article:\n"
        for flair in flair_list:
            persona_block += f"- **{flair}**: {FLAIR_GLOSSARY.get(flair, '')}\n"
        persona_block += "\nOnly use the flair types listed above — do not invent or add others."
    else:
        persona_block += "\n\nNo flair styles are included. Write cleanly and clearly without embellishments."

    if "🎨 Persona and Flair Instructions" in system_prompt:
        system_prompt = system_prompt.split("🎨 Persona and Flair Instructions")[0] + "🎨 Persona and Flair Instructions\n\n" + persona_block
    else:
        system_prompt = persona_block + "\n\n" + system_prompt

    # 🔄 Get category slug from category_id
    category_slug = ""
    if conn and article_data.get("category_id"):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT slug FROM categories WHERE category_id = ?", (article_data["category_id"],))
            row = cursor.fetchone()
            if row:
                category_slug = row[0]
        except Exception as e:
            print(f"⚠️ Failed to resolve category slug for article {article_data.get('uuid')}: {e}")

    user_prompt = {
        "title": article_data["post_title"],
        "city": article_data.get("city", ""),
        "category": category_slug,
        "tier": "Tier 1",  # ✅ LOCK to Tier 1
        "min_word_count": 1800,  # ✅ Enforce Tier 1 word count
        "internal_links": related_articles,  # ✅ Already passed
        "flair_styles": flair_list or ["contractor_quotes"],
        "author_persona": article_data.get("author", "default"),
        "focus_keyphrase": "",  # Claude will generate
        "seo_title": "",        # Claude will generate
        "seo_description": "",  # Claude will generate
        "tags": "",             # Claude will generate
        "instructions": (
            "This must be written as a Tier 1 article (1800+ words), "
            "with clear structure, helpful HTML formatting, and local detail. "
            "Do not end with a summary or use wrap-up phrases. Each section must be full and useful."
        )
    }
    
    user_prompt["nonce"] = str(uuid.uuid4())

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt)}
    ]

    # === BATCH PREP SHORT-CIRCUIT ===
    if use_claude == "batch_prep_only":
        return {
            "user_prompt": user_prompt,
            "flair_styles": flair_list
        }

    def run_gpt(messages):
        try:
            system_msg, user_msg = "", ""
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                elif m["role"] == "user":
                    user_msg = m["content"]

            if use_claude:
                return call_claude(user_msg, system_msg=system_msg)
            else:
                raise NotImplementedError("GPT backend not implemented. Set use_claude=True.")
        except Exception as e:
            print(f"❌ Claude/GPT call failed: {e}")
            return None


    raw_output = run_gpt(messages)
    parsed, word_count, tier_min = validate_and_process(
    raw_output,
    related_articles=related_articles,
    author_bio=author_bio,
    flair_list=flair_list,
    image_instruction=image_instruction
)

    if parsed and word_count >= tier_min:
        print(f"✅ Article word count: {word_count} (Tier minimum: {tier_min})")
        return parsed

    if parsed:
        parsed.update({
            "rewrite": "yes",
            "notes": f"Returned only {word_count} words (Tier minimum: {tier_min})",
            "status": "Draft",
            "uuid": article_data["uuid"],
            "post_title": article_data["post_title"],
            "city": article_data["city"],
            "category": article_data["category"],
        })
        return parsed

    return None

    
def get_next_eligible_article(planning_df):

    today = pd.Timestamp(datetime.datetime.now().date())
    candidates = planning_df[
        (planning_df["status"].astype(str).str.lower() == "planned") &
        (pd.to_datetime(planning_df["publish_date"]).dt.date >= today.date()) &
        ((planning_df["article_html"].isna()) | (planning_df["article_html"].astype(str).str.strip() == ""))
    ]
    if candidates.empty:
        print("⚠️ No eligible articles found.")
        return None, None

    next_row = candidates.sort_values(by="publish_date").iloc[0]
    row_index = planning_df.index.get_loc(next_row.name)
    print(f"✅ Selected row: {next_row['post_title']} (row {row_index})")
    return next_row.to_dict(), row_index

def enforce_intro_paragraph(html: str) -> str:
    """
    Ensures the article HTML starts with a <p> paragraph and not an <h2> or other heading.
    If an <h2> appears first, inserts a generic intro paragraph before it.
    """
    html = html.strip()
    if html.lower().startswith("<h2>"):
        match = re.match(r"<h2>(.*?)</h2>", html, flags=re.IGNORECASE)
        if match:
            first_heading = match.group(0)
            remaining = html[len(first_heading):].lstrip()
            intro = (
                "<p>As the seasons shift, it’s the perfect time to explore what your yard needs most. "
                "Let’s dive into some timely tips to help your outdoor space thrive.</p>\n"
            )
            return intro + "\n" + first_heading + "\n" + remaining
    return html

def remove_intro_heading(html: str) -> str:
    """
    Removes an <h2>Introduction</h2> tag from the top of the article, if present.
    Leaves the paragraph content intact.
    """
    return re.sub(r'^<h2>\s*Introduction\s*</h2>\s*', '', html.strip(), flags=re.IGNORECASE)

def fix_encoding_issues(text):
    if not isinstance(text, str):
        return text
    return (
        text.replace("â€”", "—")
            .replace("â€“", "–")
            .replace("â€˜", "‘")
            .replace("â€™", "’")
            .replace("â€œ", "“")
            .replace("â€�", "”")
            .replace("â€¦", "…")
            .replace("‚Äî", "—")
            .replace("‚Äôs", "’s")
            .replace("‚Äù", "”")
            .replace("‚Äì", "–")
            .replace("Ã©", "é")
            .replace("Ã", "à")
    )
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

# Map common broken surrogate pairs to the intended emoji
BROKEN_EMOJI_MAP = {
    "üí°": "🌱",   # plant / nature
    "üåª": "🦋",   # butterfly / pollinator
    "üêù": "🐝",   # bee
    "üåº": "🌼",   # flower / spring
    "üê¶": "🪶",   # bird/pollinator
    "üå≥": "🌳",   # tree
    "üåµ": "🌺",   # tropical plant
    "üå∫": "🔥",   # sun / heat
    "üå∑": "✨",   # magic / fairy duster
    "ü¶ã": "🦋",   # butterfly
    "üå∏": "🏵️",  # decorative flower
    "üí° Kid Friendly Box:": "🌟 Kid Friendly Box:",  # special case full replacement
}

def fix_broken_emojis(text: str) -> str:
    for broken, emoji in BROKEN_EMOJI_MAP.items():
        text = text.replace(broken, emoji)
    return text

def update_article_in_db(conn, gpt_output, article_data):
    print("🛠 Entered update_article_in_db")
    print("🔑 UUID passed in:", article_data.get("uuid"))
    from re import findall

    word_count = len(findall(r'\b\w+\b', gpt_output.get("article_html", "")))
    flair_used = gpt_output.get("flair_used", 0)
    flair_requested = gpt_output.get("flair_requested", 0)
    tier = article_data.get("tier", "")
    min_words = {"Tier 1": 1400, "Tier 2": 1100, "Tier 3": 900}.get(tier, 1100)
    rewrite_flag = "yes" if word_count < int(min_words * 0.85) else "no"

    notes = f"word_count:{word_count}/{min_words}; flair_used:{flair_used}/{flair_requested}; image_placement:{gpt_output.get('image_placement', '')}"

    # === Build update fields from GPT output ===
    update_fields = {
        "rewrite": rewrite_flag,
        "notes": notes,
        "article_html": gpt_output.get("article_html", ""),
        "focus_keyphrase": gpt_output.get("focus_keyphrase", ""),
        "seo_title": gpt_output.get("seo_title", ""),
        "seo_description": gpt_output.get("seo_description", ""),
        "tags": ", ".join(gpt_output.get("tags", [])) if isinstance(gpt_output.get("tags"), list) else (gpt_output.get("tags") or ""),
        "image_filename": gpt_output.get("image_filename", ""),
        "image_caption": gpt_output.get("image_caption", ""),
        "image_alt_text": gpt_output.get("image_alt_text", ""),
        "image_prompt": gpt_output.get("image_prompt", "")
    }

    # Conditionally set the status
    if article_data.get("status") in ("Planned", "In Batch", None):
        update_fields["status"] = "Image Needed"
        
    if "image_prompt" in update_fields:
        preview = update_fields["image_prompt"][:60] + "..."
        print(f"  image_prompt: {preview}")

    # === Prepare SQL update ===
    set_clause = ", ".join([f"{col} = ?" for col in update_fields])
    values = list(update_fields.values())
    uuid = article_data.get("uuid")

    sql = f"UPDATE articles SET {set_clause} WHERE uuid = ?"
    params = values + [uuid]

    # === Execute Update ===
    cursor = conn.cursor()
    print("⬇️ Saving to DB with the following fields:")
    for k, v in update_fields.items():
        preview = v[:60] + "..." if isinstance(v, str) and len(v) > 60 else v
        print(f"  {k}: {preview}")

    print(f"🛠 SQL: {sql}")
    print(f"📦 Params: {params}")

    cursor.execute(sql, params)
    conn.commit()

    if cursor.rowcount == 0:
        print(f"❌ No row found for UUID: {uuid}")
    else:
        print(f"✅ Article {uuid} saved to DB")
    
def get_next_eligible_article_from_db(conn):
    today = datetime.datetime.now().date()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM articles
        WHERE LOWER(status) = 'planned'
            AND (article_html IS NULL OR TRIM(article_html) = '')
            AND DATE(publish_date) >= ?
        ORDER BY publish_date ASC
        LIMIT 1
    """, (today,))
    row = cursor.fetchone()

    if row:
        cursor.execute("PRAGMA table_info(articles)")
        columns = [col[1] for col in cursor.fetchall()]
        article = dict(zip(columns, row))
        return article, article["uuid"]
    else:
        print("⚠️ No eligible articles found in DB")
        return None, None
    
def link_inline_titles_to_articles(html: str, related_articles: list[dict]) -> str:
    """
    Replaces plain-text mentions of related article titles with proper <a href="..."> links.
    Only links exact title matches, case-insensitive, and avoids re-linking if already wrapped.
    """
    for article in related_articles:
        title = article.get("post_title", "").strip()
        url = article.get("published_url", "").strip()
        if not title or not url or url == "None":
            continue

        # Skip if already linked
        if f'href="{url}"' in html:
            continue

        # Use negative lookbehind to avoid replacing inside existing <a> tags
        pattern = rf'(?<![">])\b({re.escape(title)})\b'
        replacement = rf'<a href="{url}">\1</a>'
        html = re.sub(pattern, replacement, html, count=1, flags=re.IGNORECASE)

    return html    
    
def validate_and_process(raw_output, related_articles, author_bio, flair_list, image_instruction):
    parsed = parse_delimited_response(raw_output)
    html = parsed.get("article_html", "")
    html = link_inline_titles_to_articles(html, related_articles)
    if not html.strip():
        return None, 0

    word_count = len(re.sub(r"<[^>]+>", "", html).split())
    chosen_tier = parsed.get("tier", "").strip()

    tier_min = {
        "Tier 1": 1800,
        "Tier 2": 1400,
        "Tier 3": 1100
    }.get(chosen_tier, 1100)

    # Inject image
    image_tag = f"""
<figure>
<img src="{parsed.get('image_filename')}" alt="{parsed.get('image_alt_text')}">
<figcaption>{parsed.get('image_caption')}</figcaption>
</figure>
""".strip()

    html = inject_image_tag(html, image_tag, image_instruction)

    # Footer
    footer_html = build_article_footer(related_articles, author_bio)
    if footer_html:
        html += "\n\n" + footer_html

    flair_used = len([f for f in flair_list if f in html])

    parsed.update({
        "article_html": html,
        "flair_styles": flair_list,
        "flair_requested": len(flair_list),
        "flair_used": flair_used,
        "image_placement": image_instruction,
        "word_count": word_count,
        "tier": parsed.get("tier", "Tier 2")
    })

    return parsed, word_count, tier_min