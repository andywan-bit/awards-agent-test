# ============================================================
#  edge_detector.py — runs the model and finds Kalshi edges
# ============================================================

from config import EDGE_ALERT_THRESHOLD, MIN_CONFIDENCE, KALSHI_USE_DEMO_DATA
from kalshi_client import fetch_kalshi_price as fetch_live_kalshi_price, DEMO_KALSHI

SIGNAL_WEIGHTS = {
    "critics_choice": 0.413,
    "sag_win":        0.285,
    "social_volume":  0.091,
    "guild_noms":     0.091,
    "bafta_win":      0.086,
    "rt_score":       0.034,
}
SHOW_CONFIDENCE = {"Oscars": 1.0, "Emmys": 0.9, "Golden Globes": 0.85, "Grammys": 0.70}


def bool_to_signal(v):
    if v is True:  return 1.0
    if v is False: return 0.25
    return None

def rt_to_signal(s):
    if s is None: return None
    if s >= 95: return 1.0
    if s >= 90: return 0.85
    if s >= 80: return 0.70
    if s >= 70: return 0.55
    return 0.30

def guild_to_signal(n):
    if n is None: return None
    if n >= 4: return 1.0
    if n >= 3: return 0.85
    if n >= 2: return 0.70
    if n >= 1: return 0.50
    return 0.20


def calculate_probability(signals: dict) -> dict:
    show = signals.get("show", "Oscars")
    conf_mult = SHOW_CONFIDENCE.get(show, 1.0)
    raw = {
        "sag_win":        bool_to_signal(signals.get("sag_win")),
        "bafta_win":      bool_to_signal(signals.get("bafta_win")),
        "critics_choice": bool_to_signal(signals.get("critics_choice")),
        "guild_noms":     guild_to_signal(signals.get("guild_noms")),
        "rt_score":       rt_to_signal(signals.get("rt_score") or signals.get("metascore")),
        "social_volume":  signals.get("social_volume"),
    }
    available = {k: v for k, v in raw.items() if v is not None}
    if not available:
        return {"probability": 50.0, "confidence": "low", "signals_used": 0}
    total_w = sum(SIGNAL_WEIGHTS[k] for k in available)
    weighted_sum = sum((SIGNAL_WEIGHTS[k] / total_w) * v for k, v in available.items())
    squeezed = 0.05 + weighted_sum * 0.90
    dampened = 0.5 + (squeezed - 0.5) * conf_mult
    n = len(available)
    return {
        "probability": round(dampened * 100, 1),
        "confidence":  "high" if n >= 4 else "medium" if n >= 2 else "low",
        "signals_used": n,
    }


def fetch_kalshi_price(nominee: str, show: str | None = None, category: str | None = None) -> int | None:
    price = fetch_live_kalshi_price(nominee, show=show, category=category)
    if price is None and KALSHI_USE_DEMO_DATA:
        return DEMO_KALSHI.get(nominee)
    return price


def find_edges(precursor_data: dict) -> list[dict]:
    conf_order = {"high": 3, "medium": 2, "low": 1}
    min_conf   = conf_order.get(MIN_CONFIDENCE, 2)
    print(f"  [DEBUG] threshold={EDGE_ALERT_THRESHOLD}, min_conf={MIN_CONFIDENCE}, demo={KALSHI_USE_DEMO_DATA}")

    edges = []
    for nominee, signals in precursor_data.items():
        result = calculate_probability(signals)
        model_prob = result["probability"]
        confidence = result["confidence"]
        print(f"  [DEBUG] {nominee}: model={model_prob}%, conf={confidence}, signals={result['signals_used']}")

        if conf_order.get(confidence, 0) < min_conf:
            print(f"    skipped: confidence too low")
            continue

        kalshi_price = fetch_kalshi_price(
            nominee,
            show=signals.get("show"),
            category=signals.get("category"),
        )
        print(f"    kalshi_price={kalshi_price}")

        if kalshi_price is None:
            print(f"    skipped: no kalshi price")
            continue

        edge = round(model_prob - kalshi_price, 1)
        print(f"    edge={edge}")

        if edge >= EDGE_ALERT_THRESHOLD:
            edges.append({
                "nominee":     nominee,
                "show":        signals["show"],
                "category":    signals["category"],
                "model_prob":  model_prob,
                "kalshi_prob": kalshi_price,
                "edge":        edge,
                "confidence":  confidence,
            })
        else:
            print(f"    skipped: edge below threshold")

    edges.sort(key=lambda x: -x["edge"])
    return edges
