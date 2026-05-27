import base64
import datetime
import os
import time
from functools import lru_cache
from urllib.parse import urlparse

import requests

from config import (
    KALSHI_API_KEY,
    KALSHI_BASE_URL,
    KALSHI_KEY_ID,
    KALSHI_SEARCH_TERMS,
    KALSHI_SERIES_BY_SHOW_CATEGORY,
    KALSHI_USE_DEMO_DATA,
)


def _load_private_key(pem_or_path: str):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    key_material = pem_or_path
    if os.path.exists(pem_or_path):
        with open(pem_or_path, "r", encoding="utf-8") as f:
            key_material = f.read()

    key_material = key_material.replace("\\n", "\n")
    return serialization.load_pem_private_key(
        key_material.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )


def _sign_request(private_key, timestamp_ms: str, method: str, path: str) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    path_without_query = path.split("?", 1)[0]
    msg = timestamp_ms + method.upper() + path_without_query
    signature = private_key.sign(
        msg.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _auth_headers(method: str, url: str) -> dict:
    if not KALSHI_API_KEY or not KALSHI_KEY_ID:
        return {}

    timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))
    path = urlparse(url).path
    private_key = _load_private_key(KALSHI_API_KEY)
    return {
        "KALSHI-ACCESS-KEY": KALSHI_KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": _sign_request(private_key, timestamp_ms, method, path),
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "Content-Type": "application/json",
    }


def _request(method: str, endpoint: str, **kwargs) -> dict:
    endpoint = "/" + endpoint.lstrip("/")
    url = KALSHI_BASE_URL + endpoint
    headers = kwargs.pop("headers", {})
    headers.update(_auth_headers(method, url))

    for attempt in range(3):
        resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        if resp.status_code != 429 or attempt == 2:
            resp.raise_for_status()
            return resp.json()

        retry_after = resp.headers.get("Retry-After")
        delay = float(retry_after) if retry_after else 1.5 * (attempt + 1)
        time.sleep(delay)

    return {}


def _market_price(market: dict) -> int | None:
    if market.get("kalshi_prob") is not None:
        return int(round(market["kalshi_prob"]))

    for field in ("yes_ask", "yes_bid", "last_price"):
        price = market.get(field)
        if price is not None:
            return int(round(price))

    for field in ("yes_ask_dollars", "yes_bid_dollars", "last_price_dollars"):
        price = market.get(field)
        if price is not None:
            return int(round(float(price) * 100))

    return None


def _market_text(market: dict) -> str:
    parts = [
        market.get("ticker", ""),
        market.get("event_ticker", ""),
        market.get("title", ""),
        market.get("subtitle", ""),
        market.get("yes_sub_title", ""),
        market.get("no_sub_title", ""),
    ]
    return " ".join(str(p).lower() for p in parts if p)


def _series_text(series: dict) -> str:
    parts = [
        series.get("ticker", ""),
        series.get("title", ""),
        series.get("category", ""),
        " ".join(series.get("tags") or []),
    ]
    return " ".join(str(p).lower() for p in parts if p)


@lru_cache(maxsize=1)
def fetch_entertainment_series() -> list[dict]:
    data = _request(
        "GET",
        "/series",
        params={"category": "Entertainment", "include_volume": "true"},
    )
    return data.get("series") or []


@lru_cache(maxsize=1)
def fetch_open_markets() -> list[dict]:
    markets = []
    cursor = None
    max_pages = int(os.environ.get("KALSHI_MARKET_SCAN_PAGES", "5"))

    for _ in range(max_pages):
        params = {"status": "open", "limit": 1000}
        if cursor:
            params["cursor"] = cursor

        data = _request("GET", "/markets", params=params)
        markets.extend(data.get("markets", []))
        cursor = data.get("cursor")
        if not cursor:
            break

    return markets


@lru_cache(maxsize=256)
def fetch_markets_for_series(series_ticker: str) -> list[dict]:
    data = _request(
        "GET",
        "/markets",
        params={
            "series_ticker": series_ticker,
            "status": "open",
            "limit": 1000,
        },
    )
    return data.get("markets") or []


@lru_cache(maxsize=16)
def fetch_markets_for_show(show: str) -> list[dict]:
    search_term = KALSHI_SEARCH_TERMS.get(show, show).lower()
    results = []
    scan_series = os.environ.get("KALSHI_SCAN_AWARD_SERIES", "").lower() in {
        "1",
        "true",
        "yes",
    }
    max_series = int(os.environ.get("KALSHI_AWARD_SERIES_SCAN_LIMIT", "25"))

    try:
        series_tickers = sorted({
            ticker
            for (mapped_show, _), ticker in KALSHI_SERIES_BY_SHOW_CATEGORY.items()
            if mapped_show == show
        })

        if scan_series:
            discovered = [
                s.get("ticker", "")
                for s in fetch_entertainment_series()
                if search_term in _series_text(s)
            ][:max_series]
            series_tickers.extend(t for t in discovered if t and t not in series_tickers)

        for series_ticker in series_tickers:
            for market in fetch_markets_for_series(series_ticker):
                price = _market_price(market)
                if price is None:
                    continue

                market = dict(market)
                market["id"] = market.get("ticker", "")
                market["kalshi_prob"] = price
                market["show"] = show
                results.append(market)

        if results:
            return results

        for market in fetch_open_markets():
            if search_term in _market_text(market):
                price = _market_price(market)
                if price is not None:
                    market = dict(market)
                    market["id"] = market.get("ticker", "")
                    market["kalshi_prob"] = price
                    market["show"] = show
                    results.append(market)
        return results
    except Exception as e:
        print(f"  [Kalshi error for {show}]: {e}")
        return []


def fetch_kalshi_price(nominee: str, show: str | None = None, category: str | None = None) -> int | None:
    if KALSHI_USE_DEMO_DATA:
        from edge_detector import DEMO_KALSHI
        return DEMO_KALSHI.get(nominee)

    try:
        nominee_key = nominee.lower().split("–", 1)[0].strip()
        show_key = KALSHI_SEARCH_TERMS.get(show, show or "").lower()
        category_key = (category or "").lower()
        series_ticker = KALSHI_SERIES_BY_SHOW_CATEGORY.get((show, category))

        best_match = None
        best_score = -1

        if series_ticker:
            markets = fetch_markets_for_series(series_ticker)
        elif show:
            markets = fetch_markets_for_show(show)
        else:
            markets = fetch_open_markets()

        for market in markets:
            text = _market_text(market)
            if nominee_key not in text:
                continue

            score = 10
            if show_key and show_key in text:
                score += 5
            if category_key and any(word in text for word in category_key.split()):
                score += 2

            if score > best_score:
                best_match = market
                best_score = score

        if best_match:
            return _market_price(best_match)
    except Exception as e:
        print(f"  [Kalshi fetch error for '{nominee}']: {e}")

    return None


def fetch_all_award_markets() -> list[dict]:
    if KALSHI_USE_DEMO_DATA:
        print("  KALSHI_USE_DEMO_DATA enabled - using demo data")
        from edge_detector import DEMO_KALSHI
        return [{"nominee": k, "kalshi_prob": v, "show": "", "category": ""}
                for k, v in DEMO_KALSHI.items()]

    all_markets = []
    for show in KALSHI_SEARCH_TERMS:
        print(f"  Fetching Kalshi markets for {show}...")
        all_markets.extend(fetch_markets_for_show(show))
    return all_markets
