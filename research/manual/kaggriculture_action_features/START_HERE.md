# Kaggriculture · Round 07

## Run one new notebook, not the historical studies

This package adds terminal action-opportunity features and six Plotly views. It leaves both Git checkouts, raw Kaggle downloads, restored episodes, environment and frozen policies unchanged.

The uploaded `kaggriculture_workforce_milestone(1).zip` was the original input package, not an execution result. Notebook 07 handles this without guessing:

- A verified notebook-06 result is **reused**.
- If notebook 06 has never run, its existing bounded audit is executed **once**.
- A failed, active or interrupted notebook-06 run stops the sequence. Its diagnostics are bundled; it is not retried unchanged.

No notebook-05 setup, clone, reset, package installation or data redownload is required.

## 1. Open your space

Open AWS in a browser tab → SageMaker AI → US West (Oregon), `us-west-2` → Studio → domain `QuickSetupDomain-20260902T115323` → profile `default-20260902T115323` → JupyterLab → `kaggriculture-dev`.

Use the existing working configuration. If stopped, verify that the old automated research lifecycle script is not reattached, then Run space → Open JupyterLab. Starting the space is billable. No GPU is required by this package. Do not delete the space or either repository.

## 2. Upload and extract

Upload `kaggriculture_action_features.zip` into `/home/sagemaker-user` with JupyterLab's upload arrow. File → New → Terminal, then paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
root=Path('/home/sagemaker-user').resolve()
target=root/'kaggriculture_action_features'
if target.exists():
    raise SystemExit('Folder already exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(root/'kaggriculture_action_features.zip') as z:
    for item in z.infolist():
        destination=(root/item.filename).resolve()
        if not destination.is_relative_to(target):
            raise SystemExit('Unsafe archive path: '+item.filename)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('Archive symlink rejected')
    z.extractall(root)
print('OPEN:',target/'07_action_opportunity_features.ipynb')
PY
```

## 3. Run notebook 07

Open `kaggriculture_action_features/07_action_opportunity_features.ipynb`.

Kernel → Change Kernel → **Kaggriculture Manual (verified source)**. Run → Run All Cells.

The cells perform two separately bounded stages. The notebook-06 worker retains its 180-second limit (its wrapper allows startup/shutdown overhead, at most 195 seconds before termination). The new notebook-07 worker has a 180-second limit plus up to two seconds to terminate. These are budgets, not performance promises. Charts and result packaging are local exports, not further game runs. Each long stage prints UTC heartbeats at ten-second intervals and saves successful episode checkpoints.

Expected stage markers:

```text
NOTEBOOK06_GATE_PASSED
PREFLIGHT_PASSED
EPISODE_CHECKPOINTED ... 1/7 through 7/7
ACTION_FEATURE_AUDIT_PASSED
NOTEBOOK07_COMPLETE
```

Reused work may print `EPISODE_REUSED` or `EXISTING_PASS_REUSED` instead of recomputing it.

Expected report limitations:

```text
full_callback_acceptance: NOT_RUN
official_metric_effect_measured: false
feature_value_proven: false
new_complete_games: 0
```

They mean exactly what they say: this milestone builds and audits candidate features, not a stronger validated game-playing agent. The six charts include action-probe changes, cash deadlines, worker/task opportunities, price impact, activation and feature-only latency.

### On any failure

Stop at the first failed cell. Do not reinstall, reset, redownload or change limits. Save the notebook, then run the bundle command below; it includes failure details and the prior-06 diagnostic summaries. If the entire original notebook-06 package is absent, restore that package to its original home-folder location; do not replace an existing package or environment.

The `--resume-after-review` option is intentionally not used in the standard commands. It is only for a diagnosed interruption with matching code/input hashes. It will not ignore incompatible checkpoints.

## 4. Save and bundle the correct results file

Press Ctrl+S in notebook 07. In a terminal:

```bash
cd /home/sagemaker-user/kaggriculture_action_features
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path.home()/'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_next.py bundle
```

Download **`kaggriculture_action_feature_results.zip`** from that folder and upload it back into ChatGPT.

Do **not** upload `kaggriculture_action_features.zip` again: that is the input package. The results ZIP contains the saved notebook, report or failure, checksummed feature/probe exports, derived episode checkpoints, dashboard, UTC logs and notebook-06 diagnostic summaries. Raw episode archives and credentials are excluded.

## 5. Stop compute

Return to Studio → Running instances and stop the JupyterLab application for `kaggriculture-dev`. Do not delete the space. Closing a browser tab does not stop the application.

AWS reference: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Terminal-only execution alternative

This is an alternative to the notebook's execution cells; do not run both simultaneously. Use the same `PYTHON_BIN` block above, then:

```bash
"$PYTHON_BIN" run_next.py ensure06 && \
"$PYTHON_BIN" run_next.py run --seconds 180
```

Open notebook 07 afterward for charts. The passed results are rechecked and reused rather than recomputed. Save it and run `bundle` as above. If the command fails, use `bundle` directly instead of rerunning.

## What the files contain

`opportunity_features.py` is the new feature implementation. `workforce_features.py` is the unchanged observation contract copied from the preceding package, with its origin hash verified. `run_next.py` provides local-only stage supervision, tests, source/data checks, component parity, replay, caches and bundling. `visualize.py` contains six Plotly figures and standalone HTML export. `FEATURE_RESEARCH.md` records mechanisms, assumptions, hypothesis, probe definitions, stopping rules and the remaining research queue. `feature_dictionary.json` documents every numeric output.

The package includes tests and local validation evidence. The main notebook is intentionally unexecuted: an AWS pass must come from your verified runtime, not from synthetic preview data. The separate synthetic preview uses toy unit-test prices and is never promoted into a live receipt.
