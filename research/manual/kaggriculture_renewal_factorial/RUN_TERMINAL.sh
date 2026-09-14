#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path.home()/'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_factorial.py screen
"$PYTHON_BIN" run_factorial.py pilot
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
from visualize import export_dashboard
print(export_dashboard(Path.cwd()))
PY
"$PYTHON_BIN" run_factorial.py bundle
