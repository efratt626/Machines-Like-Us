"""
MLU Multi-Period Dashboard Generator
Produces Q1, individual months (Jan–Mar from Q1 data), and April.
Usage: python3 build_dashboard.py <mlu_root>
"""

import sys, os, glob, json
import pandas as pd

ROOT = sys.argv[1]

# ── Raw loaders ────────────────────────────────────────────────────────────

def glob_first(*patterns):
    for p in patterns:
        m = glob.glob(p)
        if m: return sorted(m)
    return []

def load_episode_csv(paths):
    """Load episode-level Apple CSVs and aggregate to daily Plays."""
    df = pd.concat([pd.read_csv(f, quotechar='"') for f in paths], ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m%d')
    for col in ['Total Time Listened', 'Plays', 'Unique Listeners', 'Unique Engaged Listeners']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return (df.groupby('Date', as_index=False)
              [['Total Time Listened', 'Plays', 'Unique Listeners', 'Unique Engaged Listeners']]
              .sum()
              .sort_values('Date').reset_index(drop=True))

def load_followers_csv(paths):
    df = pd.concat([pd.read_csv(f) for f in paths], ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m%d')
    return df.sort_values('Date').reset_index(drop=True)

def load_single_csv(path):
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    return df.sort_values('Date').reset_index(drop=True)

# ── Load all source data once ──────────────────────────────────────────────

Q1 = os.path.join(ROOT, "QBRs", "Q1")
APR = os.path.join(ROOT, "Monthly Reports", "April")

# Q1 Apple plays (episode-level → daily)
q1_apple_plays_csvs = glob_first(os.path.join(Q1, "Apple", "Apple Monthly Plays", "*.csv"))
q1_apple_plays = load_episode_csv(q1_apple_plays_csvs)

# Q1 Apple followers
q1_apple_fol_csvs = glob_first(os.path.join(Q1, "Apple", "Apple Monthly Subscribers", "*.csv"))
q1_apple_fol = load_followers_csv(q1_apple_fol_csvs)

# Q1 Spotify
q1_spotify_file = glob_first(
    os.path.join(Q1, "Spotify", "*Spotify_Listeners*.csv"),
    os.path.join(Q1, "Spotify", "*.csv"),
)[0]
q1_spotify = load_single_csv(q1_spotify_file)

# Q1 YouTube
q1_yt_viewers_file = glob_first(
    os.path.join(Q1, "YouTube", "*AllViewers*.csv"),
    os.path.join(Q1, "YouTube", "*Viewers*.csv"),
)[0]
q1_yt_viewers = load_single_csv(q1_yt_viewers_file)

q1_yt_subs_file = glob_first(os.path.join(Q1, "YouTube", "*Subscribers*.csv"))[0]
q1_yt_subs = load_single_csv(q1_yt_subs_file)

# April Apple plays
apr_apple_plays_csvs = glob_first(
    os.path.join(APR, "Apple", "*Plays*.csv"),
    os.path.join(APR, "Apple", "*.csv"),
)
apr_apple_plays = load_episode_csv(apr_apple_plays_csvs)

# April Apple followers
apr_apple_fol_csvs = glob_first(
    os.path.join(APR, "Apple", "*Followers*.csv"),
    os.path.join(APR, "Apple", "*Subscribers*.csv"),
)
apr_apple_fol = load_followers_csv(apr_apple_fol_csvs)

# April Spotify
apr_spotify_file = glob_first(
    os.path.join(APR, "Spotify", "*Followers_Plays*.csv"),
    os.path.join(APR, "Spotify", "*.csv"),
)[0]
apr_spotify = load_single_csv(apr_spotify_file)

# April YouTube
apr_yt_viewers_file = glob_first(
    os.path.join(APR, "YouTube", "*Viewers*.csv"),
    os.path.join(APR, "YouTube", "*viewers*.csv"),
)[0]
apr_yt_viewers = load_single_csv(apr_yt_viewers_file)

apr_yt_subs_file = glob_first(os.path.join(APR, "YouTube", "*Subscribers*.csv"))[0]
apr_yt_subs = load_single_csv(apr_yt_subs_file)

# ── Filter helpers ─────────────────────────────────────────────────────────

def by_month(df, month):
    return df[df['Date'].dt.month == month].copy().reset_index(drop=True)

# ── Serialisation helpers ──────────────────────────────────────────────────

def pts(df, col):
    if df is None or col not in df.columns: return []
    return [{"x": r['Date'].strftime("%Y-%m-%d"), "y": int(r[col])}
            for _, r in df.iterrows() if pd.notna(r[col])]

def safe_last(series):
    s = series.dropna()
    return int(s.iloc[-1]) if len(s) else 0

def delta(series):
    s = series.dropna()
    return int(s.iloc[-1]) - int(s.iloc[0]) if len(s) >= 2 else 0

def pct(series):
    s = series.dropna()
    start = int(s.iloc[0])
    return round((delta(series) / start) * 100, 1) if start and len(s) >= 2 else 0

def kpis(ap, af, sp, yv, ys):
    return {
        "apple_plays_total":       f"{int(ap['Plays'].sum()):,}"        if ap is not None else "—",
        "apple_followers_end":     f"{safe_last(af['Net Followers']):,}" if af is not None else "—",
        "apple_followers_delta":   f"+{delta(af['Net Followers']):,}"    if af is not None else "—",
        "apple_followers_pct":     f"+{pct(af['Net Followers'])}%"       if af is not None else "—",
        "spotify_plays_total":     f"{int(sp['Plays'].sum()):,}"         if sp is not None else "—",
        "spotify_followers_end":   f"{safe_last(sp['Followers']):,}"     if sp is not None else "—",
        "spotify_followers_delta": f"+{delta(sp['Followers']):,}"        if sp is not None else "—",
        "spotify_followers_pct":   f"+{pct(sp['Followers'])}%"           if sp is not None else "—",
        "yt_audience_avg":         f"{int(yv['Monthly audience'].mean()):,}" if yv is not None else "—",
        "yt_subs_end":             f"{safe_last(ys['Subscribers']):,}"   if ys is not None else "—",
        "yt_subs_delta":           f"+{delta(ys['Subscribers']):,}"      if ys is not None else "—",
        "yt_subs_pct":             f"+{pct(ys['Subscribers'])}%"         if ys is not None else "—",
    }

def make_period(label, group, ap, af, sp, yv, ys):
    return {
        "label": label, "group": group,
        "apple_plays":       pts(ap, "Plays"),
        "apple_followers":   pts(af, "Net Followers"),
        "spotify_plays":     pts(sp, "Plays"),
        "spotify_followers": pts(sp, "Followers"),
        "yt_audience":       pts(yv, "Monthly audience"),
        "yt_subs":           pts(ys, "Subscribers"),
        "kpi":               kpis(ap, af, sp, yv, ys),
    }

# ── Build all periods ──────────────────────────────────────────────────────

MONTH_NAMES = {1: "January", 2: "February", 3: "March"}

all_periods = []

# Q1 full
all_periods.append(make_period(
    "Q1 2026", "quarter",
    q1_apple_plays, q1_apple_fol, q1_spotify, q1_yt_viewers, q1_yt_subs
))

# Jan, Feb, Mar (filtered from Q1 data)
for m, name in MONTH_NAMES.items():
    all_periods.append(make_period(
        f"{name} 2026", "month",
        by_month(q1_apple_plays, m),
        by_month(q1_apple_fol, m),
        by_month(q1_spotify, m),
        by_month(q1_yt_viewers, m),
        by_month(q1_yt_subs, m),
    ))

# April
all_periods.append(make_period(
    "April 2026", "month",
    apr_apple_plays, apr_apple_fol, apr_spotify, apr_yt_viewers, apr_yt_subs
))

periods_json = json.dumps(all_periods)

# ── HTML ───────────────────────────────────────────────────────────────────

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
  .hero{{background:var(--header);color:#fff;padding:32px 48px 24px;display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:20px}}
  .hero h1{{font-size:26px;font-weight:700;letter-spacing:-0.3px}}
  .hero-eyebrow{{font-size:11px;color:rgba(255,255,255,0.45);letter-spacing:2px;text-transform:uppercase;margin-bottom:4px}}

  /* Toggle groups */
  .toggles{{display:flex;flex-direction:column;gap:8px;align-items:flex-end}}
  .toggle-group{{display:flex;align-items:center;gap:6px}}
  .toggle-group-label{{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.35);margin-right:4px;white-space:nowrap}}
  .period-btn{{padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.2);background:transparent;color:rgba(255,255,255,0.55);font-size:12px;font-weight:600;cursor:pointer;transition:all .18s;white-space:nowrap;font-family:Arial,sans-serif}}
  .period-btn:hover{{background:rgba(255,255,255,0.1);color:#fff}}
  .period-btn.active{{background:#fff;color:var(--header);border-color:#fff}}

  /* Platform nav */
  nav{{background:#fff;border-bottom:1px solid var(--cream-border);padding:0 48px;display:flex;position:sticky;top:0;z-index:100}}
  .nav-btn{{padding:15px 20px;font-size:13px;font-weight:600;color:var(--muted);background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;transition:all .18s;font-family:Arial,sans-serif}}
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
    .toggles{{align-items:flex-start}}
    .page{{padding:24px 24px 60px}}
    nav{{padding:0 16px}}
    .kpi-row,.overview-grid{{grid-template-columns:1fr}}
  }}
</style>
</head>
<body>

<div class="hero">
  <div>
    <div class="hero-eyebrow">Machines Like Us</div>
    <h1>Analytics Dashboard</h1>
  </div>
  <div class="toggles">
    <div class="toggle-group" id="tg-quarter"></div>
    <div class="toggle-group" id="tg-month"></div>
  </div>
</div>

<nav>
  <button class="nav-btn active"  onclick="showTab('overview',this)">Overview</button>
  <button class="nav-btn apple"   onclick="showTab('apple',this)">Apple Podcasts</button>
  <button class="nav-btn spotify" onclick="showTab('spotify',this)">Spotify</button>
  <button class="nav-btn youtube" onclick="showTab('youtube',this)">YouTube</button>
</nav>

<div class="page">
  <div class="section active" id="sec-overview">
    <div class="overview-grid" id="ov-cards"></div>
    <div class="chart-card">
      <div class="chart-title">Followers &amp; Subscribers Growth</div>
      <div class="chart-wrap"><canvas id="ch-combined"></canvas></div>
    </div>
  </div>
  <div class="section" id="sec-apple">
    <div class="kpi-row" id="ap-kpis"></div>
    <div class="chart-card">
      <div class="chart-title">Plays Per Day</div>
      <div class="chart-wrap"><canvas id="ch-apple-plays"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Net Followers Over Time</div>
      <div class="chart-wrap"><canvas id="ch-apple-followers"></canvas></div>
    </div>
  </div>
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
const CREAM     = '#F2EDE3';
const GRID_C    = '#C5BDB3';
const TEXT_C    = '#3A3A3A';
const RED_FILL  = '#7B1E1E';
const APPLE_C   = '#5B2C8D';
const SPOTIFY_C = '#1A4B8C';
const YOUTUBE_C = '#C0392B';
Chart.defaults.font.family = 'Arial, sans-serif';

const ALL_PERIODS = {periods_json};
const PERIODS = {{}};
ALL_PERIODS.forEach(p => PERIODS[p.label] = p);

let activePeriod = ALL_PERIODS[0].label;
const charts = {{}};

function destroyChart(id) {{ if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }} }}

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
  responsive: true, maintainAspectRatio: false,
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: '#fff', borderColor: GRID_C, borderWidth: 1,
      titleColor: TEXT_C, bodyColor: TEXT_C,
      callbacks: {{ label: ctx => ' ' + ctx.parsed.y.toLocaleString() }}
    }}
  }},
  scales: baseScales, animation: {{ duration: 400 }}
}};

function makeArea(id, data, color) {{
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id).getContext('2d'), {{
    type: 'line',
    data: {{ datasets: [{{ data, parsing: {{ xAxisKey:'x', yAxisKey:'y' }},
      borderColor: color, borderWidth: 1.5, backgroundColor: color + '22',
      fill: true, pointRadius: 0, tension: 0.3 }}] }},
    options: baseOpts
  }});
}}

function makeLine(id, datasets) {{
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id).getContext('2d'), {{
    type: 'line',
    data: {{ datasets: datasets.map(d => ({{ label: d.label, data: d.data,
      parsing: {{ xAxisKey:'x', yAxisKey:'y' }},
      borderColor: d.color, borderWidth: 2, backgroundColor: 'transparent',
      fill: false, pointRadius: 0, tension: 0.3 }})) }},
    options: {{ ...baseOpts, plugins: {{ ...baseOpts.plugins,
      legend: {{ display: true, position: 'bottom',
        labels: {{ color: TEXT_C, boxWidth: 12, font: {{ size: 11 }}, padding: 20 }} }} }} }}
  }});
}}

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

  document.getElementById('ap-kpis').innerHTML =
    kpiCard('Total Plays', k.apple_plays_total, label, '') +
    kpiCard('Followers', k.apple_followers_end, '', k.apple_followers_delta + ' (' + k.apple_followers_pct + ')') +
    kpiCard('Follower Growth', k.apple_followers_delta, 'Net new followers', '');

  document.getElementById('sp-kpis').innerHTML =
    kpiCard('Total Plays', k.spotify_plays_total, label, '') +
    kpiCard('Followers', k.spotify_followers_end, '', k.spotify_followers_delta + ' (' + k.spotify_followers_pct + ')') +
    kpiCard('Follower Growth', k.spotify_followers_delta, 'Net new followers', '');

  document.getElementById('yt-kpis').innerHTML =
    kpiCard('Avg Monthly Audience', k.yt_audience_avg, label, '') +
    kpiCard('Subscribers', k.yt_subs_end, '', k.yt_subs_delta + ' (' + k.yt_subs_pct + ')') +
    kpiCard('Subscriber Growth', k.yt_subs_delta, 'Net new subscribers', '');

  makeLine('ch-combined', [
    {{ label: 'Apple Podcasts', data: d.apple_followers,   color: APPLE_C }},
    {{ label: 'Spotify',        data: d.spotify_followers, color: SPOTIFY_C }},
    {{ label: 'YouTube',        data: d.yt_subs,           color: YOUTUBE_C }},
  ]);
  makeArea('ch-apple-plays',       d.apple_plays,       RED_FILL);
  makeArea('ch-apple-followers',   d.apple_followers,   APPLE_C);
  makeArea('ch-spotify-plays',     d.spotify_plays,     RED_FILL);
  makeArea('ch-spotify-followers', d.spotify_followers, SPOTIFY_C);
  makeArea('ch-yt-audience',       d.yt_audience,       RED_FILL);
  makeArea('ch-yt-subs',           d.yt_subs,           YOUTUBE_C);
}}

// ── Build toggle buttons ──
function buildToggles() {{
  const quarters = ALL_PERIODS.filter(p => p.group === 'quarter');
  const months   = ALL_PERIODS.filter(p => p.group === 'month');

  const tgQ = document.getElementById('tg-quarter');
  const tgM = document.getElementById('tg-month');

  const lbl = (txt, el) => {{
    const s = document.createElement('span');
    s.className = 'toggle-group-label'; s.textContent = txt; el.appendChild(s);
  }};

  lbl('Quarter', tgQ);
  lbl('Month', tgM);

  [...quarters, ...months].forEach(p => {{
    const btn = document.createElement('button');
    btn.className = 'period-btn' + (p.label === ALL_PERIODS[0].label ? ' active' : '');
    // Short label: strip year for months, keep "Q1" for quarter
    btn.textContent = p.group === 'quarter' ? p.label.split(' ')[0] : p.label.split(' ')[0];
    btn.title = p.label;
    btn.onclick = () => {{
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderPeriod(p.label);
    }};
    (p.group === 'quarter' ? tgQ : tgM).appendChild(btn);
  }});
}}

function showTab(id, btn) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  btn.classList.add('active');
}}

buildToggles();
renderPeriod(ALL_PERIODS[0].label);
</script>
</body>
</html>"""

out_path = os.path.join(ROOT, "MLU_Dashboard.html")
with open(out_path, "w") as f:
    f.write(html)
print(f"SAVED:{out_path}")
