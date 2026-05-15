"""
MLU Multi-Period Dashboard Generator
Auto-discovers all QBRs and Monthly Reports under the Machines Like Us root.
Usage: python3 build_dashboard.py <mlu_root>
  mlu_root – path to the "Machines Like Us" folder
"""

import sys, os, glob, json
import pandas as pd

ROOT = sys.argv[1]  # e.g. /Users/.../Machines Like Us

# ── Data loaders ───────────────────────────────────────────────────────────

def glob_first(*patterns):
    for p in patterns:
        m = glob.glob(p)
        if m: return sorted(m)
    return []

def load_apple_plays(apple_dir):
    csvs = glob_first(
        os.path.join(apple_dir, "Apple Monthly Plays", "*.csv"),
        os.path.join(apple_dir, "*Plays*.csv"),
        os.path.join(apple_dir, "*plays*.csv"),
    )
    if not csvs: return None
    df = pd.concat([pd.read_csv(f, quotechar='"') for f in csvs], ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m%d')
    for col in ['Total Time Listened', 'Plays', 'Unique Listeners', 'Unique Engaged Listeners']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # Episode-level → aggregate to daily totals
    df = (df.groupby('Date', as_index=False)
          [['Total Time Listened', 'Plays', 'Unique Listeners', 'Unique Engaged Listeners']]
          .sum())
    return df.sort_values('Date').reset_index(drop=True)

def load_apple_followers(apple_dir):
    csvs = glob_first(
        os.path.join(apple_dir, "Apple Monthly Subscribers", "*.csv"),
        os.path.join(apple_dir, "*Followers*.csv"),
        os.path.join(apple_dir, "*followers*.csv"),
        os.path.join(apple_dir, "*Subscribers*.csv"),
    )
    if not csvs: return None
    df = pd.concat([pd.read_csv(f) for f in csvs], ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m%d')
    return df.sort_values('Date').reset_index(drop=True)

def load_spotify(spotify_dir):
    files = glob_first(
        os.path.join(spotify_dir, "*Spotify_Listeners*.csv"),
        os.path.join(spotify_dir, "*Spotify_Followers_Plays*.csv"),
        os.path.join(spotify_dir, "*.csv"),
    )
    if not files: return None
    df = pd.read_csv(files[0])
    df['Date'] = pd.to_datetime(df['Date'])
    return df.sort_values('Date').reset_index(drop=True)

def load_yt_viewers(yt_dir):
    files = glob_first(
        os.path.join(yt_dir, "*AllViewers*.csv"),
        os.path.join(yt_dir, "*Viewers*.csv"),
        os.path.join(yt_dir, "*viewers*.csv"),
    )
    if not files: return None
    df = pd.read_csv(files[0])
    df['Date'] = pd.to_datetime(df['Date'])
    return df.sort_values('Date').reset_index(drop=True)

def load_yt_subs(yt_dir):
    files = glob_first(os.path.join(yt_dir, "*Subscribers*.csv"))
    if not files: return None
    df = pd.read_csv(files[0])
    df['Date'] = pd.to_datetime(df['Date'])
    return df.sort_values('Date').reset_index(drop=True)

# ── Discover periods ────────────────────────────────────────────────────────

def discover_periods(root):
    periods = []

    # QBRs
    qbr_base = os.path.join(root, "QBRs")
    if os.path.isdir(qbr_base):
        for name in sorted(os.listdir(qbr_base)):
            folder = os.path.join(qbr_base, name)
            if os.path.isdir(folder):
                periods.append({"label": f"{name} 2026", "type": "QBR", "path": folder})

    # Monthly Reports
    monthly_base = os.path.join(root, "Monthly Reports")
    if os.path.isdir(monthly_base):
        for name in sorted(os.listdir(monthly_base)):
            folder = os.path.join(monthly_base, name)
            if os.path.isdir(folder):
                periods.append({"label": f"{name} 2026", "type": "Monthly", "path": folder})

    return periods

# ── Build dataset for one period ────────────────────────────────────────────

def to_points(df, date_col, val_col):
    if df is None or val_col not in df.columns: return []
    return [
        {"x": row[date_col].strftime("%Y-%m-%d"), "y": int(row[val_col])}
        for _, row in df.iterrows() if pd.notna(row[val_col])
    ]

def safe_int(series):
    return int(series.dropna().iloc[-1]) if len(series.dropna()) else 0

def delta(series):
    s = series.dropna()
    return int(s.iloc[-1]) - int(s.iloc[0]) if len(s) >= 2 else 0

def pct(series):
    s = series.dropna()
    start = int(s.iloc[0])
    return round((delta(series) / start) * 100, 1) if start and len(s) >= 2 else 0

def build_period_data(p):
    path = p["path"]
    apple_dir   = os.path.join(path, "Apple")
    spotify_dir = os.path.join(path, "Spotify")
    yt_dir      = os.path.join(path, "YouTube")

    al = load_apple_plays(apple_dir)
    af = load_apple_followers(apple_dir)
    sp = load_spotify(spotify_dir)
    yv = load_yt_viewers(yt_dir)
    ys = load_yt_subs(yt_dir)

    return {
        "label":   p["label"],
        "type":    p["type"],
        # chart series
        "apple_plays":       to_points(al, "Date", "Plays"),
        "apple_followers":   to_points(af, "Date", "Net Followers"),
        "spotify_plays":     to_points(sp, "Date", "Plays"),
        "spotify_followers": to_points(sp, "Date", "Followers"),
        "yt_audience":       to_points(yv, "Date", "Monthly audience"),
        "yt_subs":           to_points(ys, "Date", "Subscribers"),
        # KPIs
        "kpi": {
            "apple_plays_total":      f"{int(al['Plays'].sum()):,}" if al is not None else "—",
            "apple_followers_end":    f"{safe_int(af['Net Followers']):,}" if af is not None else "—",
            "apple_followers_delta":  f"+{delta(af['Net Followers']):,}" if af is not None else "—",
            "apple_followers_pct":    f"+{pct(af['Net Followers'])}%" if af is not None else "—",
            "spotify_plays_total":    f"{int(sp['Plays'].sum()):,}" if sp is not None else "—",
            "spotify_followers_end":  f"{safe_int(sp['Followers']):,}" if sp is not None else "—",
            "spotify_followers_delta":f"+{delta(sp['Followers']):,}" if sp is not None else "—",
            "spotify_followers_pct":  f"+{pct(sp['Followers'])}%" if sp is not None else "—",
            "yt_audience_avg":        f"{int(yv['Monthly audience'].mean()):,}" if yv is not None else "—",
            "yt_subs_end":            f"{safe_int(ys['Subscribers']):,}" if ys is not None else "—",
            "yt_subs_delta":          f"+{delta(ys['Subscribers']):,}" if ys is not None else "—",
            "yt_subs_pct":            f"+{pct(ys['Subscribers'])}%" if ys is not None else "—",
        }
    }

# ── Collect all periods ─────────────────────────────────────────────────────

periods_meta = discover_periods(ROOT)
if not periods_meta:
    print("ERROR: No QBR or Monthly Report folders found under", ROOT)
    sys.exit(1)

all_data = [build_period_data(p) for p in periods_meta]
periods_json = json.dumps(all_data)
default_label = all_data[0]["label"]

# ── Generate HTML ───────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Machines Like Us — Analytics Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  :root{{
    --cream:#F2EDE3;--cream-dark:#E8E0D2;--cream-border:#D5CAB8;
    --dark:#1C1C1C;--mid:#4A4A4A;--muted:#7A7060;
    --apple:#5B2C8D;--spotify:#1A4B8C;--youtube:#C0392B;
    --red-fill:#7B1E1E;--header:#2C3E50;
  }}
  html{{scroll-behavior:smooth}}
  body{{font-family:Arial,sans-serif;background:var(--cream);color:var(--dark);min-height:100vh}}

  /* Hero */
  .hero{{background:var(--header);color:#fff;padding:36px 48px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}}
  .hero h1{{font-size:26px;font-weight:700;letter-spacing:-0.3px}}
  .hero p{{font-size:12px;color:rgba(255,255,255,0.5);margin-top:4px;letter-spacing:1.5px;text-transform:uppercase}}

  /* Period toggle */
  .period-bar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
  .period-btn{{padding:7px 16px;border-radius:20px;border:1px solid rgba(255,255,255,0.25);background:transparent;color:rgba(255,255,255,0.6);font-size:12px;font-weight:600;cursor:pointer;transition:all .18s;white-space:nowrap;font-family:Arial,sans-serif}}
  .period-btn:hover{{background:rgba(255,255,255,0.1);color:#fff}}
  .period-btn.active{{background:#fff;color:var(--header);border-color:#fff}}

  /* Platform nav */
  nav{{background:#fff;border-bottom:1px solid var(--cream-border);padding:0 48px;display:flex;gap:0;position:sticky;top:0;z-index:100}}
  .nav-btn{{padding:15px 20px;font-size:13px;font-weight:600;color:var(--muted);background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;transition:all .18s;white-space:nowrap;font-family:Arial,sans-serif}}
  .nav-btn:hover{{color:var(--dark)}}
  .nav-btn.active{{color:var(--dark);border-bottom-color:var(--dark)}}
  .nav-btn.active.apple{{color:var(--apple);border-bottom-color:var(--apple)}}
  .nav-btn.active.spotify{{color:var(--spotify);border-bottom-color:var(--spotify)}}
  .nav-btn.active.youtube{{color:var(--youtube);border-bottom-color:var(--youtube)}}

  /* Layout */
  .page{{max-width:1100px;margin:0 auto;padding:36px 48px 80px}}
  .section{{display:none}}.section.active{{display:block}}

  /* KPI row */
  .kpi-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px}}
  .kpi-card{{background:#fff;border:1px solid var(--cream-border);border-radius:10px;padding:18px 20px}}
  .kpi-label{{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:8px}}
  .kpi-value{{font-size:28px;font-weight:700;color:var(--dark);letter-spacing:-0.5px}}
  .kpi-sub{{font-size:12px;color:var(--muted);margin-top:3px}}
  .kpi-delta{{display:inline-block;background:#e8f5ee;color:#1a6b38;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-top:6px}}

  /* Overview platform cards */
  .overview-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px}}
  .platform-card{{background:#fff;border:1px solid var(--cream-border);border-radius:10px;overflow:hidden}}
  .platform-header{{padding:14px 18px;display:flex;align-items:center;gap:10px}}
  .platform-dot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
  .platform-name{{font-size:13px;font-weight:700}}
  .platform-stats{{padding:2px 18px 16px;display:flex;flex-direction:column;gap:7px}}
  .stat-row{{display:flex;justify-content:space-between;font-size:13px}}
  .stat-label{{color:var(--muted)}}
  .stat-val{{font-weight:600}}

  /* Chart card */
  .chart-card{{background:#fff;border:1px solid var(--cream-border);border-radius:10px;padding:22px 22px 14px;margin-bottom:18px}}
  .chart-title{{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:16px}}
  .chart-wrap{{position:relative;height:260px}}

  @media(max-width:720px){{
    .hero{{padding:24px}}
    .page{{padding:24px 24px 60px}}
    nav{{padding:0 16px}}
    .kpi-row,.overview-grid{{grid-template-columns:1fr}}
  }}
</style>
</head>
<body>

<div class="hero">
  <div>
    <p>Machines Like Us</p>
    <h1>Analytics Dashboard</h1>
  </div>
  <div class="period-bar" id="period-bar"></div>
</div>

<nav>
  <button class="nav-btn active"    onclick="showTab('overview',this)">Overview</button>
  <button class="nav-btn apple"     onclick="showTab('apple',this)">Apple Podcasts</button>
  <button class="nav-btn spotify"   onclick="showTab('spotify',this)">Spotify</button>
  <button class="nav-btn youtube"   onclick="showTab('youtube',this)">YouTube</button>
</nav>

<div class="page">

  <!-- Overview -->
  <div class="section active" id="sec-overview">
    <div class="overview-grid" id="ov-cards"></div>
    <div class="chart-card">
      <div class="chart-title">Followers &amp; Subscribers Growth</div>
      <div class="chart-wrap"><canvas id="ch-combined"></canvas></div>
    </div>
  </div>

  <!-- Apple -->
  <div class="section" id="sec-apple">
    <div class="kpi-row" id="ap-kpis"></div>
    <div class="chart-card">
      <div class="chart-title">Plays Per Day</div>
      <div class="chart-wrap"><canvas id="ch-apple-listeners"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Net Followers Over Time</div>
      <div class="chart-wrap"><canvas id="ch-apple-followers"></canvas></div>
    </div>
  </div>

  <!-- Spotify -->
  <div class="section" id="sec-spotify">
    <div class="kpi-row" id="sp-kpis"></div>
    <div class="chart-card">
      <div class="chart-title">Plays Per Day</div>
      <div class="chart-wrap"><canvas id="ch-spotify-plays"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Followers Over Time</div>
      <div class="chart-wrap"><canvas id="ch-spotify-followers"></canvas></div>
    </div>
  </div>

  <!-- YouTube -->
  <div class="section" id="sec-youtube">
    <div class="kpi-row" id="yt-kpis"></div>
    <div class="chart-card">
      <div class="chart-title">Monthly Audience Per Day</div>
      <div class="chart-wrap"><canvas id="ch-yt-audience"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Subscribers Over Time</div>
      <div class="chart-wrap"><canvas id="ch-yt-subs"></canvas></div>
    </div>
  </div>

</div>

<script>
const CREAM    = '#F2EDE3';
const GRID_C   = '#C5BDB3';
const TEXT_C   = '#3A3A3A';
const RED_FILL = '#7B1E1E';
const APPLE_C  = '#5B2C8D';
const SPOTIFY_C= '#1A4B8C';
const YOUTUBE_C= '#C0392B';

Chart.defaults.font.family = 'Arial, sans-serif';

// ── All embedded period data ──
const ALL_PERIODS = {json.dumps(all_data)};

// Build lookup by label
const PERIODS = {{}};
ALL_PERIODS.forEach(p => PERIODS[p.label] = p);

let activePeriod = ALL_PERIODS[0].label;

// ── Chart instances (destroyed & recreated on period switch) ──
const charts = {{}};

function destroyChart(id) {{
  if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }}
}}

// ── Shared chart config ──
const baseScales = {{
  x: {{
    type: 'time',
    time: {{ unit: 'week', displayFormats: {{ week: 'dd-MMM' }} }},
    ticks: {{ color: TEXT_C, maxRotation: 45, font: {{ size: 9 }} }},
    grid: {{ display: false }},
    border: {{ color: GRID_C }}
  }},
  y: {{
    ticks: {{ color: TEXT_C, font: {{ size: 9 }}, callback: v => Number.isInteger(v) ? v.toLocaleString() : '' }},
    grid: {{ color: GRID_C, lineWidth: 0.8 }},
    border: {{ display: false }}
  }}
}};

const baseOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: '#fff', borderColor: GRID_C, borderWidth: 1,
      titleColor: TEXT_C, bodyColor: TEXT_C,
      callbacks: {{ label: ctx => ' ' + ctx.parsed.y.toLocaleString() }}
    }}
  }},
  scales: baseScales,
  animation: {{ duration: 500 }}
}};

function makeArea(canvasId, data, color) {{
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {{
    type: 'line',
    data: {{ datasets: [{{
      data, parsing: {{ xAxisKey:'x', yAxisKey:'y' }},
      borderColor: color, borderWidth: 1.5,
      backgroundColor: color + '22', fill: true,
      pointRadius: 0, tension: 0.3
    }}] }},
    options: baseOpts
  }});
}}

function makeLine(canvasId, datasets) {{
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {{
    type: 'line',
    data: {{ datasets: datasets.map(d => ({{
      label: d.label, data: d.data,
      parsing: {{ xAxisKey:'x', yAxisKey:'y' }},
      borderColor: d.color, borderWidth: 2,
      backgroundColor: 'transparent', fill: false,
      pointRadius: 0, tension: 0.3
    }})) }},
    options: {{ ...baseOpts, plugins: {{ ...baseOpts.plugins,
      legend: {{ display: true, position: 'bottom',
        labels: {{ color: TEXT_C, boxWidth: 12, font: {{ size: 11 }}, padding: 20 }} }}
    }} }}
  }});
}}

// ── Render KPI cards ──
function kpiCard(label, value, sub, delta) {{
  return `<div class="kpi-card">
    <div class="kpi-label">${{label}}</div>
    <div class="kpi-value">${{value}}</div>
    ${{sub ? `<div class="kpi-sub">${{sub}}</div>` : ''}}
    ${{delta ? `<div class="kpi-delta">${{delta}}</div>` : ''}}
  </div>`;
}}

function renderPeriod(label) {{
  activePeriod = label;
  const d = PERIODS[label];
  const k = d.kpi;

  // Overview cards
  document.getElementById('ov-cards').innerHTML = `
    <div class="platform-card">
      <div class="platform-header"><div class="platform-dot" style="background:${{APPLE_C}}"></div><span class="platform-name">Apple Podcasts</span></div>
      <div class="platform-stats">
        <div class="stat-row"><span class="stat-label">Total Plays</span><span class="stat-val">${{k.apple_plays_total}}</span></div>
        <div class="stat-row"><span class="stat-label">Followers</span><span class="stat-val">${{k.apple_followers_end}} <small style="color:var(--muted);font-weight:400">${{k.apple_followers_pct}}</small></span></div>
      </div>
    </div>
    <div class="platform-card">
      <div class="platform-header"><div class="platform-dot" style="background:${{SPOTIFY_C}}"></div><span class="platform-name">Spotify</span></div>
      <div class="platform-stats">
        <div class="stat-row"><span class="stat-label">Total Plays</span><span class="stat-val">${{k.spotify_plays_total}}</span></div>
        <div class="stat-row"><span class="stat-label">Followers</span><span class="stat-val">${{k.spotify_followers_end}} <small style="color:var(--muted);font-weight:400">${{k.spotify_followers_pct}}</small></span></div>
      </div>
    </div>
    <div class="platform-card">
      <div class="platform-header"><div class="platform-dot" style="background:${{YOUTUBE_C}}"></div><span class="platform-name">YouTube</span></div>
      <div class="platform-stats">
        <div class="stat-row"><span class="stat-label">Avg Monthly Audience</span><span class="stat-val">${{k.yt_audience_avg}}</span></div>
        <div class="stat-row"><span class="stat-label">Subscribers</span><span class="stat-val">${{k.yt_subs_end}} <small style="color:var(--muted);font-weight:400">${{k.yt_subs_pct}}</small></span></div>
      </div>
    </div>`;

  // Apple KPIs
  document.getElementById('ap-kpis').innerHTML =
    kpiCard('Total Plays', k.apple_plays_total, d.label, '') +
    kpiCard('Followers', k.apple_followers_end, '', k.apple_followers_delta + ' (' + k.apple_followers_pct + ')') +
    kpiCard('Follower Growth', k.apple_followers_delta, 'Net new followers', '');

  // Spotify KPIs
  document.getElementById('sp-kpis').innerHTML =
    kpiCard('Total Plays', k.spotify_plays_total, d.label, '') +
    kpiCard('Followers', k.spotify_followers_end, '', k.spotify_followers_delta + ' (' + k.spotify_followers_pct + ')') +
    kpiCard('Follower Growth', k.spotify_followers_delta, 'Net new followers', '');

  // YouTube KPIs
  document.getElementById('yt-kpis').innerHTML =
    kpiCard('Avg Monthly Audience', k.yt_audience_avg, d.label, '') +
    kpiCard('Subscribers', k.yt_subs_end, '', k.yt_subs_delta + ' (' + k.yt_subs_pct + ')') +
    kpiCard('Subscriber Growth', k.yt_subs_delta, 'Net new subscribers', '');

  // Charts
  makeLine('ch-combined', [
    {{ label: 'Apple Podcasts', data: d.apple_followers,   color: APPLE_C }},
    {{ label: 'Spotify',        data: d.spotify_followers, color: SPOTIFY_C }},
    {{ label: 'YouTube',        data: d.yt_subs,           color: YOUTUBE_C }},
  ]);
  makeArea('ch-apple-listeners',   d.apple_plays,       RED_FILL);
  makeArea('ch-apple-followers',   d.apple_followers,   APPLE_C);
  makeArea('ch-spotify-plays',     d.spotify_plays,     RED_FILL);
  makeArea('ch-spotify-followers', d.spotify_followers, SPOTIFY_C);
  makeArea('ch-yt-audience',       d.yt_audience,       RED_FILL);
  makeArea('ch-yt-subs',           d.yt_subs,           YOUTUBE_C);
}}

// ── Period toggle buttons ──
const bar = document.getElementById('period-bar');
ALL_PERIODS.forEach((p, i) => {{
  const btn = document.createElement('button');
  btn.className = 'period-btn' + (i === 0 ? ' active' : '');
  btn.textContent = p.label;
  btn.onclick = () => {{
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderPeriod(p.label);
  }};
  bar.appendChild(btn);
}});

// ── Platform tab switching ──
function showTab(id, btn) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  btn.classList.add('active');
}}

// ── Init ──
renderPeriod(ALL_PERIODS[0].label);
</script>
</body>
</html>"""

out_path = os.path.join(ROOT, "MLU_Dashboard.html")
with open(out_path, "w") as f:
    f.write(html)
print(f"SAVED:{out_path}")
