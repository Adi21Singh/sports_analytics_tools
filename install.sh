#!/usr/bin/env bash
# install.sh — Sports Analytics Platform — first-time setup
# Usage: bash install.sh
set -e

# ── Terminal colours ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${GREEN}✔${NC}  $*"; }
step() { echo -e "${BLUE}▶${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✘${NC}  $*" >&2; exit 1; }

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo ""
echo "  Sports Analytics Platform — Installer"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Python 3.9+ check ────────────────────────────────────────────────────────
step "Checking Python version..."
PY=$(command -v python3 2>/dev/null || command -v python 2>/dev/null \
     || die "Python 3.9+ not found. Install it from https://python.org and re-run.")
"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" \
    || die "Python 3.9+ is required. Found: $("$PY" --version 2>&1)"
info "Python OK ($("$PY" --version))"

# ── Virtual environment ───────────────────────────────────────────────────────
step "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    "$PY" -m venv venv
    info "Virtual environment created."
else
    info "Virtual environment already exists."
fi
source venv/bin/activate

# ── Install Python dependencies ───────────────────────────────────────────────
step "Installing dependencies (this may take a minute on first run)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
info "All dependencies installed."

# ── Check bundled player data ─────────────────────────────────────────────────
step "Checking player data file..."
if [ -f "players_data-2025_2026.csv" ]; then
    info "Player data CSV found ($(wc -l < players_data-2025_2026.csv | tr -d ' ') rows)."
else
    warn "players_data-2025_2026.csv not found."
    echo "     The Dashboard requires this file. It should be included with the repo."
    echo "     If missing, place an FBref player stats CSV in: $DIR/"
fi

# ── Pre-fetch StatsBomb open data (competitions + La Liga match list) ─────────
step "Pre-fetching StatsBomb open data (competitions & La Liga match list)..."
venv/bin/python - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
try:
    from analytics.press_engine import load_sb_competitions, load_sb_season_matches, LA_LIGA_COMPETITION_ID
    comps = load_sb_competitions()
    print(f"   ✔  {len(comps)} competitions loaded and cached.")
    la_liga = comps[comps["competition_name"] == "La Liga"]
    if not la_liga.empty:
        # Cache the most recent La Liga season available
        season_row = la_liga.sort_values("season_id").iloc[-1]
        season_id  = int(season_row["season_id"])
        season_name = str(season_row["season_name"])
        matches = load_sb_season_matches(LA_LIGA_COMPETITION_ID, season_id)
        print(f"   ✔  La Liga {season_name}: {len(matches)} matches cached.")
    else:
        print("   ⚠  La Liga not found — match list will be fetched on first app use.")
except ImportError as e:
    print(f"   ⚠  Could not import press engine: {e}")
except Exception as e:
    print(f"   ⚠  StatsBomb pre-fetch failed: {e}")
    print("      Match Analysis and Press Intelligence pages will fetch data on first use.")
PYEOF

# ── All done ──────────────────────────────────────────────────────────────────
echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Setup complete!"
echo ""
echo "  To start the app:"
echo ""
echo "    bash run.sh"
echo ""
echo "  Or manually:"
echo ""
echo "    source venv/bin/activate && streamlit run app.py"
echo ""
echo "  The app opens at http://localhost:8501"
echo ""
echo "  Pages:"
echo "    Dashboard          — 2025/26 squad overview (uses bundled FBref CSV)"
echo "    Match Analysis     — shot maps, xG timeline (StatsBomb open data)"
echo "    Press Intelligence — PPDA windows, momentum index (StatsBomb open data)"
echo ""
echo "  Note: match event data is downloaded from StatsBomb on first selection"
echo "  and then cached locally in analytics/sb_press_cache/."
echo ""
