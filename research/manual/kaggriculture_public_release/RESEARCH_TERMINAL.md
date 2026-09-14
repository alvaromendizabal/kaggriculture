# Equivalent terminal execution for the two outcome rounds

Notebook execution is recommended because it saves the full explanatory narrative
and inline plots. These commands are an alternative for tests/features/experiments,
not something to run again after the notebook has already completed them.

```bash
cd /home/sagemaker-user/kaggriculture_public_release/research
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home()/'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" review_and_pair.py verify --round 21 && \
"$PYTHON_BIN" review_and_pair.py tests --round 21 && \
"$PYTHON_BIN" review_and_pair.py analyze --round 21 && \
"$PYTHON_BIN" review_and_pair.py pair --round 21
```

Stop on an exception. A normal reported negative endpoint is preserved, not retried.
The independent second family can run after normal completion:

```bash
"$PYTHON_BIN" review_and_pair.py verify --round 22 && \
"$PYTHON_BIN" review_and_pair.py tests --round 22 && \
"$PYTHON_BIN" review_and_pair.py analyze --round 22 && \
"$PYTHON_BIN" review_and_pair.py pair --round 22
```

For plotted evidence after terminal execution, open each notebook and run its setup,
read-only outcome-read, plot-display and HTML-export cells, not the test or pair
cells again. Save and reopen. The usual notebook path is simpler.

Do not start additional blocks. Do not combine the two interventions. Return the
bounded outcomes and their negative findings as well as any promising result.
