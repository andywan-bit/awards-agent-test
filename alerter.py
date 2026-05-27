# ============================================================
#  alerter.py — sends email alerts via Gmail SMTP
# ============================================================

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

SENT_LOG = "/tmp/sent_alerts.json"

GMAIL_USER     = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
ALERT_TO_EMAIL = os.environ.get("ALERT_TO_EMAIL", GMAIL_USER)


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
    subject = f"🎬 Awards Scanner — {len(edges)} Edge{'s' if len(edges) > 1 else ''} Found"
    body = "Awards Market Scanner — Edge Alert\n"
    body += "=" * 50 + "\n\n"
    for e in edges:
        sign = "+" if e["edge"] >= 0 else ""
        body += f"★ {e['show']} | {e['category']}\n"
        body += f"  Nominee:    {e['nominee']}\n"
        body += f"  Model:      {e['model_prob']}%\n"
        body += f"  Kalshi:     {e['kalshi_prob']}¢\n"
        body += f"  Edge:       {sign}{e['edge']}%\n"
        body += f"  Confidence: {e['confidence']}\n\n"
    body += "=" * 50 + "\n"
    body += "Check your dashboard for full reasoning."
    return subject, body

def send_email(subject, body):
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("  [Email] Gmail not configured — printing alert:")
        print("  " + body.replace("\n", "\n  "))
        return False
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_USER
        msg["To"]      = ALERT_TO_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, ALERT_TO_EMAIL, msg.as_string())
        print(f"  ✓ Email sent to {ALERT_TO_EMAIL}")
        return True
    except Exception as e:
        print(f"  [Email error]: {e}")
        return False

def alert_on_edges(edges):
    new_edges = [e for e in edges if not already_alerted(e["nominee"], e["edge"])]
    if not new_edges:
        print("  No new edges to alert on.")
        return
    print(f"  Sending email alert for {len(new_edges)} new edge(s)...")
    subject, body = format_email(new_edges)
    success = send_email(subject, body)
    if success:
        for e in new_edges:
            save_sent_alert(e["nominee"], e["edge"])
