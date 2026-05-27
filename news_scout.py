# ============================================================
#  news_scout.py — searches for awards ceremony results
# ============================================================

import requests
from datetime import datetime, timedelta
from config import NEWS_API_KEY

BASE_URL = "https://newsapi.org/v2/everything"

# Search queries for each awards show
SEARCH_QUERIES = {
    "Oscars":        ["Oscar winners 2027"],
    "Emmys":         ["Emmy winners 2026"],
    "Grammys":       ["Grammy winners 2027"],
    "Golden Globes": ["Golden Globes winners 2027"],
    "MTV VMAs":      ["VMA winners 2026"],
    "GTA 6":         ["GTA 6 release"],
}


def fetch_recent_news(show: str, hours_back: int = 25) -> list[dict]:
    """
    Fetch recent news articles related to an awards show.
    Returns list of articles with title, description, url, publishedAt.
    """
    if NEWS_API_KEY == "your-newsapi-key-here":
        return _demo_articles(show)

    queries = SEARCH_QUERIES.get(show, [show])
    articles = []
    since = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for query in queries:
        try:
            resp = requests.get(BASE_URL, params={
                "q":        query,
                "from":     since,
                "sortBy":   "publishedAt",
                "language": "en",
                "pageSize": 5,
                "apiKey":   NEWS_API_KEY,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"  [NewsAPI error for '{query}']: {e}")

    # Deduplicate by URL
    seen, unique = set(), []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    return unique


def fetch_all_shows() -> dict[str, list[dict]]:
    """Fetch news for all tracked shows. Returns dict of show → articles."""
    results = {}
    for show in SEARCH_QUERIES:
        articles = fetch_recent_news(show)
        if articles:
            results[show] = articles
            print(f"  Found {len(articles)} articles for {show}")
    return results


def _demo_articles(show: str) -> list[dict]:
    """Demo articles for testing without a NewsAPI key."""
    demos = {
        "Oscars": [
            {"title": "Oscars 2027: Complete list of winners", "description": "Adrien Brody wins Best Actor for The Brutalist. The Brutalist wins Best Picture. Demi Moore wins Best Actress for The Substance.", "url": "https://example.com/oscars", "publishedAt": datetime.utcnow().isoformat()},
        ],
        "Emmys": [
            {"title": "Emmy Awards 2026 Winners", "description": "The Bear wins Best Comedy Series. Shōgun wins Best Drama Series. Disclaimer wins Best Limited Series.", "url": "https://example.com/emmys", "publishedAt": datetime.utcnow().isoformat()},
        ],
        "Grammys": [
            {"title": "Grammy winners 2027", "description": "Beyoncé wins Album of the Year for Cowboy Carter. Kendrick Lamar wins Record of the Year for Not Like Us.", "url": "https://example.com/grammys", "publishedAt": datetime.utcnow().isoformat()},
        ],
        "Golden Globes": [
            {"title": "Golden Globes 2027 results", "description": "Conclave wins Best Picture Drama. Shōgun wins Best TV Series Drama.", "url": "https://example.com/globes", "publishedAt": datetime.utcnow().isoformat()},
        ],
    }
    return demos.get(show, [])
