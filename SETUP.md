# FC Analytics United - Setup Guide

MIS41500 Sports & Performance Analytics | Group Assessment

---

## Requirements

- Python 3.11 or later - https://www.python.org/downloads/
- Internet connection (StatsBomb match data is downloaded on first use)
- Terminal / Command Prompt

Check your Python version:
```
python3 --version
```

---

## Quick Start (Mac / Linux)

**Step 1 - Install dependencies (run once):**
```bash
bash install.sh
```

**Step 2 - Start the app:**
```bash
bash run.sh
```

The app opens automatically at http://localhost:8501

---

## Quick Start (Windows)

If you do not have `bash`, run the following in Command Prompt or PowerShell:

```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## What the app contains

| Page | What it shows |
|---|---|
| Dashboard | Season overview, squad fitness, top scorers |
| Player Performance | Physical training metrics, technical match stats, wellness |
| Player Comparison | Side-by-side radar and percentile comparison of any two players |
| Team Analytics | K-means clustering, Z-score benchmarking, season trends |
| Injury & Load Monitor | ACWR, PMC, monotony/strain, ML risk prediction |
| Match Analysis | Shot map, xG timeline, press analysis (StatsBomb data) |
| Press Intelligence | PPDA windows, momentum index, substitution profiles (StatsBomb data) |

---

## First-run notes

**Dashboard, Player Performance, Player Comparison, Team Analytics, Injury Monitor**
Load instantly. They use the bundled `players_data-2025_2026.csv` file (FBref 2025/26 data included in the repo).

**Match Analysis and Press Intelligence**
These pages use StatsBomb open event data (La Liga 2015/16), which is downloaded from StatsBomb's public GitHub repository the first time each match is selected. This requires an internet connection.

- The match list loads in a few seconds on first open.
- Individual match events download the first time you select that match (~2-5 seconds each). After that they are cached locally and load instantly.
- The **Substitution Profiles** tab (inside Press Intelligence) processes all locally cached matches the first time it is opened. This may take 30-60 seconds on the first run. After that it is instant.

No StatsBomb account or credentials are required. All data accessed is free open data.

---

## Troubleshooting

**"command not found: python3"**
Install Python from https://www.python.org/downloads/ and make sure it is on your PATH.

**"ModuleNotFoundError"**
Run `bash install.sh` again to ensure all dependencies are installed.

**Port already in use**
Another app is using port 8501. Stop it, or run:
```bash
venv/bin/streamlit run app.py --server.port=8502
```

**App opens but Match Analysis / Press Intelligence show errors**
Check your internet connection. StatsBomb data is fetched on first use.

**Slow on first load of Substitution Profiles tab**
Expected behaviour on a fresh install - it is processing match event files for the first time. Wait 30-60 seconds. Subsequent loads are instant.

---

## Stopping the app

Press `Ctrl + C` in the terminal.
