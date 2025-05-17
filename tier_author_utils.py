# tier_author_utils.py
# Assigns Tier and Author based on title and category

import random

CATEGORY_AUTHOR_POOLS = {
    "gardening": ["tina-delgado", "sofia-vargas", "ramon-ellis"],
    "vegetable-gardening": ["sofia-vargas", "priya-shah"],
    "landscaping": ["ramon-ellis", "marcus-wynn"],
    "irrigation-watering": ["derek-holt", "priya-shah"],
    "lawn-care": ["derek-holt", "marcus-wynn"],
    "pest-control": ["marcus-wynn", "ramon-ellis"],
    "monthly-checklists": ["tina-delgado", "marcus-wynn"],
    "newsletter": ["tina-delgado", "sofia-vargas"],
    "composting": ["sofia-vargas", "priya-shah"],
    "tree-shrub-care": ["tina-delgado", "marcus-wynn"],
    "outdoor-living": ["ramon-ellis", "sofia-vargas"],
    "tool-maintenance": ["ramon-ellis", "derek-holt"],
    "wildlife-pollinators": ["tina-delgado", "priya-shah"],
    "hardscaping": ["ramon-ellis", "marcus-wynn"],
    "seasonal-decor-lighting": ["sofia-vargas", "ramon-ellis"],
    "yard-planning-design": ["tina-delgado", "ramon-ellis"],
    "rain-storm-management": ["priya-shah", "marcus-wynn"],
    "yard-care": ["sofia-vargas", "ramon-ellis"],
}

def assign_tier_and_author(title, category_slug):
    """
    Assign a Tier and Author based on title content and category.

    NOTE: Tier assignment is provisional. All articles default to Tier 1 for maximum depth.
    A scheduled reassessment will update tiers ~90 days post-publish based on actual word count and depth.
    """

    # === Tier Assignment ===
    # Default to Tier 1 to encourage GPT to generate rich, in-depth content.
    tier = "1"

    # === Author Assignment ===
    # Pull from topic-based author pool. Fallback to Marcus Wynn if no match.
    author_pool = CATEGORY_AUTHOR_POOLS.get(category_slug, ["marcus-wynn"])
    author = random.choice(author_pool)

    return tier, author