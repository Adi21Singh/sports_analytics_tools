# FC Analytics United — User Manual

**Module:** MIS41500 Sports and Performance Analytics  
**Assessment Component:** Group Assessment (40%)  
**Sport:** Football (Soccer)  
**Team:** FC Analytics United

---

## Table of Contents

1. [What the Tool Does](#1-what-the-tool-does)
2. [How to Run It](#2-how-to-run-it)
3. [Navigating the Tool](#3-navigating-the-tool)
4. [Module Guide](#4-module-guide)
   - 4.1 Match Analysis
   - 4.2 Press Intelligence
5. [Configurable Settings](#5-configurable-settings)
6. [KPI Definitions](#6-kpi-definitions)
7. [Analytics Methods Explained](#7-analytics-methods-explained)
8. [Data Source](#8-data-source)
9. [Limitations](#9-limitations)
10. [Group Member Contribution Statement](#10-group-member-contribution-statement)

---

## 1. What the Tool Does

This tool is a web-based football analytics dashboard focused on match and pressing analysis. It is built for coaches, analysts, and tactical staff to break down match events, evaluate pressing effectiveness, and track opponent tendencies — all from a single interface.

The tool uses StatsBomb open event data covering the full La Liga 2015/16 season (380 matches). No account or credentials are required. Data downloads automatically on first use and is cached locally for instant subsequent access.

The tool covers two areas:

- **Match Analysis** — shot maps, expected goals timelines, and press breakdowns for any selected match
- **Press Intelligence** — PPDA-based pressing analysis in 10-minute windows, momentum tracking, substitution profiles, and season-long opponent history

---

## 2. How to Run It

### Option A: Local (Recommended)

You need Python 3.11 or later installed. Open a terminal in the project folder and run:

```bash
bash install.sh
bash run.sh
```

`install.sh` creates a virtual environment and installs all dependencies. `run.sh` starts the app. The browser opens automatically at `http://localhost:8501`. You only need to run `install.sh` once.

If you prefer manual setup:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Option B: Hugging Face Spaces

1. Create a new Space at huggingface.co/spaces.
2. Set the SDK to Streamlit.
3. Upload all project files, keeping the same folder structure.
4. The Space builds and deploys automatically.

The `README.md` already contains the correct configuration header for Hugging Face.

---

## 3. Navigating the Tool

The left sidebar has the main navigation menu:

| Section | Pages |
|---|---|
| La Liga 2015/16 | Match Analysis, Press Intelligence |

Select a match from the sidebar dropdown on either page. The match list loads in a few seconds on first open. Individual match events download the first time you select that match (2–5 seconds) and are cached locally after that.

---

## 4. Module Guide

### 4.1 Match Analysis

Select a competition, season, and match from the sidebar dropdowns. Three tabs are available.

**Shot Map tab**

A full-pitch diagram drawn in Plotly. Each shot is plotted at the coordinates where it was taken. Bubble size represents the xG value of that shot — larger bubbles are higher-quality chances. Shape and colour indicate the outcome: stars for goals, circles for on-target saves, crosses for blocked or off-target shots.

A table underneath lists every shot with player name, minute, xG value, outcome, and whether it was a goal.

**xG Timeline tab**

Cumulative expected goals plotted by minute for both teams, using a step line so each shot's xG contribution is visible as it happens. Actual goals are marked with a star annotation showing the player name and minute. The chart makes it easy to see which team was creating better chances across the match, and where the momentum shifted.

**Press Analysis tab**

Spatial breakdown of all pressing actions (pressures, interceptions, tackles, ball recoveries) for each team. A pitch map shows where each action occurred. A bar chart breaks press volume by pitch third (defensive, middle, attacking). A territory depth chart shows which players pressed highest up the pitch.

---

### 4.2 Press Intelligence

Select a match from the sidebar. Six tabs are available.

**Press Timeline tab**

The main view. PPDA (Passes Allowed Per Defensive Action) is computed in 10-minute tumbling windows for both teams and displayed as a lollipop chart. Lower PPDA means more aggressive pressing.

Goal and red card events are annotated on the timeline so you can see how pressing intensity relates to match events. Windows classified as Direct/Defensive (where the opponent bypassed the press with long balls) are shown in a different colour, and second-ball recovery rate is displayed as the headline metric for those windows instead of PPDA, which becomes unreliable when the opponent is not building through the defensive zone.

You can adjust the PPDA collapse threshold using the slider in the sidebar. The default is 10.0.

**Context Layer tab**

Four supporting charts:
- Possession by period (stacked area chart)
- Pressing success rate by window (lollipop)
- Defensive territory depth by 10-minute period (area chart with zone bands marking defensive, middle, and attacking thirds)
- Second-ball recovery rate by pitch third

**Momentum Index tab**

A composite 0–100 score combining PPDA performance (60% weight) and territory depth (40% weight), plotted across all windows. This is a heuristic index — it is clearly labelled as such. It gives a single number to describe which team controlled the match at each point.

**Substitution Profiles tab**

Per-player pressing statistics aggregated from all locally cached matches: pressures per match, pressing regain rate, and late-game pressures per match. Select two players from the dropdowns to compare them on a radar chart.

This tab processes all locally cached match files on first open. On a fresh install this can take 30–60 seconds. Every subsequent load is instant.

**Opponent History tab**

The opponent's PPDA trend across all cached La Liga 2015/16 matches where they were the pressing team. Each match appears as a dot. A trend line shows whether their pressing has been improving or declining across the season. The current match is highlighted.

**Threshold Validator tab**

Backtests the PPDA collapse threshold (configurable in the sidebar) across all 380 La Liga 2015/16 matches and reports the distribution of window categories: Build-up (PPDA is a reliable signal), Mixed, and Direct/Defensive (PPDA is unreliable). This gives analytical confidence in the threshold value being used.

---

## 5. Configurable Settings

| Page | Setting | Where | What it changes |
|---|---|---|---|
| Match Analysis | Match selector | Sidebar | Switches all tabs to the chosen fixture |
| Match Analysis | Competition / Season | Sidebar | Filters the available match list |
| Press Intelligence | Match selector | Sidebar | Switches all tabs to the chosen fixture |
| Press Intelligence | PPDA threshold | Sidebar slider | The collapse threshold used in all window classifications and the Threshold Validator |
| Press Intelligence | Player selectors | Substitution Profiles tab | Two players to compare on the radar chart |

The PPDA threshold defaults to 10.0, validated against all 380 La Liga 2015/16 matches. Raising it increases the proportion of windows classified as Build-up; lowering it flags more windows as Mixed or Direct/Defensive.

---

## 6. KPI Definitions

| KPI | Definition |
|---|---|
| xG | Expected Goals: the probability that a shot results in a goal, based on shot location |
| PPDA | Passes Allowed Per Defensive Action. Computed as (opponent passes in their defensive zone) / (our defensive actions in that zone). Lower = more aggressive press. |
| Press success rate | Pressing actions that won possession divided by total pressing actions |
| Territory depth | Average x-coordinate of pressing actions, normalised to the opponent's pitch direction. Higher = pressing further up the pitch. |
| Momentum Index | Composite heuristic: 60% PPDA performance score + 40% territory depth score, scaled to 0–100. |
| Second-ball recovery rate | In Direct/Defensive windows: proportion of long-ball sequences where the pressing team recovered the second ball. Used as an alternative press effectiveness metric when PPDA is unreliable. |
| Regain rate | Pressures that led to possession won, divided by total pressures. A per-player metric in Substitution Profiles. |

---

## 7. Analytics Methods Explained

### PPDA (Passes Allowed Per Defensive Action)

PPDA measures how aggressively a team presses by counting how many passes the opponent is allowed to complete in their own defensive zone for every defensive action the pressing team makes in that zone.

A PPDA of 5 means the pressing team makes one defensive action for every 5 opponent passes — aggressive pressing. A PPDA of 15 means the opponent is passing relatively freely — a passive defensive block.

This tool computes PPDA in 10-minute tumbling windows using StatsBomb pressure event data. The defensive zone is defined as the possessing team's own half (x < 72 m on a 120 m pitch, team-relative), validated against all 380 La Liga 2015/16 matches.

Source: Trainor (2014); StatsBomb press analysis methodology.

### Build-up Tendency Classifier

PPDA has a known false-positive problem: when an opponent plays direct football (long balls, aerial play), their pass count in their defensive zone is near zero, producing artificially low PPDA even when the press had no meaningful effect.

The Build-up Tendency Classifier identifies these windows by measuring the ratio of long-ball events to total passes in each window. Windows above the threshold are classified as Direct/Defensive, and the second-ball recovery rate is surfaced as the headline metric instead.

This is an original extension built on top of standard PPDA methodology.

### Match Momentum Index

A composite 0–100 heuristic combining pressing quality (PPDA score, 60% weight) and territorial control (depth of pressing actions, 40% weight). It provides a single number to describe match control at each 10-minute period. It is clearly labelled as a heuristic throughout the tool.

### Expected Goals (xG)

xG estimates how likely a shot is to result in a goal based on where it was taken. A central shot inside the six-yard box has a high xG. A long-range shot from the flank has a low xG.

This tool uses shot location data from StatsBomb events. xG values are provided by StatsBomb for each shot event in the dataset.

Source: Rathke, A. (2017). An examination of expected goals and shot quality. *Journal of Human Sport and Exercise*, 12(2).

---

## 8. Data Source

All data in this tool comes from StatsBomb's open event dataset, fetched via the `statsbombpy` library.

| Dataset | Coverage |
|---|---|
| La Liga 2015/16 match events | 380 matches, full event-level detail |

Data is downloaded automatically over the internet on first use and cached to disk at `analytics/sb_press_cache/`. No API key or account is required. Subsequent loads use the local cache and are instant.

StatsBomb open data is provided under the StatsBomb Open Data Licence. It is used here for academic purposes only.

---

## 9. Limitations

- All analysis is post-match. StatsBomb open data has no live feed.
- The xG values are from StatsBomb's model. They account for shot location and some context, but not all factors (e.g. goalkeeper position at time of shot).
- The PPDA threshold (default 10.0) was validated on La Liga 2015/16 only. Its transferability to other leagues or seasons is untested.
- Substitution pressing profiles are built from locally cached matches only. Profiles become more reliable as more matches are loaded and cached.
- The Momentum Index is a heuristic combining two metrics with fixed weights. It is not a peer-reviewed model.

---

## 10. Group Member Contribution Statement

| Member | Primary Contribution |
|---|---|
| Member 1 | Data generation module, training load analytics, FBref integration |
| Member 2 | Injury risk module (ACWR, PMC, ML model) |
| Member 3 | Match Analysis (shot map, xG timeline, press analysis) |
| Member 4 | Team Analytics (K-means clustering, Z-scores, season trends) |
| Member 5 | Press Intelligence module, UI design, deployment |

All members contributed to conceptual design, documentation, and final testing.

---

*MIS41500 Sports and Performance Analytics — Group Assessment Submission*
