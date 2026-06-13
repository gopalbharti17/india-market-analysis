"""
report.py — Generates report.html after every pipeline run.
Called automatically from main.py / server.py.
"""

from datetime import datetime
import pandas as pd
import json


def _to_json(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        row = {}
        for k, v in r.items():
            if isinstance(v, float) and pd.isna(v):
                row[k] = None
            elif hasattr(v, 'item'):
                row[k] = v.item()
            else:
                row[k] = v
        rows.append(row)
    return json.dumps(rows)


def generate(
    stock_df: pd.DataFrame,
    mf_df: pd.DataFrame,
    stock_changes: list[dict],
    mf_changes: list[dict],
    run_ts: str,
):
    ts = datetime.fromisoformat(run_ts).strftime("%d %b %Y, %I:%M %p")
    stock_json = _to_json(stock_df)
    mf_json = _to_json(mf_df)
    changes_json = json.dumps({"stock": stock_changes, "fund": mf_changes})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>India Market Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#222;font-size:14px}}
  .topbar{{background:#1a1a2e;color:#fff;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}}
  .topbar h1{{font-size:1.1rem;font-weight:700;letter-spacing:.02em}}
  .topbar .meta{{font-size:0.78rem;color:#aab;margin-top:2px}}
  #runBtn{{background:#e8b84b;color:#1a1a2e;border:none;padding:9px 22px;border-radius:7px;font-weight:700;font-size:0.88rem;cursor:pointer;transition:opacity .2s}}
  #runBtn:disabled{{opacity:.5;cursor:not-allowed}}
  #runBtn:hover:not(:disabled){{opacity:.85}}
  .wrapper{{max-width:1500px;margin:0 auto;padding:20px 16px}}
  .card{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:20px 24px;margin-top:20px;overflow-x:auto}}
  .card-header{{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f2f5}}
  .card-header h2{{font-size:1rem;font-weight:700}}
  .filters{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
  .filters select,.filters input{{padding:5px 10px;border:1px solid #ddd;border-radius:6px;font-size:0.82rem;background:#fafafa}}
  .filters label{{font-size:0.82rem;color:#555}}
  .dl-btn{{padding:5px 14px;background:#f0f2f5;border:1px solid #ddd;border-radius:6px;font-size:0.82rem;cursor:pointer;font-weight:600;color:#333}}
  .dl-btn:hover{{background:#e4e6ea}}
  table{{width:100%;border-collapse:collapse;white-space:nowrap;font-size:0.84rem}}
  th{{background:#1a1a2e;color:#fff;padding:9px 12px;text-align:left;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;cursor:pointer;user-select:none}}
  th:hover{{background:#2d2d4e}}
  th .sort-icon{{margin-left:4px;opacity:.5;font-size:.7em}}
  td{{padding:7px 12px;border-bottom:1px solid #f0f2f5;vertical-align:middle}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#f7f8fc!important}}
  .score-hi{{background:#c6efce;color:#276221;font-weight:600;border-radius:4px;padding:2px 6px}}
  .score-md{{background:#ffeb9c;color:#9c5700;font-weight:600;border-radius:4px;padding:2px 6px}}
  .score-lo{{background:#ffc7ce;color:#9c0006;font-weight:600;border-radius:4px;padding:2px 6px}}
  .scope-sector{{color:#2a7a2a;font-size:0.78em}}
  .scope-fallback{{color:#e07000;font-size:0.78em}}
  .val-pos{{color:#276221;font-weight:600}}
  .val-neg{{color:#9c0006}}
  .na{{color:#bbb}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px}}
  @media(max-width:800px){{.grid2{{grid-template-columns:1fr}}}}
  .changes-card{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:18px 22px}}
  .changes-card h3{{font-size:.95rem;font-weight:700;margin-bottom:12px;color:#333}}
  .ch-list{{list-style:none}}
  .ch-list li{{padding:5px 0;border-bottom:1px solid #f5f5f5;font-size:.85rem}}
  .ch-up{{color:#276221}}.ch-down{{color:#9c0006}}.ch-new{{color:#1a56a0}}.ch-flag{{color:#e07000}}.ch-none{{color:#888}}
  .legend{{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:.78rem}}
  .legend span{{display:flex;align-items:center;gap:5px}}
  .dot{{width:11px;height:11px;border-radius:3px;display:inline-block}}
  .disclaimer{{font-size:.73rem;color:#999;margin-top:24px;padding:12px 16px;background:#fff;border-radius:8px;line-height:1.6}}
  #logPanel{{display:none;background:#1a1a2e;color:#a8e6a8;font-family:monospace;font-size:.8rem;padding:14px 18px;border-radius:10px;margin-top:16px;max-height:220px;overflow-y:auto;white-space:pre-wrap}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.72rem;font-weight:700;margin-left:6px}}
  .badge-sector{{background:#e8f5e9;color:#2a7a2a}}
  .badge-fallback{{background:#fff3e0;color:#e07000}}
  #noRows{{text-align:center;padding:20px;color:#aaa;font-style:italic}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1>🇮🇳 India Market Analysis</h1>
    <div class="meta">Last run: {ts} &nbsp;|&nbsp; Scores are percentile ranks within peer groups</div>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <span id="statusDot" style="font-size:.8rem;color:#aab"></span>
    <button id="runBtn" onclick="runAnalysis()" style="display:none">▶ Run Analysis</button>
  </div>
</div>

<div class="wrapper">

  <!-- LOG PANEL -->
  <div id="logPanel"></div>

  <!-- STOCK RANKINGS -->
  <div class="card">
    <div class="card-header">
      <h2>📈 Stock Rankings</h2>
      <div class="filters">
        <label>Sector:</label>
        <select id="sectorFilter" onchange="renderStocks()"><option value="">All Sectors</option></select>
        <label>Min Score:</label>
        <input type="number" id="minScore" value="0" min="0" max="100" style="width:64px" oninput="renderStocks()">
        <label>Sort:</label>
        <select id="stockSort" onchange="renderStocks()">
          <option value="total_score">Total Score</option>
          <option value="quality_score">Quality</option>
          <option value="growth_score">Growth</option>
          <option value="valuation_score">Valuation</option>
          <option value="momentum_score">Momentum</option>
        </select>
        <button class="dl-btn" onclick="downloadCSV('stock')">⬇ CSV</button>
      </div>
    </div>
    <table id="stockTable">
      <thead>
        <tr>
          <th>#</th>
          <th>Ticker</th>
          <th>Company</th>
          <th>Sector</th>
          <th>P/E</th>
          <th>ROE</th>
          <th>Quality</th>
          <th>Growth</th>
          <th>Valuation</th>
          <th>Momentum</th>
          <th>Total</th>
          <th>Scope</th>
        </tr>
      </thead>
      <tbody id="stockBody"></tbody>
    </table>
    <div class="legend">
      <span><span class="dot" style="background:#c6efce"></span>≥70 strong</span>
      <span><span class="dot" style="background:#ffeb9c"></span>50–70 neutral</span>
      <span><span class="dot" style="background:#ffc7ce"></span>&lt;50 weak</span>
    </div>
  </div>

  <!-- MF RANKINGS -->
  <div class="card">
    <div class="card-header">
      <h2>💰 Mutual Fund Rankings</h2>
      <div class="filters">
        <label>Category:</label>
        <select id="catFilter" onchange="renderFunds()"><option value="">All Categories</option></select>
        <button class="dl-btn" onclick="downloadCSV('fund')">⬇ CSV</button>
      </div>
    </div>
    <table id="mfTable">
      <thead>
        <tr>
          <th>#</th>
          <th>Fund</th>
          <th>Category</th>
          <th>CAGR 3y %</th>
          <th>Alpha 3y</th>
          <th>Upside Cap.</th>
          <th>Downside Cap.</th>
          <th>Worst 3y Roll</th>
          <th>Max DD %</th>
          <th>Total</th>
          <th>Scope</th>
        </tr>
      </thead>
      <tbody id="mfBody"></tbody>
    </table>
    <p style="font-size:.77rem;color:#888;margin-top:10px">
      <b>Alpha 3y:</b> fund CAGR minus benchmark — positive = manager added value &nbsp;|&nbsp;
      <b>Downside Capture:</b> % of market falls absorbed — below 80 is defensive &nbsp;|&nbsp;
      <b>Worst 3y Roll:</b> worst rolling 3-year CAGR ever experienced
    </p>
  </div>

  <!-- CHANGES -->
  <div class="grid2">
    <div class="changes-card">
      <h3>📊 Stock Changes since last run</h3>
      <ul class="ch-list" id="stockChanges"></ul>
    </div>
    <div class="changes-card">
      <h3>📊 Fund Changes since last run</h3>
      <ul class="ch-list" id="fundChanges"></ul>
    </div>
  </div>

  <div class="disclaimer">
    ⚠ This dashboard is for personal research and education only. Scores are relative rankings based on
    publicly available data — they are <b>not investment advice</b>. Methodology weights are unvalidated
    hypotheses. Always do your own due diligence before making any investment decision.
  </div>

</div>

<script>
const STOCKS = {stock_json};
const FUNDS  = {mf_json};
const CHANGES = {changes_json};

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(v, dec=1) {{
  if (v === null || v === undefined) return '<span class="na">—</span>';
  if (typeof v === 'number') return v.toFixed(dec);
  return v;
}}

function scoreCell(v) {{
  if (v === null || v === undefined) return '<td><span class="na">—</span></td>';
  const cls = v >= 70 ? 'score-hi' : v >= 50 ? 'score-md' : 'score-lo';
  return `<td><span class="${{cls}}">${{v.toFixed(1)}}</span></td>`;
}}

function numCell(v, dec=2, posGood=true) {{
  if (v === null || v === undefined) return '<td><span class="na">—</span></td>';
  const cls = posGood ? (v > 0 ? 'val-pos' : v < -5 ? 'val-neg' : '') : (v < 80 ? 'val-pos' : v > 100 ? 'val-neg' : '');
  return `<td class="${{cls}}">${{v.toFixed(dec)}}</td>`;
}}

function scopeCell(v) {{
  const fallback = v && v.includes('fallback');
  const cls = fallback ? 'scope-fallback' : 'scope-sector';
  return `<td class="${{cls}}">${{v || '—'}}</td>`;
}}

// ── Populate filter dropdowns ─────────────────────────────────────────────────
const sectors = [...new Set(STOCKS.map(r => r.sector).filter(Boolean))].sort();
sectors.forEach(s => {{
  document.getElementById('sectorFilter').innerHTML += `<option value="${{s}}">${{s}}</option>`;
}});

const cats = [...new Set(FUNDS.map(r => r.category).filter(Boolean))].sort();
cats.forEach(c => {{
  document.getElementById('catFilter').innerHTML += `<option value="${{c}}">${{c}}</option>`;
}});

// ── Render stock table ────────────────────────────────────────────────────────
function renderStocks() {{
  const sector = document.getElementById('sectorFilter').value;
  const minScore = parseFloat(document.getElementById('minScore').value) || 0;
  const sortCol = document.getElementById('stockSort').value;

  let rows = STOCKS.filter(r =>
    (!sector || r.sector === sector) &&
    ((r.total_score || 0) >= minScore)
  ).sort((a, b) => (b[sortCol] || 0) - (a[sortCol] || 0));

  const tbody = document.getElementById('stockBody');
  if (!rows.length) {{
    tbody.innerHTML = '<tr><td colspan="12" id="noRows">No stocks match current filters</td></tr>';
    return;
  }}
  tbody.innerHTML = rows.map((r, i) => `
    <tr style="background:${{i%2===0?'#fafafa':'#fff'}}">
      <td style="color:#999;font-size:.8em">${{i+1}}</td>
      <td><b>${{r.ticker||''}}</b></td>
      <td>${{r.name||''}}</td>
      <td>${{r.sector||''}}</td>
      <td>${{fmt(r.pe)}}</td>
      <td>${{fmt(r.roe)}}</td>
      ${{scoreCell(r.quality_score)}}
      ${{scoreCell(r.growth_score)}}
      ${{scoreCell(r.valuation_score)}}
      ${{scoreCell(r.momentum_score)}}
      ${{scoreCell(r.total_score)}}
      ${{scopeCell(r.rank_scope)}}
    </tr>`).join('');
}}

// ── Render fund table ─────────────────────────────────────────────────────────
function renderFunds() {{
  const cat = document.getElementById('catFilter').value;
  let rows = FUNDS.filter(r => !cat || r.category === cat);

  const tbody = document.getElementById('mfBody');
  tbody.innerHTML = rows.map((r, i) => `
    <tr style="background:${{i%2===0?'#fafafa':'#fff'}}">
      <td style="color:#999;font-size:.8em">${{i+1}}</td>
      <td style="max-width:260px;white-space:normal">${{r.scheme_name||''}}</td>
      <td style="font-size:.8em">${{r.category||''}}</td>
      ${{numCell(r.cagr_3y, 2, true)}}
      ${{numCell(r.alpha_3y, 2, true)}}
      ${{numCell(r.upside_capture, 1, true)}}
      ${{numCell(r.downside_capture, 1, false)}}
      ${{numCell(r.roll3y_worst, 2, true)}}
      ${{numCell(r.max_drawdown, 2, true)}}
      ${{scoreCell(r.total_score)}}
      ${{scopeCell(r.rank_scope)}}
    </tr>`).join('');
}}

// ── Render changes ────────────────────────────────────────────────────────────
function renderChanges(changes, elId) {{
  const el = document.getElementById(elId);
  if (!changes || !changes.length) {{
    el.innerHTML = '<li class="ch-none">No significant changes since last run.</li>';
    return;
  }}
  const icons = {{UP:'▲',DOWN:'▼',NEW:'★',FLAG:'⚠',REMOVED:'✕'}};
  const cls   = {{UP:'ch-up',DOWN:'ch-down',NEW:'ch-new',FLAG:'ch-flag',REMOVED:'ch-down'}};
  el.innerHTML = changes.map(c =>
    `<li class="${{cls[c.kind]||''}}">${{icons[c.kind]||'•'}} ${{c.text}}</li>`
  ).join('');
}}

// ── CSV download ──────────────────────────────────────────────────────────────
function downloadCSV(type) {{
  const data = type === 'stock' ? STOCKS : FUNDS;
  if (!data.length) return;
  const cols = Object.keys(data[0]);
  const csv = [cols.join(','),
    ...data.map(r => cols.map(c => {{
      const v = r[c];
      if (v === null || v === undefined) return '';
      if (typeof v === 'string' && v.includes(',')) return `"${{v}}"`;
      return v;
    }}).join(','))
  ].join('\\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{type:'text/csv'}}));
  a.download = type === 'stock' ? 'stock_rankings.csv' : 'mf_rankings.csv';
  a.click();
}}

// ── Run Analysis ──────────────────────────────────────────────────────────────
function runAnalysis() {{
  const btn = document.getElementById('runBtn');
  const log = document.getElementById('logPanel');
  const status = document.getElementById('statusDot');
  btn.disabled = true;
  btn.textContent = '⏳ Running...';
  log.style.display = 'block';
  log.textContent = '';
  status.textContent = '● Running...';
  status.style.color = '#e8b84b';

  fetch('/api/run', {{method:'POST'}})
    .then(r => r.json())
    .then(() => {{
      const es = new EventSource('/api/stream');
      es.onmessage = e => {{
        const msg = JSON.parse(e.data);
        if (msg === '__DONE__') {{
          es.close();
          status.textContent = '● Done — reloading...';
          status.style.color = '#a8e6a8';
          setTimeout(() => window.location.reload(), 1200);
        }} else if (msg === '__TIMEOUT__') {{
          es.close();
          btn.disabled = false;
          btn.textContent = '▶ Run Analysis';
          status.textContent = '● Timed out';
          status.style.color = '#ffc7ce';
        }} else {{
          log.textContent += msg + '\\n';
          log.scrollTop = log.scrollHeight;
        }}
      }};
      es.onerror = () => {{
        es.close();
        btn.disabled = false;
        btn.textContent = '▶ Run Analysis';
        status.textContent = '● Error — check terminal';
        status.style.color = '#ffc7ce';
      }};
    }})
    .catch(() => {{
      btn.disabled = false;
      btn.textContent = '▶ Run Analysis';
      status.textContent = '● Server not running';
      status.style.color = '#ffc7ce';
    }});
}}

// ── Init ──────────────────────────────────────────────────────────────────────
renderStocks();
renderFunds();
renderChanges(CHANGES.stock, 'stockChanges');
renderChanges(CHANGES.fund,  'fundChanges');

// Show Run button only when the local server is reachable
fetch('/api/status').then(r => r.json())
  .then(() => {{ document.getElementById('runBtn').style.display = 'inline-block'; }})
  .catch(() => {{}});
</script>
</body>
</html>"""

    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved -> report.html")
