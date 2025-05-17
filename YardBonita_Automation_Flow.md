
# 🪴 YardBonita Automation Flow

This document outlines the full content automation pipeline for YardBonita, starting with row creation and ending with article publication.

---

## 1. `start_process.py`

Ensures each day from **today** through **N future days** has up to **X planned articles**.

- Automatically adds new rows to `planning.xlsx`
- Populates: `uuid`, `publish_date`, `city` (rotating Gilbert, Chandler, Mesa, Queen Creek + Southeast Valley)
- All other fields are left blank for downstream scripts

**Usage:**
```bash
python3 start_process.py 4 30
```
- `4`: Max articles per day
- `30`: Number of future days to prepare

---

## 2. `title_creation.py`

Fills in critical metadata for each planned article:
- `post_title` (generated using GPT)
- `category` (inferred based on title/context)
- `author` (rotates based on city/persona)
- `tier` (automatically assigned using title/category logic)

**Triggered automatically after row creation**

---

## 3. `assign_outline.py`

Uses the title and tier to generate a full outline:
- Outline depth matches tier (Tier 1 = deep, Tier 3 = fast)
- Uses existing metadata (title, author, category, tier)
- GPT-powered, updates `outline` field in `planning.xlsx`

---

## 4. `generate_article.py`

Generates a complete article from the outline:
- Fills: `article_html`, `focus_keyphrase`, `seo_title`, `seo_description`, `tags`
- Includes image metadata: `image_prompt`, `image_caption`, `image_alt`
- Injects related links and author bio based on Tier
- Uses `utils.py` for core functions

---

## 5. `update_published_script.py`

Moves the article from `planning.xlsx` to `published.xlsx`:
- Accepts 14 arguments (including UUID, title, metadata, etc.)
- Ensures accurate publication history
- Final step in the publishing process

---

## Summary

```text
start_process.py  →  title_creation.py  →  assign_outline.py  →  generate_article.py  →  update_published_script.py
```

This pipeline enables fully automated, high-quality content generation across multiple cities and article tiers.
