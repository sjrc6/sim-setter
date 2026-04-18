#!/usr/bin/env bash
set -euo pipefail

name="${1:-SimSetter}"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --name "$name" run_gui.py

echo "Built dist/$name"
