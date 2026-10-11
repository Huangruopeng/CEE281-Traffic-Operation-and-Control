#!/usr/bin/env bash
# Intermediate 1 in one command: environment (created if needed) -> unit tests -> minimum case.
# Set PYTHON=/path/to/python to use an existing environment instead of .venv.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON:-$PROJECT_DIR/.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$PROJECT_DIR/.venv"
  "$PROJECT_DIR/.venv/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
  PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
fi

cd "$PROJECT_DIR"
"$PYTHON_BIN" -m unittest discover -s tests
"$PYTHON_BIN" run_int1.py
echo "Intermediate 1 outputs: $PROJECT_DIR/outputs/int1"
