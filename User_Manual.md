# Sports Analytics Tool — User Manual

A football analytics tool for analyzing La Liga 2015/16 matches using StatsBomb event data. View detailed match statistics, shot maps, pressing patterns, and team performance metrics.

---

## What You'll See

**Match Analysis** - Shot maps, expected goals (xG) timelines, and defensive action breakdowns for each match

**Press Intelligence** - Pressing patterns, defensive territory, team momentum, and season-long pressing trends with configurable analysis windows

---

## Installation

### What You Need

- **Computer**: Mac, Linux, or Windows
- **Python**: Version 3.11 or later ([download here](https://www.python.org/downloads/))
- **Internet**: Required to download match data on first use

**Check if you have Python:**
Open your terminal or command prompt and type:
```
python3 --version
```

If you see `Python 3.11` or higher, you're good. If not, install Python first.

---

## Quick Start

### Mac & Linux Users

Open the terminal in the project folder and run:

```bash
bash install.sh
bash run.sh
```

The app will open automatically at `http://localhost:8501`

**Next time you want to run it**, just type:
```bash
bash run.sh
```

---

### Windows Users

Open Command Prompt or PowerShell in the project folder and run:

```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

**Next time you want to run it**, just run the last line again:
```cmd
venv\Scripts\streamlit run app.py
```

---

## How to Use

### First Time

When you first open Match Analysis or Press Intelligence, the app will download match data from StatsBomb. This takes 5-10 seconds. After that, data loads instantly.

### Navigating

- Use the menu on the left to switch between **Match Analysis** and **Press Intelligence**
- Select a match from the dropdown to view that match's data
- Hover over charts to see exact values
- Use the sidebar sliders and controls to adjust analysis thresholds and filters

### Match Analysis

- **Shot Map** - See every shot on a football pitch. Bubble size = shot quality (xG)
- **xG Timeline** - Watch how expected goals accumulated throughout the match
- **Press Analysis** - See where teams made defensive tackles, pressures, and interceptions

### Press Intelligence

- **Press Timeline** - Visualize pressing intensity over time for both teams
- **Context Layer** - Possession, success rates, and defensive territory
- **Match Momentum** - Overall match control score
- **Substitution Profiles** - Compare pressing stats between players
- **Opponent History** - See how opponents pressed across their season
- **Threshold Validator** - Technical validation of analysis windows

---

## Stopping the App

Press `Ctrl + C` in the terminal where the app is running.

---

## Troubleshooting

**"Python not found"**  
Install Python 3.11+ from https://www.python.org/downloads/

**"No virtual environment found"**  
Run the install script: `bash install.sh`

**"Port already in use"**  
Another app is using port 8501. To use a different port, run:
```bash
streamlit run app.py --server.port=8502
```

**"ModuleNotFoundError"**  
Close the app and run: `bash install.sh`

**Match data is slow to load**  
This is normal on first run. The app is downloading data from StatsBomb. Wait 5-10 seconds and refresh.

**Something broke**  
Close the app (`Ctrl + C`) and run the install script again:
```bash
bash install.sh
```

---

**For technical details** about analytics methods and formulas, see the README.md file.
