#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$PROJECT_DIR/.venv"
  "$PYTHON_BIN" -m pip install -r "$PROJECT_DIR/requirements.txt"
fi

cd "$PROJECT_DIR"
"$PYTHON_BIN" -m unittest discover -s tests -v
"$PYTHON_BIN" run_project.py
"$PYTHON_BIN" scripts/build_report.py
"$PYTHON_BIN" scripts/build_presentation_pdf.py

echo "Complete: see $PROJECT_DIR/deliverables and $PROJECT_DIR/outputs"
