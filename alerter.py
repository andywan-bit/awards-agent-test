import json
import os
import requests
from datetime import datetime, timezone

SENT_LOG       = "/tmp/sent_alerts.json"
SENDGRID_KEY   = os.environ.get("SENDGRID_API_KEY")
ALERT_FROM     = os.environ.get("GMAIL_USER")
ALERT_TO_EMAIL = os.environ.get("ALERT_TO_EMAIL", ALERT_FROM)
ALERTS_ENABLED = os.environ.get("ALERTS_ENABLED", "true").lower() in {"1","true","yes"}


def utc_now():
    return datetime.now(timezone.utc)

def load_sent_alerts():
    try:
        with open(SENT_LOG) as f: return json.load(f)
    except: return {}

def save_sent_alert(nominee, edge):
    log = load_sent_alerts()
    log[nominee] = {"edge": edge, "sent_at": utc_now().isoformat()}
    with open(SENT_LOG, "w") as f: json.dump(log, f, indent=2)

def already_alerted(nominee, current_edge):
    log = load_sent_alerts()
    if nominee not in log: return False
    return abs(current_edge - log[nominee]["edge"]) < 5.0

def format_email(edges):
    subject = f"Awards Scanner — {len(edges)} Edge{'s' if len(edges) > 1 else ''} Found"
    body = "Awards Market Scanner — Edge Alert\n"
    body += "=" * 50 + "\n\n"
    for e in edges:
        sign = "+" if e["edge"] >= 0 else ""
        body += f"* {e['show']} | {e['category']}\n"
        body += f"  Nominee:    {e['nominee']}\n"
        body += f"  Model:      {e['model_prob']}%\n"
        body += f"  Kalshi:     {e['kalshi_prob']}c\n"
        body += f"  Edge:       {sign}{e['edge']}%\n"
        body += f"  Confidence: {e['confidence']}\n\n"
    body += "=" * 50 + "\n"
    body += "Check your dashboard for full reasoning."
    return subject, body

def send_email(subject, body):
    if not ALERTS_ENABLED:
        print("  [Email] Alerts disabled")
        return False
    if not SENDGRID_KEY:
        print("  [Email] No SendGrid key — skipping")
        return False
    if not ALERT_FROM:
        print("  [Email] No GMAIL_USER set — skipping")
        return False
    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": ALERT_TO_EMAIL}]}],
                "from": {"email": ALERT_FROM},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=15,
        )
        if resp.status_code == 202:
            print(f"  ✓ Email sent to {ALERT_TO_EMAIL}")
            return True
        else:
            print(f"  [Email error]: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"  [Email error]: {e}")
        return False

def alert_on_edges(edges):
    new_edges = [e for e in edges if not already_alerted(e["nominee"], e["edge"])]
    if not new_edges:
        print("  No new edges to alert on.")
        return
    print(f"  Sending email for {len(new_edges)} edge(s)...")
    subject, body = format_email(new_edges)
    success = send_email(subject, body)
    if success:
        for e in new_edges:
            save_sent_alert(e["nominee"], e["edge"])
