# utils.py – YardBonita Unified Article & Image Generation Utilities
# Canonical Version: v1.2.1
# Last Modified: 2025-05-10

"""
🔧 Function Index:
- load_planning_data(): Read Excel sheet into DataFrame
- get_author_persona(): Get specialty/persona for author
- select_flair(): Randomly assign 0–2 flair types from author pool
- get_related_articles(): Pull 4 city+category-matched links ±2 months
- clean_internal_links(): Strip unused placeholders
- generate_image_prompt(): Build prompt string for DALL·E
- generate_image(): Return image metadata (URL placeholder currently)
- save_image_from_url(): Download and save image (no-op if url=None)
- build_article_footer(): Create <div> block for related+author bio
- parse_delimited_response(): Handle GPT delimited response formatting
- generate_article_and_metadata(): Main GPT call + processing logic

🆕 Recent Changes:
- Added prompt_path as explicit parameter to ensure robust file I/O
- Included Yoast SEO optimization guidelines in system prompt
- Preserved GPT-provided image metadata: filename, caption, alt text
"""

import os, json, pandas as pd, datetime, re, random, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

FLAIR_POOL = {
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

def load_planning_data(path):
    return pd.read_excel(path)

def get_author_persona(persona_df, author_name):
    row = persona_df[persona_df["author"].str.strip().str.lower() == author_name.strip().lower()]
    
    if row.empty:
        return {
            "name": author_name,
            "city": "Gilbert",
            "specialty": "seasonal yard care",
            "tone": "natural and helpful",
            "bio": ""
        }

    r = row.iloc[0]
    return {
        "name": r["author"],
        "city": r.get("city", "Gilbert"),
        "specialty": r.get("specialty", "yard care"),
        "tone": r.get("tone", "natural and helpful"),
        "bio": r.get("bio", "")
    }

def select_flair(author):
    flair_options = FLAIR_POOL.get(author, [])
    if not flair_options:
        return []
    roll = random.random()
    return random.sample(flair_options, 2 if roll > 0.80 else 1) if roll > 0.10 else []

def get_related_articles(published_df, city, category, publish_date, post_title):
    try:
        publish_date = pd.to_datetime(publish_date)
        start_date = publish_date - pd.DateOffset(months=2)
        end_date = publish_date + pd.DateOffset(months=2)
        filtered = published_df[
            (published_df["category"].str.lower() == category.strip().lower()) &
            (published_df["post_title"].str.lower() != post_title.strip().lower()) &
            (pd.to_datetime(published_df["publish_date"]).between(start_date, end_date))
        ]
        return filtered[["post_title", "published_url"]].dropna().head(4).to_dict(orient="records")
    except Exception as e:
        print(f"❌ Error in get_related_articles(): {e}")
        return []

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
        related_html = "<div><p><strong>Related</strong></p><ul>"
        for item in related_articles:
            related_html += f'<li><a href="{item["published_url"]}">{item["post_title"]}</a></li>'
        related_html += "</ul></div>"
        blocks.append(related_html)
    if author_bio:
        blocks.append(f"<div>{author_bio.strip()}</div>")
    return "\n".join(blocks).strip() if blocks else None

def parse_delimited_response(raw_response):
    expected_sections = {
        "focus_keyphrase": "",
        "seo_title": "",
        "seo_description": "",
        "tags": "",
        "article_html": "",
        "image_filename": "",
        "image_alt_text": "",
        "image_caption": ""
    }
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


def generate_article_and_metadata(article_data, persona_df, published_df, related_articles, system_prompt):
    title = article_data.get("post_title", "")
    tier = article_data.get("tier", "")
    author = article_data.get("author", "")
    min_words = {"Tier 1": 1400, "Tier 2": 1100, "Tier 3": 900}.get(tier, 1100)
    flair_list = select_flair(author)

    persona = get_author_persona(persona_df, author)
    author_bio = persona["bio"] if tier in ["Tier 1", "Tier 2"] else None

    image_instruction = (
        "after_intro" if random.random() < 0.5 else f"after_section_{random.choice([2, 3, 4])}"
    )

    # Persona block injection
    persona_block = f"""
🎨 Persona and Flair Instructions

Write in the voice of **{persona['name']}**, a {persona['city']}-based expert in {persona['specialty'].lower()}.
Use a tone that is {persona['tone'].lower()}. Reflect their background, communication style, and local knowledge.
"""
    if flair_list:
        persona_block += "\nApply the following flair styles naturally and consistently throughout the article:\n"
        for flair in flair_list:
            persona_block += f"- **{flair}**: {FLAIR_GLOSSARY.get(flair, '')}\n"
        persona_block += "\nOnly use the flair types listed above — do not invent or add others."
    else:
        persona_block += "\nNo flair styles are included. Write cleanly and clearly without embellishments."

    system_prompt = system_prompt.replace("🎨 Persona and Flair Instructions", persona_block.strip())

    user_prompt = {
        "title": title,
        "city": article_data.get("city", ""),
        "category": article_data.get("category", ""),
        "tier": tier,
        "internal_links": article_data.get("internal_links", []),
        "focus_keyphrase": "",
        "seo_title": "",
        "seo_description": "",
        "tags": "",
        "min_word_count": min_words,
        "flair_styles": flair_list,
        "author_persona": author,
        "related_articles": related_articles
    }

    def run_gpt(messages):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ GPT API Error: {e}")
            return None

    def validate_and_process(raw_output):
        parsed = parse_delimited_response(raw_output)
        html = parsed.get("article_html", "")
        if not html.strip():
            return None, 0

        word_count = len(re.sub(r"<[^>]+>", "", html).split())

        image_tag = f"""
<figure>
<img src="{parsed.get('image_filename')}" alt="{parsed.get('image_alt_text')}">
<figcaption>{parsed.get('image_caption')}</figcaption>
</figure>
""".strip()

        if image_instruction == "after_intro":
            html = re.sub(r"(<p>.*?</p>)", r"\1\n" + image_tag, html, count=1, flags=re.DOTALL)
        elif "after_section_" in image_instruction:
            section_number = int(image_instruction.split("_")[-1])
            matches = list(re.finditer(r"<h2>.*?</h2>", html))
            if len(matches) >= section_number:
                insert_pos = matches[section_number - 1].end()
                html = html[:insert_pos] + "\n" + image_tag + html[insert_pos:]
            else:
                html += "\n" + image_tag

        footer_html = build_article_footer(related_articles, author_bio)
        if footer_html:
            html = html.replace("<article_footer_html>", footer_html)

        flair_used = len([f for f in flair_list if f in html])

        parsed.update({
            "article_html": html,
            "flair_styles": flair_list,
            "flair_requested": len(flair_list),
            "flair_used": flair_used,
            "image_placement": image_instruction,
            "word_count": word_count,
        })

        return parsed, word_count

    # Call GPT
    print("=== SYSTEM PROMPT ===\n", system_prompt)
    print("=== USER PROMPT ===\n", json.dumps(user_prompt, indent=2))

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt)}
    ]
    raw_output = run_gpt(messages)
    parsed, word_count = validate_and_process(raw_output)

    if parsed and word_count >= min_words:
        print(f"✅ Article word count: {word_count} (Tier minimum: {min_words})")
        return parsed

    print(f"❌ Article too short — only {word_count} words (min: {min_words}). Flagging for rewrite.")

    if parsed:
        parsed["rewrite"] = "yes"
        parsed["notes"] = f"Returned only {word_count} words (Tier minimum: {min_words})"
        parsed["status"] = "Draft"
        parsed["uuid"] = article_data["uuid"]
        parsed["post_title"] = article_data["post_title"]
        parsed["city"] = article_data["city"]
        parsed["category"] = article_data["category"]
        return parsed

    return None
    

def save_article_to_planning(row_index, article_data, gpt_output, planning_path):
    import re
    df = pd.read_excel(planning_path, dtype={"rewrite": str})

    article_html = gpt_output.get("article_html", "")
    flair_used = gpt_output.get("flair_used", 0)
    flair_requested = gpt_output.get("flair_requested", 0)
    image_placement = article_data.get("image_placement", "")
    tier = article_data.get("tier", "")
    min_words = {"Tier 1": 1400, "Tier 2": 1100, "Tier 3": 900}.get(tier, 1100)
    word_count = len(re.findall(r'\b\w+\b', article_html))

    notes_block = f"word_count:{word_count}/{min_words}; flair_used:{flair_used}/{flair_requested}; image_placement:{image_placement}".strip()

    for field in ["article_html", "focus_keyphrase", "seo_title", "seo_description",
                  "tags", "image_filename", "image_caption", "image_alt_text"]:
        value = gpt_output.get(field)
        if isinstance(value, list):
            value = ", ".join(value)
        elif pd.isna(value):
            value = ""
        else:
            value = str(value)
        df.at[row_index, field] = value

    # Add metadata fields
    df.at[row_index, "notes"] = notes_block
    thresholds = {"Tier 1": 0.85, "Tier 2": 0.80, "Tier 3": 0.75}
    threshold = thresholds.get(tier, 0.80)
    rewrite_flag = "yes" if word_count < int(min_words * threshold) else "no"
    df.at[row_index, "rewrite"] = str(rewrite_flag)
    df.at[row_index, "status"] = "Draft"

    # Save changes
    df.to_excel(planning_path, index=False)
    print("✅ Article and metadata saved to planning.xlsx as 'Draft'")

    
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

