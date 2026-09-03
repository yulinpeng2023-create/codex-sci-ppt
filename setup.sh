#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" plugins/sci-ppt/skills/sci-ppt/scripts/doctor.py
echo "Sci-PPT installed successfully."
