# Notebook 11 — one feature screen and one bounded endpoint pilot

Use the existing `kaggriculture-dev` space and verified manual kernel. Do not wipe, clone, reinstall, redownload data, or rerun notebooks 05–10. This package does not contact AWS APIs, S3, GitHub or Kaggle. You manually run local code in your existing space. Stop compute after downloading results; notebook timeouts do not stop AWS billing.

## 1. Open AWS and upload

AWS console → SageMaker AI → US West (Oregon), `us-west-2` → Studio → `QuickSetupDomain-20260902T115323` → profile `default-20260902T115323` → JupyterLab → `kaggriculture-dev`.

Open the existing space. If stopped, keep the working image/storage configuration and leave old automated research lifecycle scripts unselected. No GPU or new instance type is needed.

Upload `kaggriculture_route_opportunity.zip` to `/home/sagemaker-user` using JupyterLab's upload arrow. Open File → New → Terminal.

## 2. Extract once

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
root=Path('/home/sagemaker-user').resolve()
target=root/'kaggriculture_route_opportunity'
if target.exists():
    raise SystemExit('Folder already exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(root/'kaggriculture_route_opportunity.zip') as z:
    for item in z.infolist():
        p=(root/item.filename).resolve()
        if not p.is_relative_to(target):
            raise SystemExit('Unsafe archive path: '+item.filename)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('Archive symlink rejected')
    z.extractall(root)
print('OPEN:',target/'11_route_opportunity_feature_ablation.ipynb')
PY
```

## 3. Run notebook 11

Open `/home/sagemaker-user/kaggriculture_route_opportunity/11_route_opportunity_feature_ablation.ipynb`.

Kernel → Change Kernel → **Kaggriculture Manual (verified source)**. Run → **Run All Cells**.

The notebook checks the prior result without repeating it. Stage A evaluates 69 saved coordinated states, checks the original route menus and reference actions, and saves the feature screen. Stage B only runs when a first action actually changed. It tests one no-change control and one activation-selected primary pair: at most 92 research interpreter transitions, no new full season.

Stage A cap: 90 seconds. Stage B cap: 120 seconds. Each worker receives up to two seconds to terminate before forced shutdown. Callback gate: 500 ms. Ten-second UTC heartbeats. These are safety limits, not runtime estimates. The outer notebook has separate emergency deadlines for cleanup.

Expected stage markers:

```text
PREFLIGHT_PASSED
SCREEN_EPISODE_SAVED
ROUTE_OPPORTUNITY_SCREEN_COMPLETE
BRANCH_CHECKPOINT_SAVED     # only when screen activates
PAIR_COMPLETE              # only when pilot runs
ROUTE_OPPORTUNITY_PILOT_COMPLETE
NOTEBOOK11_COMPLETE
```

Matching completed checkpoints or stages may print `...REUSED`. An unresolved FAILED/RUNNING/interrupted status is deliberately not retried unchanged. If a cell errors, stop and bundle diagnostics. Do not delete status/checkpoint files or increase timeouts.

Decisions:

- `STOP_NO_ACTION_ACTIVATION`: no saved-state first action changed, so the pilot is skipped.
- `STOP_NEGATIVE_ENDPOINT`: at least one of own cash, coin margin or local match outcome declined in the primary pair.
- `STOP_NO_TRAJECTORY_ACTIVATION`: the treatment had no first-action effect in its continuously advanced branch.
- `STOP_NO_ENDPOINT_BENEFIT`: changed actions did not improve the primary endpoint.
- `PROMISING_SINGLE_DEVELOPMENT_PAIR_NOT_VALIDATED`: a small exploratory benefit; not a leaderboard gain, independent validation or authorization to scale automatically.

Eight Plotly views cover the prior endpoint result, action activation, static utility, opportunity cost, feature activation, callback timing, paired endpoint effects, and linked cash trajectories. Static utility and activation are not actual cash or predictive importance.

## 4. Save and bundle, including after an error

Save the notebook with Ctrl+S. Run:

```bash
cd /home/sagemaker-user/kaggriculture_route_opportunity
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path.home()/'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_routes.py bundle
```

Download `kaggriculture_route_opportunity_results.zip` from that folder and upload it to this chat. Do not return the original input ZIP. The result bundle excludes source raw episodes, credentials, environments and symlinked files. It contains derived feature tables, outcome tables, branch checkpoints, logs and the saved notebook.

## 5. Stop compute

Studio → Running instances → stop the application for `kaggriculture-dev`. Do not delete the space. Closing the browser does not stop the application.

AWS reference: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Terminal alternative

Run this instead of the notebook's execution cells, not in addition to them:

```bash
cd /home/sagemaker-user/kaggriculture_route_opportunity
PYTHON_BIN="$(python3 -c 'import json,pathlib; print(json.loads((pathlib.Path.home()/"kaggriculture_manual_resume/state/runtime.json").read_text())["executable"])')"
"$PYTHON_BIN" run_routes.py screen && "$PYTHON_BIN" run_routes.py pilot
```

Then open notebook 11 and Run All Cells to render the saved results; successful stages are checksum-verified and reused. A failed stage must be diagnosed, not repeatedly restarted.

## Source control

The reviewed GitHub baseline is `7194116dfc92a8663139611233b5a221dad431a4`. This manual package is not yet committed/pushed/merged, and nothing in it performs those operations. Raw/private artifacts and the old research sources remain untouched. Keep this package and download its results. A later reviewed publication can add tested canonical code and executed evidence without uploading private source episodes or claiming unrun tests.
