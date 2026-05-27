# ============================================================
#  data_updater.py — applies winner data to opportunities.py
#  and pushes the update to GitHub automatically
# ============================================================

import re
import json
import base64
import requests
from datetime import datetime
from config import GITHUB_TOKEN, GITHUB_REPO, GITHUB_FILE_PATH

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}


def fetch_current_file() -> tuple[str, str]:
    """
    Fetch the current opportunities.py from GitHub.
    Returns (content, sha) — sha needed to update the file.
    """
    if GITHUB_TOKEN == "your-github-token-here":
        print("  [GitHub] No token set — skipping auto-update")
        return None, None

    try:
        resp = requests.get(GITHUB_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]
    except Exception as e:
        print(f"  [GitHub fetch error]: {e}")
        return None, None


def apply_winner_to_content(content: str, winner: dict) -> tuple[str, bool]:
    """
    Given the file content and a winner dict, update the relevant
    precursor fields in PRECURSOR_DATA.
    Returns (updated_content, was_changed).
    """
    nominee  = winner["nominee"]
    category = winner["category"].lower()
    show     = winner["show"]

    # Map category to the field name in PRECURSOR_DATA
    field_map = {
        "best actor":          "sag_win",
        "best actress":        "sag_win",
        "best picture":        "bafta_win",
        "best film":           "bafta_win",
        "best drama series":   "sag_win",
        "best comedy series":  "sag_win",
        "album of the year":   "social_volume",
        "record of the year":  "social_volume",
    }

    # Determine which precursor field to update based on show + category
    if "sag" in show.lower():
        field = "sag_win"
    elif "bafta" in show.lower():
        field = "bafta_win"
    elif "critics choice" in show.lower():
        field = "critics_choice"
    else:
        # For the main ceremony, mark the overall win
        field = field_map.get(category, None)

    if not field:
        print(f"  [Updater] No field mapping for category '{category}' — skipping")
        return content, False

    # Find the nominee block and update the field
    # Look for the nominee name in quotes followed by their data block
    pattern = rf'("{re.escape(nominee)}")\s*:\s*\{{[^}}]+\}}'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print(f"  [Updater] Nominee '{nominee}' not found in data — skipping")
        return content, False

    block = match.group(0)

    # Update the specific field within the block
    # Match: "field_name": True/False/None/0.XX
    field_pattern = rf'("{re.escape(field)}":\s*)(True|False|None|[\d.]+)'
    field_match = re.search(field_pattern, block)

    if not field_match:
        print(f"  [Updater] Field '{field}' not found for '{nominee}' — skipping")
        return content, False

    old_value = field_match.group(2)
    new_value = "True"   # winner → True

    if old_value == new_value:
        print(f"  [Updater] '{nominee}' {field} already True — no change needed")
        return content, False

    new_block = block.replace(
        field_match.group(0),
        field_match.group(1) + new_value
    )
    updated = content.replace(block, new_block)
    print(f"  ✓ Updated '{nominee}' {field}: {old_value} → {new_value}")
    return updated, True


def push_update_to_github(content: str, sha: str, winners: list[dict]) -> bool:
    """Push updated opportunities.py back to GitHub."""
    if GITHUB_TOKEN == "your-github-token-here":
        return False

    names = ", ".join(w["nominee"] for w in winners)
    commit_message = f"Agent update: {names} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"

    try:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        resp = requests.put(GITHUB_API, headers=HEADERS, json={
            "message": commit_message,
            "content": encoded,
            "sha":     sha,
        }, timeout=15)
        resp.raise_for_status()
        print(f"  ✓ Pushed to GitHub: {commit_message}")
        return True
    except Exception as e:
        print(f"  [GitHub push error]: {e}")
        return False


def apply_winners(winners: list[dict]) -> bool:
    """
    Main function: fetch file, apply all winners, push back.
    Returns True if any changes were made.
    """
    if not winners:
        return False

    content, sha = fetch_current_file()
    if content is None:
        return False

    changed_winners = []
    for winner in winners:
        updated_content, changed = apply_winner_to_content(content, winner)
        if changed:
            content = updated_content
            changed_winners.append(winner)

    if changed_winners:
        return push_update_to_github(content, sha, changed_winners)

    print("  No data changes needed.")
    return False
