# ============================================================
#  config.py — keys are loaded from environment variables
#  so they never appear in your code or GitHub
# ============================================================

import os

# ── Anthropic (Claude) ───────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your-anthropic-key-here")

# ── NewsAPI ──────────────────────────────────────────────────
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "your-newsapi-key-here")

# ── Twilio (SMS alerts) ──────────────────────────────────────
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "your-twilio-sid-here")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN",  "your-twilio-token-here")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "+1XXXXXXXXXX")
TWILIO_TO_NUMBER   = os.environ.get("TWILIO_TO_NUMBER",   "+1XXXXXXXXXX")

# ── Kalshi ───────────────────────────────────────────────────
KALSHI_API_KEY  = os.environ.get("KALSHI_API_KEY", "")
KALSHI_KEY_ID   = os.environ.get("KALSHI_KEY_ID", "")
KALSHI_BASE_URL = os.environ.get(
    "KALSHI_BASE_URL",
    "https://external-api.kalshi.com/trade-api/v2",
).rstrip("/")
KALSHI_USE_DEMO_DATA = os.environ.get("KALSHI_USE_DEMO_DATA", "").lower() in {
    "1",
    "true",
    "yes",
}
KALSHI_AUTH_PUBLIC_READS = os.environ.get("KALSHI_AUTH_PUBLIC_READS", "").lower() in {
    "1",
    "true",
    "yes",
}
KALSHI_SEARCH_TERMS = {
    "Oscars": "oscar",
    "Emmys": "emmy",
    "Golden Globes": "golden globe",
    "Grammys": "grammy",
}
KALSHI_SERIES_BY_SHOW_CATEGORY = {
    ("Oscars", "Best Picture"): "KXOSCARPIC",
    ("Oscars", "Best Actor"): "KXOSCARACTO",
    ("Oscars", "Best Actress"): "KXOSCARACTR",
    ("Oscars", "Best Director"): "KXOSCARDIR",
    ("Oscars", "Best Intl. Film"): "KXOSCARINTLFILM",
    ("Emmys", "Best Drama Series"): "KXEMMYDSERIES",
    ("Emmys", "Best Comedy Series"): "KXEMMYCSERIES",
    ("Emmys", "Best Limited Series"): "KXEMMYLSERIES",
    ("Golden Globes", "Best Picture – Drama"): "KXGGDRAMAFILM",
    ("Golden Globes", "Best TV Series – Drama"): "KXGGDRAMATV",
    ("Grammys", "Album of the Year"): "KXGRAMAOTY",
    ("Grammys", "Record of the Year"): "KXGRAMROTY",
}

# ── GitHub (auto-updates data) ───────────────────────────────
GITHUB_TOKEN     = os.environ.get("GITHUB_TOKEN",     "your-github-token-here")
GITHUB_REPO      = os.environ.get("GITHUB_REPO",      "andywan-bit/awards-repository")
GITHUB_FILE_PATH = os.environ.get("GITHUB_FILE_PATH", "opportunities.py")

# ── Agent settings ───────────────────────────────────────────
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", 60))
EDGE_ALERT_THRESHOLD   = int(os.environ.get("EDGE_ALERT_THRESHOLD", 10))
MIN_CONFIDENCE         = os.environ.get("MIN_CONFIDENCE", "medium")
