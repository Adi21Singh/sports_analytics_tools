#!/usr/bin/env bash
# Run the Sports Analytics Platform.
# Usage: bash run.sh
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Prefer venv/ (created by install.sh) then fall back to .venv/ (uv dev env)
if [ -d "venv" ]; then
    PY="venv/bin/python3"
    ST="venv/bin/streamlit"
elif [ -d ".venv" ]; then
    PY=".venv/bin/python3"
    ST=".venv/bin/streamlit"
else
    echo ""
    echo "  No virtual environment found."
    echo "  Run setup first:  bash install.sh"
    echo ""
    exit 1
fi

echo ""
echo "  Starting Sports Analytics Platform..."
echo "  Opening at http://localhost:8501"
echo ""
"$ST" run app.py \
  --server.port=8501 \
  --browser.gatherUsageStats=false
