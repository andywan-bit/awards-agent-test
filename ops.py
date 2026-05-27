# ============================================================
#  ops.py — live ops dashboard showing agent activity
# ============================================================

import json
import os
import threading
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)
OPS_LOG_FILE = "/tmp/ops_log.json"
AGENT_THREAD = None
AGENT_TIMER = None

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Ops</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Syne:wght@400;500;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #080a0e; --surface: #0f1117; --border: #1e2330;
    --text: #e2e4ec; --muted: #4a5068; --dim: #2a2f42;
    --green: #2ecc71; --amber: #f39c12; --red: #e74c3c; --blue: #3498db;
  }
  body { font-family: 'JetBrains Mono', monospace; background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem; font-size: 13px; }
  h1 { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 2rem; display: flex; align-items: center; gap: 10px; }
  .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; flex-shrink: 0; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; }
  .card-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
  .card-value { font-size: 1.8rem; font-weight: 300; }
  .card-value.green { color: var(--green); }
  .card-value.amber { color: var(--amber); }
  .card-value.blue  { color: var(--blue);  }
  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }
  .section-title { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem; }
  .step { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
  .step:last-child { border-bottom: none; }
  .step-icon { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; flex-shrink: 0; margin-top: 2px; }
  .step-icon.done    { background: #0d2b1a; color: var(--green); border: 1px solid #1a4a2a; }
  .step-icon.running { background: #1a2a0d; color: var(--amber); border: 1px solid #3a4a1a; animation: pulse 1s infinite; }
  .step-icon.waiting { background: var(--dim); color: var(--muted); border: 1px solid var(--border); }
  .step-name   { font-size: 12px; font-weight: 500; margin-bottom: 3px; }
  .step-detail { font-size: 11px; color: var(--muted); }
  .edge-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; margin-bottom: 8px; }
  .edge-card.strong   { border-left: 2px solid var(--green); }
  .edge-card.moderate { border-left: 2px solid var(--amber); }
  .edge-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .edge-show { font-size: 10px; color: var(--muted); margin-bottom: 2px; }
  .edge-name { font-size: 13px; font-weight: 500; }
  .edge-badge { font-size: 11px; font-weight: 500; padding: 3px 8px; border-radius: 4px; white-space: nowrap; }
  .edge-badge.strong   { background: #0d2b1a; color: var(--green); }
  .edge-badge.moderate { background: #2b1f0d; color: var(--amber); }
  .bars { display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; }
  .bar-row { display: flex; align-items: center; gap: 8px; font-size: 11px; }
  .bar-label { color: var(--muted); width: 40px; text-align: right; }
  .bar-track { flex: 1; height: 3px; background: var(--dim); border-radius: 2px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 2px; }
  .bar-fill.model  { background: var(--blue); }
  .bar-fill.kalshi { background: var(--muted); }
  .bar-pct { width: 32px; }
  .sig-table { width: 100%; border-collapse: collapse; font-size: 11px; }
  .sig-table td { padding: 5px 0; border-bottom: 1px solid var(--border); }
  .sig-table tr:last-child td { border-bottom: none; }
  .sig-table td:last-child { text-align: right; color: var(--green); }
  .winner-tag { display: inline-block; background: var(--dim); color: var(--text); font-size: 11px; padding: 3px 8px; border-radius: 4px; margin: 3px 3px 3px 0; }
  .no-data { color: var(--muted); font-size: 12px; padding: 1rem 0; }
  .top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; font-size: 11px; color: var(--muted); }
</style>
</head>
<body>
<h1><span class="pulse"></span>Agent ops · Awards scanner</h1>

<div class="top-row">
  <span id="page-time">Loading...</span>
  <span>Auto-refreshes every 30s</span>
</div>

<div class="grid-3">
  <div class="card"><div class="card-label">Cycles run</div><div class="card-value blue"  id="stat-runs">—</div></div>
  <div class="card"><div class="card-label">Edges found</div><div class="card-value green" id="stat-edges">—</div></div>
  <div class="card"><div class="card-label">Alerts sent</div><div class="card-value amber" id="stat-alerts">—</div></div>
</div>

<div class="grid-2">
  <div class="section">
    <div class="section-title">Current cycle — steps</div>
    <div id="steps-list"><div class="no-data">Waiting for first cycle...</div></div>
  </div>
  <div class="section">
    <div class="section-title">Winners extracted this cycle</div>
    <div id="winners-list"><div class="no-data">No data yet</div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">Current edges — full reasoning</div>
  <div id="edges-list"><div class="no-data">No edges found yet</div></div>
</div>

<script>
function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60)   return diff + 's ago';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  return Math.floor(diff/3600) + 'h ago';
}

function renderSteps(steps) {
  const defs = [
    {num:1, name:'News scout',   key:'articles_found',    suffix:' articles'},
    {num:2, name:'AI parser',    key:'winners_extracted', suffix:' winners'},
    {num:3, name:'Data updater', key:'github_updated',    suffix:''},
    {num:4, name:'Edge scanner', key:'edges_found',       suffix:' edges'},
  ];
  if (!steps || steps.length === 0) return '<div class="no-data">Waiting for first cycle...</div>';
  return defs.map(def => {
    const s = steps.find(x => x.step === def.num);
    const status = s ? s.status : 'waiting';
    const icon = status === 'done' ? '✓' : status === 'running' ? '◉' : '○';
    let detail = '—';
    if (s && s.status === 'done') {
      if (def.key === 'github_updated') detail = s[def.key] ? 'GitHub updated' : 'No changes needed';
      else if (def.key === 'articles_found') detail = (s[def.key]||0) + def.suffix + ' · ' + (s.shows_searched||[]).join(', ');
      else detail = (s[def.key]||0) + def.suffix;
    } else if (status === 'running') detail = 'In progress...';
    return `<div class="step">
      <div class="step-icon ${status}">${icon}</div>
      <div><div class="step-name">${def.name}</div><div class="step-detail">${detail}</div></div>
    </div>`;
  }).join('');
}

function renderWinners(winners) {
  if (!winners || winners.length === 0) return '<div class="no-data">No winners extracted this cycle</div>';
  return winners.map(w => `<span class="winner-tag">★ ${w.nominee} — ${w.category}</span>`).join('');
}

function renderEdges(edges) {
  if (!edges || edges.length === 0) return '<div class="no-data">No edges above threshold</div>';
  return edges.map(e => {
    const tier = e.edge >= 15 ? 'strong' : e.edge >= 8 ? 'moderate' : 'none';
    const sign = e.edge >= 0 ? '+' : '';
    const sigs = e.signal_breakdown || {};
    const rows = Object.entries(sigs).map(([k,v]) =>
      `<tr>
        <td style="color:var(--muted)">${k.replace(/_/g,' ')}</td>
        <td style="color:var(--muted);font-size:10px">signal ${v.raw_signal} · wt ${(v.weight*100).toFixed(0)}%</td>
        <td>+${v.contribution.toFixed(1)}pp</td>
      </tr>`).join('');
    return `<div class="edge-card ${tier}">
      <div class="edge-header">
        <div>
          <div class="edge-show">${e.show} · ${e.category}</div>
          <div class="edge-name">${e.nominee}</div>
          <div style="font-size:11px;color:var(--muted);margin-top:3px">${e.confidence} confidence · ${e.signals_used||0} signals</div>
        </div>
        <span class="edge-badge ${tier}">${sign}${e.edge}%</span>
      </div>
      <div class="bars">
        <div class="bar-row">
          <span class="bar-label">model</span>
          <div class="bar-track"><div class="bar-fill model" style="width:${e.model_prob}%"></div></div>
          <span class="bar-pct">${e.model_prob}%</span>
        </div>
        <div class="bar-row">
          <span class="bar-label">kalshi</span>
          <div class="bar-track"><div class="bar-fill kalshi" style="width:${e.kalshi_prob}%"></div></div>
          <span class="bar-pct">${e.kalshi_prob}%</span>
        </div>
      </div>
      ${rows ? `<table class="sig-table">${rows}</table>` : ''}
    </div>`;
  }).join('');
}

async function refresh() {
  try {
    const r = await fetch('/api/ops');
    const d = await r.json();
    document.getElementById('page-time').textContent  = 'Last cycle: ' + timeAgo(d.cycle_started);
    document.getElementById('stat-runs').textContent   = d.total_runs || '0';
    document.getElementById('stat-edges').textContent  = (d.edges||[]).length;
    document.getElementById('stat-alerts').textContent = d.alerts_sent || '0';
    document.getElementById('steps-list').innerHTML    = renderSteps(d.steps);
    document.getElementById('winners-list').innerHTML  = renderWinners(d.winners_found);
    document.getElementById('edges-list').innerHTML    = renderEdges(d.edges);
  } catch(e) {
    document.getElementById('page-time').textContent = 'Waiting for agent...';
  }
}

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})

@app.route("/api/ops")
def api_ops():
    try:
        with open(OPS_LOG_FILE) as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"status":"waiting","steps":[],"edges":[],"winners_found":[],"alerts_sent":0,"total_runs":0})


def start_agent_thread():
    global AGENT_THREAD
    if os.environ.get("START_AGENT", "false").lower() not in {"1", "true", "yes"}:
        print("Agent background thread disabled by START_AGENT")
        return
    if AGENT_THREAD and AGENT_THREAD.is_alive():
        return

    from agent import run_watch

    AGENT_THREAD = threading.Thread(target=run_watch, daemon=True)
    AGENT_THREAD.start()


def schedule_agent_thread():
    global AGENT_TIMER
    delay_seconds = float(os.environ.get("AGENT_START_DELAY_SECONDS", "20"))
    if AGENT_TIMER:
        return

    AGENT_TIMER = threading.Timer(delay_seconds, start_agent_thread)
    AGENT_TIMER.daemon = True
    AGENT_TIMER.start()
    print(f"Agent background thread scheduled in {delay_seconds:g}s")


print(f"Ops dashboard configured for PORT={os.environ.get('PORT', '8080')}")
schedule_agent_thread()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting ops dashboard on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port, threaded=True)
