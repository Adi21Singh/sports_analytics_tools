---
title: Sports Analytics Tool
emoji: ⚽
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---

# Sports Analytics Tool — User Manual

**Module:** MIS41500 Sports & Performance Analytics  
**Component:** Group Assessment (40%)  
**Team:** FC Analytics United  

---

## 1. Overview

This tool is an **interactive football analytics dashboard** built with Streamlit. It enables coaches, managers, and medical staff to monitor player performance, track training load, assess injury risk, and analyse match data — all from a single web-based interface.

The tool ships with **synthetic but realistic** data for a 25-player professional football squad spanning one season (Aug 2024 – Feb 2025). Users may also upload their own CSV files.

---

## 2. Installation & Running

### Option A — Local (Recommended for development)

```bash
# 1. Clone or unzip the project
cd sports_analytics_tool

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

The dashboard opens automatically at `http://localhost:8501`.

---

### Option B — Docker

```bash
# Build and run with a single command
docker compose up --build
```

Visit `http://localhost:8501`. No Python installation required.

To run without Docker Compose:
```bash
docker build -t sports-analytics .
docker run -p 8501:8501 sports-analytics
```

---

### Option C — Hugging Face Spaces

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces).
2. Choose **Streamlit** as the SDK.
3. Upload all project files (maintain the directory structure).
4. The space builds and deploys automatically.

---

### Option D — Google Colab

Open `SportAnalytics_Colab.ipynb` in Google Colab and run all cells. The notebook installs dependencies and creates a public tunnel via `pyngrok`.

---

## 3. Data Dictionary

### Training Session Data

| Column | Type | Description |
|---|---|---|
| `player_id` | int | Unique player identifier |
| `player_name` | str | Full player name |
| `position` | str | Playing position (GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST) |
| `date` | date | Session date |
| `session_type` | str | MD (match day), MD+1, MD-1, MD-2, MD-3, GYM |
| `duration_min` | int | Session length in minutes |
| `distance_m` | int | Total GPS distance (metres) |
| `hi_distance_m` | int | High-intensity distance >14.4 km/h (metres) |
| `sprint_count` | int | Number of sprints >25.2 km/h |
| `max_speed_kmh` | float | Maximum speed recorded (km/h) |
| `player_load` | float | Composite physical stress metric (AU) |
| `rpe` | float | Rate of Perceived Exertion (1–10, Borg CR10) |
| `session_rpe` | float | Foster's sRPE = RPE × duration |

### Match Player Data

| Column | Type | Description |
|---|---|---|
| `match_id` | int | Unique match identifier |
| `minutes_played` | int | Time on pitch |
| `distance_m` | int | In-match GPS distance |
| `passes` | int | Total pass attempts |
| `pass_completion` | float | Pass success rate (0–1) |
| `shots` | int | Total shots attempted |
| `goals` | int | Goals scored |
| `assists` | int | Goal assists |
| `tackles` | int | Successful tackles |
| `interceptions` | int | Interceptions made |
| `aerial_duels` | int | Aerial duels attempted |
| `dribbles` | int | Successful dribbles |
| `key_passes` | int | Passes leading to shot |
| `match_rating` | float | Overall match rating (5.0–9.5) |

---

## 4. Module Descriptions

### 4.1 Home (app.py)

Entry point showing season-level KPIs (points, goals, squad size, training sessions), a results timeline, top scorers, and average distance by position. Includes the data source selector — toggle between sample data and uploaded CSV.

### 4.2 📊 Player Performance

**Purpose:** Detailed individual player monitoring.

**Physical Metrics tab:**
- Session distance trend with 7-day moving average
- High-intensity distance fill chart
- Max speed distribution histogram
- Player Load vs RPE scatter (bubble size = sprint count)

**Technical Stats tab:**
- Match rating trend with user-configurable rolling average
- Per-match technical output bar chart
- Goals & assists stacked bar by match

**Performance Profile tab:**
- Spider/radar chart of 10 attributes mapped to squad percentiles
- Percentile comparison table

**Percentile Ranking tab:**
- Horizontal bar chart colour-coded: green (top third), yellow (middle), red (bottom)

### 4.3 🏆 Team Analytics

**Purpose:** Squad-level performance analysis and player role identification.

**Season Performance tab:**
- Cumulative points, goals for/against over the season
- Possession vs goals scatter
- Home/Away result comparison

**Player Clustering tab:**
- **K-means clustering** (configurable k = 3–7) on 9 match-performance features
- 2D PCA projection (Principal Component Analysis) to visualise clusters
- Hover shows individual player metrics
- Cluster summary table with average stats per group

**Squad Z-Scores tab:**
- Configurable metric selection
- Colour-coded Z-score table (green = above average, red = below)
- Full-squad Z-score heatmap

**Top Performers tab:**
- Selectable ranking metric across 8 categories

### 4.4 ⚕️ Injury Risk Monitor

**Purpose:** Early warning system for overtraining and injury risk.

**Squad Dashboard tab:**
- Traffic light overview (High Risk / Caution / Optimal / Under-training)
- Per-player ACWR and load metrics in styled table
- ACWR distribution histogram for the full squad

**ACWR Deep Dive tab:**
- **Acute:Chronic Workload Ratio** (Gabbett, 2016) plotted over the season
  - Acute window: configurable 5–10 days (default 7)
  - Chronic window: configurable 21–42 days (default 28)
  - Risk zones shaded on chart (0.8–1.3 = optimal; >1.5 = high risk)
- Training load calendar heatmap (week × day of week)

**Monotony & Strain tab:**
- **Foster's Training Monotony** = weekly mean sRPE / std sRPE
- **Strain** = mean sRPE × monotony
- Session type average load bar chart

**ML Risk Prediction tab:**
- **Random Forest classifier** (100 trees, scikit-learn) trained on synthetic injury data
- Input features: ACWR, age, monotony, strain, days since last rest
- Output: injury risk probability (0–100%)
- Gauge chart for selected player
- Full squad risk bar chart (colour-coded)
- Feature importance chart

### 4.5 ⚽ Match Analysis

**Purpose:** Post-match breakdown with shot maps and performance metrics.

**Shot Map tab:**
- Full-pitch SVG-style visualisation using Plotly shapes
- Shots plotted at true (x, y) pitch coordinates
- Size = xG value; colour = outcome (Goal / On Target / Off Target)
- Filter by player position

**xG Timeline tab:**
- **Expected Goals model**: logistic function of shot distance and angle to goal
  - Formula: `xG = 1 / (1 + exp(0.2 + 0.06·d − 2.5·|θ|))`
  - where d = distance to goal (m), θ = angle to goal (radians)
- Cumulative xG step chart with goal annotations
- Per-player xG breakdown table

**Player Ratings tab:**
- Colour-coded bar chart of all match participants
- Physical output table (distance, HI distance, sprints, max speed)

**Match Stats tab:**
- Full team-level match statistics
- Distance-by-position pie chart

### 4.6 🔄 Player Comparison

**Purpose:** Side-by-side comparison of 2–4 players.

**Radar Overlay tab:**
- Multi-player radar chart showing percentile profiles on shared axes
- Each player colour-coded; semi-transparent fill for easy comparison

**Head-to-Head Stats tab:**
- Transposed statistics table covering all key metrics
- Grouped bar chart across 7 key performance indicators

**Season Trends tab:**
- Rolling-average trend lines for any metric, all selected players on one chart
- Percentile rank bars vs full squad for 8 metrics

---

## 5. Analytical Methods

| Method | Module | Reference |
|---|---|---|
| Acute:Chronic Workload Ratio (ACWR) | Injury Risk | Gabbett (2016), *Br J Sports Med* |
| Training Monotony & Strain | Injury Risk | Foster (1998), *J Strength Cond Res* |
| K-means Clustering | Team Analytics | MacQueen (1967) |
| Principal Component Analysis (PCA) | Team Analytics | Pearson (1901) |
| Random Forest Classification | Injury Risk | Breiman (2001) |
| Z-score Normalisation | Comparison | Standard Statistics |
| Percentile Ranking (scipy) | Performance | |
| Expected Goals (xG) Model | Match Analysis | Rathke (2017) |
| Session RPE (sRPE) | Load Monitoring | Foster et al. (2001) |

---

## 6. Uploading Custom Data

Navigate to the **Home** page sidebar and select **Upload CSV**. Upload a CSV matching the training session schema above. The app will use this data wherever training metrics are displayed. Match data currently uses the built-in synthetic dataset.

---

## 7. Configurable Settings (Sidebar)

| Page | Setting | Effect |
|---|---|---|
| Player Performance | Player selector | Changes all charts to the chosen player |
| Player Performance | Date range | Filters training sessions |
| Player Performance | Rolling window | Smoothing for trend charts |
| Team Analytics | n_clusters | K-means number of groups |
| Team Analytics | Metrics | Z-score table columns |
| Injury Risk | Player selector | Individual ACWR/monotony charts |
| Injury Risk | Acute/chronic window | ACWR calculation periods |
| Match Analysis | Match selector | Switches all charts to chosen fixture |
| Match Analysis | Position filter | Filters shot map by position |
| Player Comparison | Player list | 2–4 players to compare (max 4) |

---

## 8. Limitations

- The tool uses **synthetic data** modelled on realistic professional football metrics. It is not connected to real GPS hardware or match data APIs.
- The xG model is a simplified logistic regression on shot location; it does not account for game state, goalkeeper position, or body part.
- The Random Forest injury model is trained on synthetic data; in a real deployment it should be trained and validated on historical injury records.

---

## 9. Group Member Contribution Statement

| Member | Contribution |
|---|---|
| Member 1 | Data generation module, training load analytics |
| Member 2 | Injury risk module (ACWR, ML model) |
| Member 3 | Match analysis module (shot map, xG) |
| Member 4 | Team analytics module (clustering, PCA) |
| Member 5 | Player performance module, deployment (Docker/HF) |

> *All members contributed equally to the conceptual design, documentation, and final testing.*
