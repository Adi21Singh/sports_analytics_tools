# Sports Analytics Tool — User Manual

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
   - 4.1 Dashboard  
   - 4.2 Player Performance  
   - 4.3 Team Analytics  
   - 4.4 Injury and Load Monitor  
   - 4.5 Match Analysis  
   - 4.6 Player Comparison  
5. [KPI Definitions](#5-kpi-definitions)  
6. [Analytics Methods Explained](#6-analytics-methods-explained)  
7. [Data Dictionary](#7-data-dictionary)  
8. [Uploading Your Own Data](#8-uploading-your-own-data)  
9. [Configurable Settings](#9-configurable-settings)  
10. [Group Member Contribution Statement](#10-group-member-contribution-statement)  

---

## 1. What the Tool Does

This tool is a web-based football analytics dashboard built for coaches, team managers, and medical staff. It takes training session data, match data, and player wellness scores, then turns them into charts, tables, and risk alerts that support day-to-day decisions.

The tool ships with a full synthetic dataset for a 25-player squad across one season. You can also upload your own CSV file. Everything updates automatically when you change the filters in the sidebar.

The tool covers six areas:

- Season overview and squad readiness
- Individual player physical and technical performance
- Squad-level analysis and player role clustering
- Training load and injury risk monitoring
- Match-by-match analysis with shot maps and expected goals
- Side-by-side player comparison

---

## 2. How to Run It

### Option A: Local (Recommended)

You need Python 3.12 installed. Open a terminal in the project folder and run:

```bash
bash run.sh
```

The script creates a virtual environment, installs all dependencies, and opens the app at `http://localhost:8501`. You only need to do the full setup once. After that, `bash run.sh` starts the app in a few seconds.

If you prefer to run the steps manually:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

### Option B: Docker

You need Docker Desktop installed. Run:

```bash
docker compose up --build
```

Then open `http://localhost:8501`. No Python setup needed.

To stop it: press `Ctrl+C` in the terminal, then run `docker compose down`.

### Option C: Hugging Face Spaces

1. Create a new Space at huggingface.co/spaces.
2. Set the SDK to Streamlit.
3. Upload all project files, keeping the same folder structure.
4. The Space builds and deploys on its own.

The `README.md` already contains the correct configuration header for Hugging Face.

### Option D: Google Colab

Open `SportAnalytics_Colab.ipynb` in Google Colab and run all cells from top to bottom. The notebook installs the required packages, uploads your project files, and creates a public link using ngrok so you can open the app in a browser.

---

## 3. Navigating the Tool

The left sidebar has the main navigation menu, split into four sections:

| Section | Pages |
|---|---|
| Overview | Dashboard |
| Player Analytics | Player Performance, Player Comparison |
| Team Analytics | Team Analytics, Match Analysis |
| Medical and Load | Injury and Load Monitor |

Each page also has its own sidebar controls: player selectors, date pickers, and sliders. These filter the data shown on that page only.

---

## 4. Module Guide

### 4.1 Dashboard

The Dashboard gives a one-page summary of the whole season.

**What you see at the top:** Six KPI cards covering points, win rate, goals scored, goals conceded, average possession, and average PPDA (a pressing intensity measure).

**Squad Readiness cards** show how many players are currently in each ACWR risk zone: optimal, caution, high risk, or under-training. This gives the medical team a quick morning check.

**Season Results Timeline** shows goals scored per match as bars, colour-coded by result, with cumulative points plotted as a line on the right axis.

**Top Scorers** ranks players by total goals. Hover over any bar to see their expected goals (xG) total alongside actual goals.

**Average Distance by Position** shows how far each position group covers in training on average. Useful for spotting if any position is being under or over-loaded.

---

### 4.2 Player Performance

Select a player from the sidebar dropdown. You can also filter by date range and choose the rolling window for trend charts.

**Physical tab**

Six KPI cards show average distance, high-speed running distance (HSR), sprint distance, peak speed, work rate, and high metabolic load (HML) for the selected period.

Below the cards:

- Distance trend: each session shown as a bar, 7-day moving average as a line
- HSR and Sprint breakdown: stacked area chart comparing the two speed zones
- Acceleration and deceleration counts: how many explosive efforts per session
- Load vs Exertion scatter: each dot is a session, bubble size represents HML

**Technical tab**

KPI cards cover goals, assists, total xG, total xA (expected assists), xG per 90 minutes, average match rating, pass accuracy, dribble success rate, tackle success rate, aerial win rate, pressing success rate, and goal involvement per 90.

Below the cards:

- Match rating trend with your chosen rolling average and a 7.0 benchmark line
- Goals and assists stacked bar per match
- Technical output bar chart: passes, key passes, progressive passes, dribbles won, pressures, touches in box

**Wellness tab**

Five KPI cards: composite wellness score, average sleep, average fatigue, average soreness, average mood.

The composite wellness line chart shows daily scores with a 7-day moving average. A dotted line at 6.0 marks the low readiness threshold. Below that, a second chart breaks out each wellness component so you can see which factor is pulling the score down.

**Radar Profile tab**

A spider chart with 11 attributes (distance, HSR, sprints, shots, xG, passes, pass accuracy, key passes, tackles won, pressures, match rating). Each axis shows the player's percentile rank against the full squad, not the raw value. A horizontal bar chart underneath shows the same percentiles in a format that is easier to read at a glance. Bars are colour-coded: green for top third, yellow for middle, red for bottom.

---

### 4.3 Team Analytics

**Season Trends tab**

Cumulative points, goals scored, and goals conceded plotted by match number. Two charts underneath: possession vs goals (scatter coloured by result) and a home/away result comparison.

**Player Clustering tab**

This uses K-means to group players into performance archetypes based on nine match-averaged metrics. The number of clusters is controlled from the sidebar (between 3 and 7).

The results appear as a scatter plot where each dot is a player. The two axes are PCA dimensions, which compress nine metrics into two coordinates for display purposes. The percentage of variance explained is shown as a caption.

Hovering over a dot shows the player name, position, and key stats. The cluster summary table underneath shows average stats for each group.

**Z-Score Benchmarks tab**

Pick the metrics you want to compare from the sidebar. The table shows each player's Z-score for those metrics. A Z-score of +1.0 means the player is one standard deviation above the squad average. The cells are colour-coded: green for well above average, red for well below. A heatmap version of the same table gives a visual overview of the whole squad at once.

**Top Performers tab**

Choose any metric from the dropdown. The tool ranks all players and shows the top 12 as a bar chart. Covers goals, assists, xG, xA, ratings, physical output, and more.

---

### 4.4 Injury and Load Monitor

**Squad Dashboard tab**

A table showing every player's current ACWR value, risk zone, acute and chronic load, session availability percentage, and latest wellness score. Rows are colour-coded by risk zone. The six KPI cards at the top summarise how many players are in each zone and the squad averages for availability and wellness.

The ACWR histogram at the bottom shows the full squad's current distribution across risk zones.

**ACWR and PMC tab**

Select a player from the sidebar.

The ACWR chart shows the acute load, chronic load, and the ratio over the full season. Risk zone bands are shaded in the background. You can adjust the acute window (5 to 10 days) and chronic window (21 to 42 days) from the sidebar.

Below that, the Performance Management Chart (PMC) shows three lines:

- CTL (Fitness): the 42-day exponential moving average of daily load
- ATL (Fatigue): the 7-day exponential moving average
- TSB (Form): CTL minus ATL. Positive values mean the player is fresh. Negative values mean they are carrying fatigue.

A training load calendar heatmap at the bottom shows the daily sRPE load across weeks and days of the week, which makes it easy to spot training spikes.

**Monotony and Strain tab**

Monotony measures how repetitive the training has been over the past seven days. It is calculated as the weekly mean load divided by the standard deviation. High monotony (above 2.0) means the player is doing the same amount of work every day, which research links to overuse injuries. Strain combines monotony and volume. A session type breakdown shows which types of session contribute most to load.

**ML Risk Prediction tab**

A Random Forest model predicts each player's injury risk probability based on ACWR, age, monotony, strain, days since their last rest day, wellness composite, and the last seven days of sRPE.

A gauge shows the selected player's risk score. The squad bar chart ranks all players. A feature importance chart shows which inputs the model relies on most.

---

### 4.5 Match Analysis

Select a match from the sidebar dropdown. You can also filter the shot map by player position.

**Shot Map tab**

A full-pitch diagram drawn in Plotly. Each shot appears as a circle (or star for goals) at the location it was taken. The bubble size represents the xG value of that shot. A table underneath lists every shot with player, minute, xG, whether it was on target, and whether it was a goal.

**xG Timeline tab**

Cumulative expected goals plotted by minute of the match, using a step line so each shot's contribution is visible. Goals are marked with a vertical dashed line and player name. Total xG is shown as a dotted horizontal reference line.

**Player Ratings tab**

A horizontal bar chart of all players in the match, colour-coded by rating. A physical output table below shows distance, HSR, sprint count, max speed, and work rate per player.

**Match Stats tab**

A full list of team statistics for the match: total distance, HSR, sprint distance, passes, completion rate, progressive passes, pressures, pressures won, key passes, shots, shot accuracy, xG, possession, and PPDA. A distance-by-position pie chart and a pressing volume chart sit alongside it.

---

### 4.6 Player Comparison

Select two to four players from the sidebar multi-select.

**Radar Overlay tab**

All selected players appear on the same spider chart in different colours. The axes are the same 11 attributes as the Player Performance radar, all shown as squad percentiles.

**Head-to-Head tab**

A transposed table showing every player's season averages side by side. A grouped bar chart highlights eight key metrics for quick visual comparison.

**Season Trends tab**

Pick any metric and see each player's rolling 4-match average plotted as a line. A percentile rank bar chart underneath compares each player against the full squad on ten metrics.

---

## 5. KPI Definitions

### Physical

| KPI | Definition |
|---|---|
| Distance (m) | Total GPS distance covered in a session or match |
| HSR (m) | High-Speed Running distance at speeds above 19.8 km/h |
| Sprint Distance (m) | Distance covered at speeds above 25.2 km/h |
| Sprint Count | Number of sprint efforts above 25.2 km/h |
| Acceleration Count | Number of acceleration efforts above 2.5 m/s squared |
| Deceleration Count | Number of deceleration efforts below -2.5 m/s squared |
| Max Speed (km/h) | Peak speed recorded in the session |
| Work Rate (m/min) | Total distance divided by time on the pitch |
| Player Load (AU) | A composite measure of physical stress from the GPS unit |
| HML (m) | High Metabolic Load distance, combining sprint and acceleration demands |
| sRPE | Session RPE: the player's Rating of Perceived Exertion multiplied by session duration in minutes. Used to quantify training load without GPS. |

### Technical

| KPI | Definition |
|---|---|
| xG | Expected Goals: the probability of a shot resulting in a goal based on shot location |
| xA | Expected Assists: the xG of the shot that followed a player's pass |
| xG per 90 | xG scaled to 90 minutes of playing time |
| xA per 90 | xA scaled to 90 minutes of playing time |
| Pass Accuracy | Passes completed divided by passes attempted |
| Progressive Passes | Passes that move the ball at least 10 metres towards the opponent's goal |
| Key Passes | Passes that directly create a shot |
| Dribble Success Rate | Successful take-ons divided by attempted take-ons |
| Tackle Success Rate | Tackles won divided by tackles attempted |
| Aerial Win Rate | Aerial duels won divided by aerial duels contested |
| Press Success Rate | Pressures that won possession divided by total pressing actions |
| Goal Involvement per 90 | Goals plus assists, scaled to 90 minutes |
| Match Rating | An overall performance score from 4.5 to 9.5, aggregated from physical and technical output |
| PPDA | Passes Allowed Per Defensive Action. A team-level pressing metric. Lower values mean the team pressed higher and more aggressively. |

### Load and Wellness

| KPI | Definition |
|---|---|
| ACWR | Acute:Chronic Workload Ratio. Acute load (last 7 days) divided by chronic load (last 28 days). Values between 0.8 and 1.3 are considered optimal. |
| CTL | Chronic Training Load, also called Fitness. The 42-day exponential weighted moving average of daily sRPE load. |
| ATL | Acute Training Load, also called Fatigue. The 7-day exponential weighted moving average of daily load. |
| TSB | Training Stress Balance, also called Form. CTL minus ATL. Positive values indicate the player is fresh. |
| Monotony | Weekly mean load divided by weekly standard deviation. Values above 2.0 suggest repetitive training. |
| Strain | Weekly mean load multiplied by monotony. High values flag both high volume and high repetitiveness at the same time. |
| Wellness Composite | Average of five daily self-report scores: sleep quality, inverted fatigue, inverted soreness, mood, and inverted stress. Higher is better. Scale of 1 to 10. |
| Availability | Percentage of scheduled sessions a player attended. |

---

## 6. Analytics Methods Explained

### Acute:Chronic Workload Ratio (ACWR)

ACWR divides a player's recent training load (the last seven days) by their background load (a rolling 28-day average). The idea is that a sudden spike relative to what the player is used to raises injury risk.

Risk zones:
- Below 0.8: under-training
- 0.8 to 1.3: optimal
- 1.3 to 1.5: caution
- Above 1.5: high risk

Source: Gabbett, T. J. (2016). The training-injury prevention paradox. *British Journal of Sports Medicine*, 50(5), 273-280.

### Performance Management Chart (PMC)

The PMC tracks three values over time. CTL (Fitness) rises slowly when a player trains consistently over many weeks. ATL (Fatigue) rises quickly in response to recent hard work and drops quickly with rest. TSB (Form) is the difference between the two.

A player with positive TSB is fresh and ready to perform. A player with very negative TSB is carrying heavy fatigue. The goal is to peak TSB before important matches.

CTL is a 42-day exponential weighted moving average of daily load. ATL is a 7-day exponential weighted moving average.

Source: Banister, E. W. (1991). Modelling elite athletic performance. In H. Green et al. (Eds.), *Physiological Testing of Elite Athletes*. Human Kinetics.

### Training Monotony and Strain

Monotony measures how consistent the training load is from day to day within a week. If a player trains at the same intensity every single day, their standard deviation is low and monotony is high. Research shows high monotony is linked to higher illness and injury rates even when the total load is not extreme.

Strain = weekly mean x monotony. It captures the combined effect of volume and repetitiveness.

Source: Foster, C. (1998). Monitoring training in athletes with reference to overtraining syndrome. *Medicine and Science in Sports and Exercise*, 30(7), 1164-1168.

### K-Means Clustering

K-means groups players into clusters based on their average match performance across nine metrics: distance, HSR, sprint count, passes, shots, tackles won, dribbles won, key passes, and pressures.

The algorithm assigns each player to the cluster whose centre is closest (by Euclidean distance in the scaled feature space). The cluster centres shift until they no longer change. The result is a set of player archetypes based on what they actually do on the pitch, not just their listed position.

PCA (Principal Component Analysis) reduces the nine metrics to two numbers so the clusters can be plotted on a scatter chart.

### Expected Goals (xG)

xG estimates how likely a shot is to result in a goal, based on where it was taken. A shot from close range, directly in front of goal, has a high xG. A shot from the corner of the penalty area has a low xG.

This tool uses a logistic regression formula calibrated on shot distance and angle to goal:

```
xG = 1 / (1 + exp(0.2 + 0.06 x distance - 2.5 x angle))
```

Where distance is measured in metres from the goal centre and angle is in radians. The formula is a simplification of published xG models but produces realistic values across the pitch.

Source: Rathke, A. (2017). An examination of expected goals and shot quality. *Journal of Human Sport and Exercise*, 12(2).

### Random Forest Injury Risk Model

A Random Forest classifier (150 decision trees) is trained on synthetic data that mirrors known injury risk relationships. The training data was generated using the domain-knowledge relationships between load metrics and injury probability.

The model takes seven inputs: ACWR, player age, training monotony, strain, days since last rest, wellness composite, and the last seven days of sRPE. It outputs a probability between 0% and 100%.

The most important features are ACWR (36%), strain (20%), and monotony (16%). These match the findings in sports science literature.

### Z-Score Benchmarking

A Z-score shows how far a player's average metric is from the squad mean, measured in standard deviations. A Z-score of +1.0 means the player is one standard deviation above average. A score of -1.5 means they are well below average.

Z-scores are useful because they put metrics on the same scale. You can compare goals (a count metric) and pass accuracy (a percentage) in the same table without the numbers being misleading.

### Percentile Ranking

Percentile rank shows where a player sits within the squad distribution for a given metric. A player at the 80th percentile for distance covered means 80% of squad members cover less distance on average. This is more intuitive than a Z-score for stakeholders who are not familiar with statistics.

---

## 7. Data Dictionary

### Training Sessions Table

| Column | Type | Description |
|---|---|---|
| player_id | integer | Unique player identifier |
| player_name | string | Player full name |
| position | string | Playing position |
| date | date | Session date |
| session_type | string | MD (match day), MD+1, MD-1, MD-2, MD-3, GYM |
| duration_min | integer | Session length in minutes |
| distance_m | integer | Total distance in metres |
| hsr_m | integer | High-speed running distance above 19.8 km/h |
| sprint_m | integer | Sprint distance above 25.2 km/h |
| sprint_count | integer | Number of sprint efforts |
| accel_count | integer | Acceleration efforts above 2.5 m/s squared |
| decel_count | integer | Deceleration efforts below -2.5 m/s squared |
| max_speed_kmh | float | Peak speed recorded |
| player_load | float | Composite physical load in arbitrary units |
| hml_m | integer | High metabolic load distance |
| rpe | float | Rating of Perceived Exertion (1 to 10) |
| srpe | float | Session RPE: RPE multiplied by duration |
| work_rate | float | Distance divided by duration in metres per minute |

### Match Player Table

| Column | Type | Description |
|---|---|---|
| match_id | integer | Match identifier |
| player_id | integer | Player identifier |
| minutes_played | integer | Minutes on the pitch |
| distance_m | integer | GPS distance in match |
| hsr_m | integer | HSR distance in match |
| passes | integer | Total pass attempts |
| pass_completion | float | Pass success rate (0 to 1) |
| progressive_passes | integer | Forward passes advancing 10+ metres toward goal |
| key_passes | integer | Passes leading directly to a shot |
| shots | integer | Total shots taken |
| goals | integer | Goals scored |
| assists | integer | Goal assists |
| xg | float | Expected goals from all shots |
| xa | float | Expected assists |
| dribbles_attempted | integer | Take-ons attempted |
| dribbles_won | integer | Successful take-ons |
| touches_in_box | integer | Penalty area touches |
| tackles_attempted | integer | Tackles made |
| tackles_won | integer | Tackles that won possession |
| interceptions | integer | Interceptions made |
| aerial_duels_attempted | integer | Aerial contests |
| aerial_duels_won | integer | Aerial contests won |
| pressures | integer | Pressing actions made |
| pressures_won | integer | Pressures that won the ball |
| saves | integer | Saves made (goalkeepers) |
| match_rating | float | Overall match rating (4.5 to 9.5) |

### Wellness Table

| Column | Type | Description |
|---|---|---|
| player_id | integer | Player identifier |
| date | date | Date of wellness check-in |
| sleep_score | float | Self-reported sleep quality (1 to 10) |
| fatigue_score | float | Self-reported fatigue (1 to 10, higher = more fatigued) |
| soreness_score | float | Self-reported muscle soreness (1 to 10) |
| mood_score | float | Self-reported mood (1 to 10) |
| stress_score | float | Self-reported stress (1 to 10) |
| wellness_composite | float | Composite readiness score (1 to 10, higher = better) |

### Matches Table

| Column | Type | Description |
|---|---|---|
| match_id | integer | Unique match identifier |
| date | date | Match date |
| opponent | string | Opposing team name |
| home_away | string | Home or Away |
| goals_for | integer | Goals scored |
| goals_against | integer | Goals conceded |
| result | string | Win, Draw, or Loss |
| possession_pct | float | Ball possession percentage |
| ppda | float | Passes allowed per defensive action |

### Shot Events Table

| Column | Type | Description |
|---|---|---|
| match_id | integer | Match identifier |
| player_id | integer | Player who took the shot |
| minute | integer | Minute of the shot |
| x | float | Pitch x-coordinate (0 to 105 metres) |
| y | float | Pitch y-coordinate (0 to 68 metres) |
| xg | float | Expected goals value for this shot |
| on_target | boolean | Whether the shot was on target |
| goal | boolean | Whether the shot resulted in a goal |

---

## 8. Uploading Your Own Data

Go to the Home page and select "Upload CSV" from the sidebar. Upload a CSV file that matches the training sessions table format above.

The most important columns are: `player_id`, `player_name`, `position`, `date`, `distance_m`, `srpe`, and `session_type`. The tool will use whatever columns it finds and skip charts that depend on missing columns.

If you have a Kaggle dataset, check whether the column names match the ones above. If they do not, you will need to rename the columns in your CSV before uploading, or ask the team to add a column mapper for your specific dataset format.

Match data and wellness data currently use the built-in synthetic dataset. A future update will add upload support for those tables too.

---

## 9. Configurable Settings

Every page has its own sidebar controls. These are the main ones:

| Page | Setting | What it changes |
|---|---|---|
| Player Performance | Player dropdown | Switches all charts to the selected player |
| Player Performance | Date range | Filters training sessions by date |
| Player Performance | Trend window | Number of matches used in the rolling average |
| Team Analytics | Number of clusters | How many K-means groups to create |
| Team Analytics | Z-score metrics | Which columns appear in the benchmarking table |
| Team Analytics | Top performer metric | What metric to rank players by |
| Injury Monitor | Player dropdown | Switches individual ACWR and PMC charts |
| Injury Monitor | Acute window | Days used for the acute load calculation (default 7) |
| Injury Monitor | Chronic window | Days used for the chronic load calculation (default 28) |
| Match Analysis | Match dropdown | Switches all charts to the selected match |
| Match Analysis | Position filter | Filters the shot map by player position |
| Player Comparison | Player multi-select | Up to 4 players to compare across all tabs |

---

## 10. Group Member Contribution Statement

| Member | Primary Contribution |
|---|---|
| Member 1 | Data generation module, training load pipeline, session type profiles |
| Member 2 | Injury risk module: ACWR, PMC, monotony and strain calculations |
| Member 3 | ML risk prediction model, wellness data generation and analysis |
| Member 4 | Match analysis module: shot map, xG model, pressing stats |
| Member 5 | Player performance module, team analytics, clustering, deployment |

All members contributed to the overall design, testing, and documentation. The workload was reviewed and agreed upon by the group before submission.

---

*MIS41500 Sports and Performance Analytics — Group Assessment Submission*
