# ============================================================
#  agent.py — main agent loop with ops logging
# ============================================================

import sys
import time
import json
import os
from datetime import datetime

from news_scout    import fetch_all_shows
from ai_parser     import parse_all_shows
from data_updater  import apply_winners
from edge_detector import find_edges
from alerter       import alert_on_edges
from config        import CHECK_INTERVAL_MINUTES

STATE_FILE   = "/tmp/agent_state.json"
OPS_LOG_FILE = "/tmp/ops_log.json"

PRECURSOR_DATA = {
    "The Brutalist":               {"show":"Oscars",       "category":"Best Picture",          "sag_win":False,"bafta_win":True, "critics_choice":True, "guild_noms":3,"rt_score":89,"social_volume":0.72},
    "Adrien Brody":                {"show":"Oscars",       "category":"Best Actor",             "sag_win":True, "bafta_win":True, "critics_choice":True, "guild_noms":0,"rt_score":None,"social_volume":0.65},
    "Brady Corbet":                {"show":"Oscars",       "category":"Best Director",          "sag_win":None, "bafta_win":False,"critics_choice":False,"guild_noms":2,"rt_score":89,"social_volume":0.55},
    "Demi Moore":                  {"show":"Oscars",       "category":"Best Actress",           "sag_win":True, "bafta_win":False,"critics_choice":True, "guild_noms":0,"rt_score":None,"social_volume":0.48},
    "Emilia Pérez":                {"show":"Oscars",       "category":"Best Intl. Film",        "sag_win":None, "bafta_win":True, "critics_choice":True, "guild_noms":1,"rt_score":79,"social_volume":0.60},
    "The Day of the Jackal":       {"show":"Emmys",        "category":"Best Drama Series",      "sag_win":False,"bafta_win":None, "critics_choice":False,"guild_noms":2,"rt_score":93,"social_volume":0.58},
    "The Bear":                    {"show":"Emmys",        "category":"Best Comedy Series",     "sag_win":True, "bafta_win":None, "critics_choice":True, "guild_noms":3,"rt_score":98,"social_volume":0.80},
    "Disclaimer":                  {"show":"Emmys",        "category":"Best Limited Series",    "sag_win":False,"bafta_win":None, "critics_choice":False,"guild_noms":2,"rt_score":94,"social_volume":0.52},
    "Beyoncé – Cowboy Carter":     {"show":"Grammys",      "category":"Album of the Year",      "sag_win":None, "bafta_win":None, "critics_choice":None, "guild_noms":0,"rt_score":None,"social_volume":0.88,"metascore":90},
    "Kendrick Lamar – Not Like Us":{"show":"Grammys",      "category":"Record of the Year",     "sag_win":None, "bafta_win":None, "critics_choice":None, "guild_noms":0,"rt_score":None,"social_volume":0.95},
    "Conclave":                    {"show":"Golden Globes","category":"Best Picture – Drama",   "sag_win":False,"bafta_win":False,"critics_choice":True, "guild_noms":2,"rt_score":92,"social_volume":0.62},
    "Shōgun":                      {"show":"Golden Globes","category":"Best TV Series – Drama", "sag_win":True, "bafta_win":None, "critics_choice":True, "guild_noms":3,"rt_score":99,"social_volume":0.75},
}


def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {"last_run":None,"runs_completed":0,"winners_found":0,"alerts_sent":0}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f,indent=2)

def save_ops_log(log):
    with open(OPS_LOG_FILE,"w") as f: json.dump(log,f,indent=2,default=str)


def run_cycle(state):
    now     = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    started = datetime.utcnow().isoformat()
    ops     = {"cycle_started":started,"cycle_time":now,"steps":[],"edges":[],"winners_found":[],"alerts_sent":0,"status":"running"}
    save_ops_log(ops)

    print(f"\n{'='*60}\n  AGENT CYCLE — {now}\n{'='*60}")

    # Step 1: news
    print("\n[1/4] Scouting for awards news...")
    ops["steps"].append({"step":1,"name":"News scout","status":"running","started":datetime.utcnow().isoformat()})
    save_ops_log(ops)
    news = fetch_all_shows()
    article_count = sum(len(v) for v in news.values())
    ops["steps"][-1].update({"status":"done","articles_found":article_count,"shows_searched":list(news.keys())})
    save_ops_log(ops)
    print(f"  Found {article_count} articles across {len(news)} shows")

    # Step 2: parse
    print("\n[2/4] Parsing with Claude AI...")
    ops["steps"].append({"step":2,"name":"AI parser","status":"running","started":datetime.utcnow().isoformat()})
    save_ops_log(ops)
    winners = parse_all_shows(news)
    ops["steps"][-1].update({"status":"done","winners_extracted":len(winners)})
    ops["winners_found"] = winners
    save_ops_log(ops)
    print(f"  Extracted {len(winners)} winners")

    # Step 3: update
    print("\n[3/4] Updating GitHub data...")
    ops["steps"].append({"step":3,"name":"Data updater","status":"running","started":datetime.utcnow().isoformat()})
    save_ops_log(ops)
    updated = False
    if winners:
        updated = apply_winners(winners)
        state["winners_found"] = state.get("winners_found",0) + len(winners)
    ops["steps"][-1].update({"status":"done","github_updated":updated})
    save_ops_log(ops)

    # Step 4: edges
    print("\n[4/4] Scanning Kalshi edges...")
    ops["steps"].append({"step":4,"name":"Edge scanner","status":"running","started":datetime.utcnow().isoformat()})
    save_ops_log(ops)
    edges = find_edges(PRECURSOR_DATA)
    ops["steps"][-1].update({"status":"done","edges_found":len(edges)})
    ops["edges"] = edges
    save_ops_log(ops)

    if edges:
        print(f"  Found {len(edges)} edge(s):")
        for e in edges:
            print(f"    * {e['nominee']} — +{e['edge']}%")
        alert_on_edges(edges)
        ops["alerts_sent"] = 1
        state["alerts_sent"] = state.get("alerts_sent",0) + 1

    state["last_run"]       = now
    state["runs_completed"] = state.get("runs_completed",0) + 1
    ops["status"]           = "complete"
    ops["cycle_ended"]      = datetime.utcnow().isoformat()
    ops["total_runs"]       = state["runs_completed"]
    save_ops_log(ops)
    print(f"\n  Cycle complete. Total runs: {state['runs_completed']}\n")
    return state


def run_once():
    s = load_state(); s = run_cycle(s); save_state(s)

def run_watch():
    print(f"\n  Agent starting — checking every {CHECK_INTERVAL_MINUTES} min. Ctrl+C to stop.\n")
    try:
        while True:
            s = load_state(); s = run_cycle(s); save_state(s)
            print(f"  Sleeping {CHECK_INTERVAL_MINUTES} minutes...\n")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        print("\n  Stopped.\n")

if __name__ == "__main__":
    run_watch() if "--watch" in sys.argv else run_once()
