# ============================================================
#  ai_parser.py — uses Claude API to extract award results
#  from news articles into structured data
# ============================================================

import json
import requests
from config import ANTHROPIC_API_KEY

API_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key":         ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "messages-2023-12-15",
    "content-type":      "application/json",
}

SYSTEM_PROMPT = """You are an awards data extractor. Given news articles about awards ceremonies,
extract the winners into structured JSON.

Return ONLY a JSON array, no other text. Each item should have:
{
  "nominee": "exact name of winner (person or film/show title)",
  "show": "Oscars|Emmys|Grammys|Golden Globes|MTV VMAs",
  "category": "exact category name e.g. Best Picture, Best Actor, Album of the Year",
  "result": "won",
  "confidence": "high|medium|low"
}

Rules:
- Only include confirmed winners, not nominees or predictions
- If an article is about predictions/odds (not actual results), return []
- Use "won" for result only when the ceremony has actually happened
- confidence = high if the article clearly states the winner
- confidence = low if it's ambiguous or a rumor
"""


def parse_articles_for_winners(show: str, articles: list[dict]) -> list[dict]:
    """
    Send articles to Claude and extract structured winner data.
    Returns list of winner dicts.
    """
    if not articles:
        return []

    if ANTHROPIC_API_KEY == "your-anthropic-key-here":
        return _demo_winners(show)

    # Combine article texts
    article_text = ""
    for a in articles[:5]:   # max 5 articles to stay within token limits
        article_text += f"\nTitle: {a.get('title', '')}\n"
        article_text += f"Description: {a.get('description', '')}\n"
        article_text += "---\n"

    prompt = f"Extract award winners from these {show} articles:\n\n{article_text}"

    try:
        resp = requests.post(API_URL, headers=HEADERS, json={
            "model":      "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system":     SYSTEM_PROMPT,
            "messages":   [{"role": "user", "content": prompt}],
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        raw = data["content"][0]["text"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        winners = json.loads(raw)
        print(f"  Claude extracted {len(winners)} winners from {show} articles")
        return winners

    except json.JSONDecodeError:
        print(f"  [Parser] Claude returned non-JSON for {show} — skipping")
        return []
    except Exception as e:
        print(f"  [Parser error for {show}]: {e}")
        return []


def parse_all_shows(news_by_show: dict[str, list[dict]]) -> list[dict]:
    """Parse all shows and return combined list of winners."""
    all_winners = []
    for show, articles in news_by_show.items():
        print(f"  Parsing {show} articles with Claude...")
        winners = parse_articles_for_winners(show, articles)
        all_winners.extend(winners)
    return all_winners


def _demo_winners(show: str) -> list[dict]:
    """Demo winners for testing without API key."""
    demos = {
        "Oscars": [
            {"nominee": "The Brutalist",  "show": "Oscars", "category": "Best Picture", "result": "won", "confidence": "high"},
            {"nominee": "Adrien Brody",   "show": "Oscars", "category": "Best Actor",   "result": "won", "confidence": "high"},
        ],
        "Emmys": [
            {"nominee": "The Bear",       "show": "Emmys",  "category": "Best Comedy Series", "result": "won", "confidence": "high"},
        ],
    }
    return demos.get(show, [])
