# FC Analytics United — Sports Analytics Platform

**Module:** MIS41500 Sports and Performance Analytics  
**Assessment:** Group Assignment (40%)  
**Team:** FC Analytics United

A Streamlit dashboard for football press and match analytics, built on StatsBomb open event data (La Liga 2015/16).

---

## Table of Contents

- [Architecture](#architecture)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [Pages](#pages)
- [Module Reference](#module-reference)
- [Configuration](#configuration)
- [Data Sources](#data-sources)
- [Analytical Methods](#analytical-methods)
- [Limitations](#limitations)

---

## Architecture

```
sports-analytics-group-assignment/
├── app.py                    # Streamlit entry point, page routing
├── config.py                 # Central config: colours, thresholds, position profiles
├── requirements.txt          # Pinned dependencies
├── pyproject.toml            # uv project manifest
│
├── pages/
│   ├── match_analysis.py     # Shot map, xG timeline, press breakdown
│   └── press_intelligence.py # PPDA windows, momentum index, substitution profiles
│
├── analytics/
│   ├── press_engine.py       # Core PPDA engine (active)
│   ├── clustering.py         # K-means player clustering (legacy, unused)
│   ├── load_monitoring.py    # ACWR / PMC / monotony (legacy, unused)
│   ├── performance.py        # Player performance helpers (legacy, unused)
│   ├── risk_model.py         # ML injury risk model (legacy, unused)
│   └── validate_xg.py        # xG model validation (legacy, unused)
│
├── ui/
│   ├── components.py         # Shared UI: kpi_card, draw_pitch, section_header …
│   ├── styles.py             # Global CSS injected via st.markdown
│   └── data_source.py        # Data source selector widget
│
├── data/
│   ├── generator.py          # Synthetic player data generator (legacy)
│   └── real_loader.py        # FBref CSV → per-match records (legacy)
│
└── docs/
    └── Press_Intelligence_Module_v2.docx
```

**Active code path:** `app.py` → `pages/match_analysis.py` + `pages/press_intelligence.py` → `analytics/press_engine.py` + `ui/` + `config.py`

The `data/`, `analytics/clustering.py`, and other analytics files are retained from the previous version but are not imported by any live page.

---

## Setup

### Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or plain `pip`
- Internet connection (StatsBomb data downloads on first match selection)

### With uv (recommended)

```bash
uv sync
```

This reads `pyproject.toml` + `uv.lock` and creates `.venv` with all pinned dependencies.

### With pip

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Shell scripts

```bash
bash install.sh   # creates venv + installs deps
bash run.sh       # starts the app
```

---

## Running the App

```bash
uv run streamlit run app.py
# or
source .venv/bin/activate && streamlit run app.py
```

Opens at `http://localhost:8501`.

To use a different port:

```bash
uv run streamlit run app.py --server.port=8502
```

---

## Pages

### Match Analysis (`pages/match_analysis.py`)

Three tabs using StatsBomb event data for a selected match:

| Tab | What it shows |
|---|---|
| Shot Map | Full pitch with shots plotted. Bubble size = xG. Colour/symbol = outcome (Goal, On Target, Blocked, Off Target). Team coordinates are normalised (home attacks right). |
| xG Timeline | Cumulative expected goals for both teams, step by step through the match. Stars mark actual goals with player + minute annotations. |
| Press Analysis | Spatial distribution of defensive actions (Pressures, Interceptions, Tackles, Ball Recoveries). Location heatmap, press-by-pitch-third bar chart, territory depth by player. |

**Coordinate system:** StatsBomb stores events in a team-relative frame (x=0 own goal, x=120 opponent goal). Shot x values cluster near 120 for all teams — no direction flip needed for shots. Scale to pitch drawing: `x_plot = x * 105/120`, `y_plot = y * 68/80`.

### Press Intelligence (`pages/press_intelligence.py`)

Six tabs using PPDA computed in 10-minute tumbling windows:

| Tab | What it shows |
|---|---|
| Press Timeline | PPDA per window for both teams (lollipop). Goal and red-card annotations. Direct/Defensive windows flagged separately with second-ball recovery rate as the headline metric. |
| Context Layer | Possession by period (area chart), pressing success rate, defensive territory depth by zone, second-ball recovery by pitch third. |
| Momentum Index | Composite 0–100 score: 60% PPDA performance + 40% territory depth. Labelled as a heuristic. |
| Substitution Profiles | Per-player pressing stats (pressures/match, regain rate, late pressures/match) aggregated from all locally cached matches. Radar comparison of two selected players. |
| Opponent History | Season-long PPDA trend for the opponent across all cached matches. Coloured dots, trend line, current match highlighted. |
| Threshold Validator | Backtests the PPDA collapse threshold across all 380 La Liga 2015/16 matches. Reports distribution of window categories. |

---

## Module Reference

### `analytics/press_engine.py`

The core analytics engine. All public functions are imported by both page files.

| Symbol | Type | Description |
|---|---|---|
| `load_sb_matches()` | `-> pd.DataFrame` | Fetches the La Liga 2015/16 match list from StatsBomb. Cached with `@st.cache_data`. |
| `load_match_events(match_id)` | `-> pd.DataFrame` | Downloads and caches a single match's event data to `analytics/sb_press_cache/`. Subsequent calls are instant (disk cache). |
| `compute_ppda_windows(events, team, threshold)` | `-> pd.DataFrame` | Computes PPDA in 10-minute tumbling windows for `team`. Returns one row per window with columns: `window_start`, `ppda`, `category`, `second_ball_recovery_rate`, `events_count`. |
| `run_threshold_validator(threshold)` | `-> pd.DataFrame` | Iterates all locally cached match files and classifies windows. Used by the Threshold Validator tab. |
| `SB_AVAILABLE` | `bool` | `False` if `statsbombpy` is not installed; pages gate on this. |
| `CACHE_DIR` | `str` | Absolute path to `analytics/sb_press_cache/`. |
| `PPDA_COLLAPSE_THRESHOLD` | `float` | Default PPDA threshold (10.0). Configurable via sidebar slider. |
| `CATEGORY_BUILDUP` / `CATEGORY_MIXED` / `CATEGORY_DIRECT` | `str` | Window category labels for the build-up tendency classifier. |
| `MIN_EVENTS_GREY_OUT` | `int` | Minimum event count to render a window; below this it is greyed out. |
| `DIRECT_PPDA_WEIGHT_FACTOR` | `float` | Weight multiplier applied to PPDA in Direct windows for the momentum index. |

**Why the Build-up Tendency Classifier exists:** PPDA's numerator counts only opponent passes in their own defensive zone. When an opponent plays direct football (long balls, aerial play), their pass count in that zone is near zero, producing artificially low PPDA even when the press had no effect. The classifier identifies these windows so the UI can surface second-ball recovery rate instead.

**PPDA defensive zone:** `x < 72.0 m` (60% of the 120 m pitch, team-relative). Validated against all 380 La Liga 2015/16 matches.

**Disk cache format:** One JSON file per match at `analytics/sb_press_cache/<match_id>.json`. First load fetches from StatsBomb GitHub (2–5 s); subsequent loads are instant.

---

### `ui/components.py`

Shared building blocks used by both pages.

| Function | Returns | Description |
|---|---|---|
| `kpi_card(label, value, delta, sub, accent)` | `str` (HTML) | Styled KPI card. Render with `st.markdown(..., unsafe_allow_html=True)`. |
| `kpi_row(cards)` | `None` | Renders a list of `kpi_card` HTML strings in a horizontal row. |
| `section_header(title, sub)` | `None` | Renders a styled section heading. |
| `draw_pitch(fig, pitch_len, pitch_wid)` | `go.Figure` | Adds pitch lines/arcs to a Plotly figure using StatsBomb coordinates. |
| `style_chart(fig)` | `go.Figure` | Applies `CHART_BASE` layout to a Plotly figure. |
| `info_box(text)` | `None` | Renders a styled info callout. |
| `info_popover(label, content)` | `None` | Renders a Streamlit popover with explanatory text. |
| `match_hero(home, away, score)` | `None` | Large match header card. |
| `verdict_card(title, body, colour)` | `None` | Coloured verdict/summary card. |
| `stat_strip(stats)` | `None` | Horizontal strip of label–value pairs. |

### `ui/styles.py`

Exports a single `apply()` function that injects global CSS (dark theme, KPI card styles, chart overrides) via `st.markdown`. Called at the top of each page.

### `config.py`

Single source of truth for all magic numbers and design tokens. Key exports:

| Name | Type | Description |
|---|---|---|
| `COLORS` | `dict` | Design token palette (bg, surface, primary teal, etc.) |
| `PALETTE` | `list[str]` | 10-colour chart sequence |
| `CHART_BASE` | `dict` | Base `update_layout` kwargs for all Plotly figures |
| `ACWR_ZONES` | `dict` | ACWR zone boundaries, colours, labels |
| `WELLNESS_WEIGHTS` | `dict` | Evidence-based wellness composite weights (McLean 2010) |
| `POSITION_PROFILES` | `dict` | Per-position mean/std for 28 match metrics (GK → ST) |
| `SESSION_FACTORS` | `dict` | Scaling factors per session type (MD, MD±n, GYM) |
| `acwr_zone(value)` | `func` | Returns zone name string for a given ACWR value |

---

## Configuration

All tuneable values live in `config.py`. No environment variables required.

The PPDA threshold (default 10.0) is additionally exposed as a sidebar slider in the Press Intelligence page — changes are session-scoped only.

---

## Data Sources

| Data | Source | Coverage |
|---|---|---|
| Match events (Match Analysis, Press Intelligence) | `statsbombpy` → StatsBomb public GitHub | La Liga 2015/16, 380 matches |

StatsBomb data is fetched over HTTP on first use and cached to disk under `analytics/sb_press_cache/`. No API key or account required.

**First-run behaviour:**
- Match list: loads in a few seconds.
- Per-match events: 2–5 s per match on first selection; instant thereafter.
- Substitution Profiles tab: processes all locally cached matches on first open (30–60 s on a fresh install with no cached files; instant on subsequent loads).

---

## Analytical Methods

| Method | Used in | Reference |
|---|---|---|
| Pressure-based PPDA | Press Intelligence | Trainor (2014), StatsBomb |
| Build-up Tendency Classifier | Press Intelligence | Original extension |
| Match Momentum Index | Press Intelligence | Original heuristic (PPDA 60% + territory 40%) |
| Expected Goals (xG) | Match Analysis | Rathke (2017) — location-only model |
| ACWR (Acute:Chronic Workload Ratio) | `analytics/load_monitoring.py` (legacy) | Gabbett (2016), Br J Sports Med |
| Training Monotony and Strain | `analytics/load_monitoring.py` (legacy) | Foster (1998), J Strength Cond Res |
| Performance Management Chart | `analytics/load_monitoring.py` (legacy) | Banister (1991) |
| Random Forest Classification | `analytics/risk_model.py` (legacy) | Breiman (2001) |
| K-means Clustering + PCA | `analytics/clustering.py` (legacy) | MacQueen (1967), Pearson (1901) |

---

## Limitations

- xG model uses shot location only. Does not account for game state, goalkeeper position, or body part.
- Substitution pressing profiles are built from locally cached matches only. Profiles become more reliable as more matches are loaded.
- All analysis is post-match. StatsBomb open data has no live feed.
- PPDA threshold of 10.0 was validated on La Liga 2015/16 only. Transferability to other leagues/seasons is untested.

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
