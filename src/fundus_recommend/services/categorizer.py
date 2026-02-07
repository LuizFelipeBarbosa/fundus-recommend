import re

CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "US": {
        "topics": [
            "politics", "congress", "senate", "house of representatives",
            "white house", "supreme court", "election", "republican", "democrat",
            "gop", "legislation", "executive order",
        ],
        "keywords": [
            "washington", "republican", "democrat", "biden", "trump",
            "capitol", "senate", "congress", "presidential", "governor",
            "u.s. politics", "midterm", "electoral", "filibuster",
        ],
    },
    "Global": {
        "topics": [
            "world", "international", "foreign policy", "diplomacy",
            "geopolitics", "war", "conflict", "united nations",
            "nato", "middle east", "europe", "asia", "africa",
        ],
        "keywords": [
            "ukraine", "russia", "china", "nato", "united nations",
            "european union", "middle east", "gaza", "israel",
            "diplomacy", "sanctions", "refugee", "ceasefire", "treaty",
            "humanitarian", "embassy", "peacekeeping",
        ],
    },
    "Business": {
        "topics": [
            "business", "economy", "finance", "markets", "stock",
            "banking", "wall street", "trade", "inflation",
            "federal reserve", "gdp", "earnings",
        ],
        "keywords": [
            "stock market", "wall street", "earnings", "revenue",
            "profit", "quarterly", "investors", "fed", "interest rate",
            "inflation", "recession", "ipo", "merger", "acquisition",
            "startup", "valuation", "dow jones", "nasdaq", "s&p 500",
        ],
    },
    "Technology": {
        "topics": [
            "tech", "technology", "ai", "artificial intelligence",
            "software", "hardware", "cybersecurity", "crypto",
            "blockchain", "startup", "science", "space",
        ],
        "keywords": [
            "silicon valley", "openai", "nvidia", "google", "apple",
            "microsoft", "meta", "amazon", "artificial intelligence",
            "machine learning", "algorithm", "chip", "semiconductor",
            "robotics", "quantum", "spacex", "nasa", "satellite",
        ],
    },
    "Arts": {
        "topics": [
            "arts", "culture", "books", "literature", "museum",
            "theater", "theatre", "music", "classical", "opera",
            "film", "cinema", "photography", "painting",
        ],
        "keywords": [
            "exhibition", "gallery", "novel", "author", "pulitzer",
            "booker", "symphony", "orchestra", "broadway",
            "documentary", "festival", "curator", "sculpture",
        ],
    },
    "Sports": {
        "topics": [
            "sports", "football", "basketball", "baseball", "soccer",
            "tennis", "golf", "hockey", "nfl", "nba", "mlb",
            "olympics", "mls", "rugby", "cricket", "formula 1",
        ],
        "keywords": [
            "championship", "playoff", "tournament", "coach", "athlete",
            "stadium", "league", "super bowl", "world cup", "grand slam",
            "transfer", "draft", "season", "referee", "score",
        ],
    },
    "Entertainment": {
        "topics": [
            "entertainment", "celebrity", "tv", "television",
            "streaming", "hollywood", "pop culture", "fashion",
            "lifestyle", "gaming", "video games",
        ],
        "keywords": [
            "netflix", "disney", "hbo", "streaming", "oscar",
            "grammy", "emmy", "box office", "reality tv",
            "celebrity", "red carpet", "blockbuster", "sequel",
            "franchise", "viral", "tiktok", "influencer",
        ],
    },
}

# Priority order for category assignment
CATEGORY_PRIORITY = ["US", "Global", "Business", "Technology", "Arts", "Sports", "Entertainment"]


def assign_category(topics: list[str], title: str, body_snippet: str = "", title_en: str | None = None) -> str:
    """Assign a category based on topics, title, and body text using keyword matching.

    Checks topics first (substring match), then scans title + body for keywords.
    Uses title_en (English translation) for keyword matching when available.
    Returns the highest-priority matching category, or "General" if no match.
    """
    topics_lower = [t.lower() for t in topics]
    match_title = title_en or title
    text_lower = f"{match_title} {title} {body_snippet}".lower()

    scores: dict[str, int] = {}

    for category in CATEGORY_PRIORITY:
        cat_config = CATEGORY_KEYWORDS[category]
        score = 0

        # Check topic matches (weighted higher)
        for topic in topics_lower:
            for pattern in cat_config["topics"]:
                if pattern in topic:
                    score += 3
                    break

        # Check keyword matches in title + body
        for keyword in cat_config["keywords"]:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                score += 1

        if score > 0:
            scores[category] = score

    if not scores:
        return "General"

    # Return the category with the highest score; break ties by priority order
    return max(CATEGORY_PRIORITY, key=lambda c: scores.get(c, 0))
