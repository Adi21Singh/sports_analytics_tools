#!/usr/bin/env bash
# Run the Sports Analytics Tool in the project virtual environment.
# Usage: bash run.sh
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
fi

echo "Starting Sports Analytics Tool..."
venv/bin/streamlit run app.py \
  --server.port=8501 \
  --browser.gatherUsageStats=false
