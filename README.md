---
title: FC Analytics United
emoji: ⚽
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.36.0
app_file: app.py
pinned: false
---

# FC Analytics United

**Module:** MIS41500 Sports and Performance Analytics
**Assessment:** Group Assignment (40%)
**Team:** FC Analytics United

An interactive football analytics dashboard built with Streamlit. Designed for coaches, analysts, and medical staff to monitor player performance, manage training load, assess injury risk, and analyse match events from a single interface.

---

## Pages at a Glance

| Page | What it does |
|---|---|
| Dashboard | Season overview, squad fitness status, top scorers, result distribution |
| Player Performance | Training load trends, technical match stats, wellness scores |
| Player Comparison | Radar overlay, head-to-head stats, season form, percentile rankings |
| Team Analytics | K-means role clustering, Z-score benchmarking, season trends |
| Injury and Load Monitor | ACWR, PMC, monotony/strain, ML injury risk prediction |
| Match Analysis | Shot map, xG timeline, press analysis (StatsBomb open data) |
| Press Intelligence | PPDA windows, momentum index, substitution profiles (StatsBomb open data) |

---

## Setup and Installation

### Requirements

- Python 3.11 or later: https://www.python.org/downloads/
- Internet connection (StatsBomb match data downloads on first use)

Check your Python version:
```
python3 --version
```

---

### Mac / Linux - Quickstart (two commands)

```bash
bash install.sh
bash run.sh
```

`install.sh` creates a virtual environment and installs all dependencies.
`run.sh` starts the app. The browser opens automatically at http://localhost:8501

---

### Windows - Quickstart

Open Command Prompt or PowerShell in the project folder, then run:

```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

### Manual setup (alternative to install.sh)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## First-Run Notes

**Dashboard, Player Performance, Player Comparison, Team Analytics, Injury Monitor**

Load instantly. These pages use the bundled `players_data-2025_2026.csv` file (FBref 2025/26 Premier League data included in the repository).

**Match Analysis and Press Intelligence**

These pages use StatsBomb open event data (La Liga 2015/16), downloaded automatically from StatsBomb's public GitHub repository the first time each match is selected. No account or credentials are required.

- The match list loads in a few seconds on first open.
- Individual match events download the first time you select that match (2 to 5 seconds). After that they are cached locally and load instantly.
- The **Substitution Profiles** tab processes all locally cached match files the first time it is opened. This can take 30 to 60 seconds on a fresh install. Subsequent loads are instant.

---

## Stopping the App

Press `Ctrl + C` in the terminal.

---

## Troubleshooting

**"command not found: python3"**
Install Python 3.11+ from https://www.python.org/downloads/ and ensure it is on your PATH.

**"ModuleNotFoundError"**
Run `bash install.sh` again to reinstall dependencies.

**Port already in use**
```bash
venv/bin/streamlit run app.py --server.port=8502
```

**Match Analysis or Press Intelligence show an error on first load**
Check your internet connection. StatsBomb data is fetched from GitHub on first use.

**Substitution Profiles tab is slow on first open**
Expected behaviour on a fresh install. The app is processing event files for the first time. Wait 30 to 60 seconds. Every subsequent load is instant.

---

## Module Descriptions

### Dashboard

Season-level KPIs (points, win rate, goals, goal difference, average possession, average PPDA), a results timeline, top scorers bar chart, average training distance by position, and a result distribution donut chart. Includes the data source selector to toggle between bundled data and an uploaded CSV.

### Player Performance

Three tabs covering a full individual player profile:

- **Physical** - total session distance trend with 7-day moving average, high-speed running and sprint stacked area chart, acceleration/deceleration counts, session load vs perceived exertion scatter.
- **Technical** - match rating trend, per-match technical output, goals and assists bar chart, pass/dribble/tackle/aerial success rates.
- **Wellness** - composite wellness score trend, individual sub-scores (sleep, fatigue, soreness, mood), correlation heatmap.

### Player Comparison

- Radar chart showing both players' percentile profiles against the full squad.
- Head-to-head statistical table with all key per-match averages.
- Season form comparison via rolling match rating.
- Percentile rankings bar chart for side-by-side metric comparison.

### Team Analytics

- **Season Trends** - cumulative points, goals for and against by match.
- **Player Clustering** - K-means clustering (configurable k = 3 to 7) on nine match performance features. PCA projection to 2D for visualisation. Cluster summary table.
- **Z-Score Benchmarking** - configurable metric selection, colour-coded Z-score table and heatmap. Z = 0 is squad average; Z = +2 is exceptional.
- **Top Performers** - ranked leaderboards across eight metric categories.

### Injury and Load Monitor

- **Squad Dashboard** - traffic-light risk overview (High Risk / Caution / Optimal / Under-training), per-player ACWR table, squad ACWR distribution histogram.
- **ACWR and PMC** - Acute:Chronic Workload Ratio chart with configurable windows (acute 5 to 10 days, chronic 21 to 42 days). Performance Management Chart showing CTL (fitness), ATL (fatigue), and TSB (form). Training load calendar heatmap.
- **Monotony and Strain** - Foster's training monotony (rolling mean / rolling std) and strain (mean x monotony) over the season. Average load by session type.
- **ML Risk Prediction** - Random Forest classifier (150 trees) trained on synthetic injury data. Input features: ACWR, age, monotony, strain, days since rest, wellness composite, 7-day sRPE total. Output: injury probability per player.

### Match Analysis

Uses StatsBomb open event data (La Liga 2015/16).

- **Shot Map** - full pitch with all shots plotted. Bubble size represents xG. Colour and symbol represent outcome (Goal, On Target, Blocked, Off Target). Home team attacks right; away team coordinates are flipped.
- **xG Timeline** - cumulative expected goals for both teams, step-by-step through the match. Stars mark actual goals. Goal annotations show player and minute.
- **Press Analysis** - spatial distribution of defensive actions (Pressures, Interceptions, Tackles, Ball Recoveries). Location map, press-by-pitch-third bar chart, territory depth by player.

### Press Intelligence

Uses StatsBomb open event data (La Liga 2015/16). Core methodology: pressure-based PPDA (Passes Allowed Per Defensive Action) computed in 10-minute windows.

- **Press Timeline** - lollipop chart showing PPDA per window for both teams side by side. Goal and red card annotations. Direct/Defensive windows (where the opponent bypassed the press with long balls) are classified separately, and second-ball recovery rate is used as the alternative metric.
- **Context Layer** - possession by period (area chart), pressing success rate (lollipop), defensive territory depth (area chart with zone bands), second-ball recovery by pitch third.
- **Momentum Index** - composite 0 to 100 score combining PPDA performance (60% weight) and territory depth (40% weight). Clearly labelled as a heuristic.
- **Substitution Profiles** - per-player pressing stats (pressures per match, regain rate, late pressures per match) aggregated from all locally cached matches. Radar chart comparison of two selected players.
- **Opponent History** - season-long PPDA trend for the opponent as pressing team, across all cached matches. Coloured dots, trend line, and current match highlighted.
- **Threshold Validator** - backtests the PPDA collapse threshold across all La Liga 2015/16 matches and reports the distribution of window categories (Build-up, Mixed, Direct/Defensive).

---

## Analytical Methods

| Method | Used in | Reference |
|---|---|---|
| ACWR - Acute:Chronic Workload Ratio | Injury Monitor | Gabbett (2016), Br J Sports Med |
| Training Monotony and Strain | Injury Monitor | Foster (1998), J Strength Cond Res |
| Performance Management Chart (CTL/ATL/TSB) | Injury Monitor | Banister (1991) |
| Random Forest Classification | Injury Monitor | Breiman (2001) |
| K-means Clustering | Team Analytics | MacQueen (1967) |
| Principal Component Analysis | Team Analytics | Pearson (1901) |
| Z-score Normalisation | Team Analytics, Comparison | Standard statistics |
| Percentile Ranking | Performance, Comparison | scipy.stats |
| Expected Goals model (xG) | Match Analysis | Rathke (2017) |
| Session RPE (sRPE) | Load Monitoring | Foster et al. (2001) |
| Pressure-based PPDA | Press Intelligence | Trainor (2014), StatsBomb |
| Build-up Tendency Classifier | Press Intelligence | Original extension |
| Match Momentum Index | Press Intelligence | Original heuristic |

---

## Data Sources

| Data | Source | Coverage |
|---|---|---|
| Player stats (Dashboard, Performance, Comparison, Team, Injury) | FBref 2025/26 Premier League CSV (bundled) | Full squad, season totals disaggregated to per-match |
| Match events (Match Analysis, Press Intelligence) | StatsBomb open data via statsbombpy | La Liga 2015/16, 380 matches |

---

## Key Design Decisions

**Why La Liga 2015/16?**
It is StatsBomb's flagship open dataset: 380 matches with complete pressure event records, which are required for PPDA computation. Larger than FIFA World Cup (64 matches), making the threshold validator and opponent history statistically meaningful.

**Synthetic player data**
The player performance, injury, and comparison pages use per-match records disaggregated from real 2025/26 FBref season totals, with position-specific physical profiles filling in GPS metrics not available from FBref. This gives realistic distributions while remaining on open data.

**PPDA threshold**
The default threshold of 10.0 is validated via backtest across all 380 La Liga 2015/16 matches (see Threshold Validator tab). It is configurable via sidebar slider.

---

## Limitations

- Player performance pages use synthetic per-match records derived from real season totals. They represent plausible distributions, not actual match-by-match data.
- The xG model uses shot location only. It does not account for game state, goalkeeper position, or body part.
- The ML injury risk model is trained on synthetic data. In a real deployment it would require historical injury records for training and validation.
- Match Analysis and Press Intelligence are post-match only. StatsBomb open data does not include a live feed.
- Substitution pressing profiles are built from locally cached matches only. The more matches are loaded, the more reliable the profiles.

---

## Group Contribution Statement

| Member | Primary Contribution |
|---|---|
| Member 1 | Data generation module, training load analytics, FBref integration |
| Member 2 | Injury risk module (ACWR, PMC, ML model) |
| Member 3 | Match Analysis (shot map, xG timeline, press analysis) |
| Member 4 | Team Analytics (K-means clustering, Z-scores, season trends) |
| Member 5 | Press Intelligence module, UI design, deployment |

All members contributed to conceptual design, documentation, and final testing.
