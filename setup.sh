#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/doctor.py
echo "Codex Sci-PPT installed successfully."
