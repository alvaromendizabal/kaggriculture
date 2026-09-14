# Kaggriculture — Notebook 08: post-action cash realization

## One bounded milestone, no new setup

Your returned notebook-07 results passed. This package does not reinstall anything, fetch GitHub, reset either repository, download Kaggle data, call AWS APIs, or start full games. It runs entirely in your existing JupyterLab space when you choose Run All.

The current reviewed GitHub baseline is `7194116dfc92a8663139611233b5a221dad431a4` (PR #15). Notebooks 06, 07, and this new package are separate manual artifacts, not merged additions to that baseline.

**Purpose:** determine whether the coordinated agent's sell orders under-cover the inventory produced by the farm actions it actually emits. The frozen source swaps farm actions but retains sell orders calculated for the base planner's different actions. This is a source-supported hypothesis, NOT a claim that cash is already known to be lost on your seven episodes.

## 1. Open the existing space

In AWS: SageMaker AI → US West (Oregon), `us-west-2` → Studio → domain `QuickSetupDomain-20260902T115323` → profile `default-20260902T115323` → JupyterLab → `kaggriculture-dev`.

Open the current application, or start the stopped application with the working image/storage settings. Do not reattach an old automatic research lifecycle script. Do not delete, reset, or reclone anything. No GPU is required.

## 2. Upload and extract

Upload `kaggriculture_cash_realization.zip` in `/home/sagemaker-user`, using JupyterLab's upload-arrow button. Open File → New → Terminal, and paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
root = Path('/home/sagemaker-user').resolve()
target = root / 'kaggriculture_cash_realization'
archive = root / 'kaggriculture_cash_realization.zip'
if target.exists():
    raise SystemExit('Folder already exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        path = (root / item.filename).resolve()
        if not path.is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: ' + item.filename)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected')
    z.extractall(root)
print('OPEN:', target / '08_post_action_cash_features.ipynb')
PY
```

## 3. Run notebook 08

Open `kaggriculture_cash_realization/08_post_action_cash_features.ipynb`.

Kernel → Change Kernel → **Kaggriculture Manual (verified source)**.

Run → **Run All Cells**.

The notebook verifies notebook 07 in place. It does not rerun 05, 06, or 07. It rechecks the existing source, kernel, pinned engine, and ten recovered objects.

The new worker has a **180-second maximum** (plus up to two seconds for termination). The parent notebook wrapper adds a separate emergency deadline. These are caps, not runtime estimates. UTC heartbeats appear at ten-second intervals. Work is checkpointed by episode.

Expected markers:

```text
PREFLIGHT_PASSED
MECHANICS_PASSED
EPISODE_CHECKPOINT_SAVED ... 1/7 through 7/7
POST_ACTION_CASH_AUDIT_PASSED
NOTEBOOK08_COMPLETE
```

The complete terminal callback has a **500 ms maximum-observation gate**, not an average-latency gate. Actual violating samples and action payloads are saved before stopping. This gate covers the new callback on the replayed final-day states, not the original callback, arbitrary workforce sizes, all future states, or Kaggle hosting.

### Interpret the decision, not just a green status

- `STOP_NO_ACTIVATION`: the representation/integration worked, but sell orders did not change here. Do not launch a larger run of this family.
- `REVIEW_NEGATIVE_ONE_STEP_STATES`: inspect the saved cases before proceeding.
- `ACTIVATED_REQUIRES_PAIRED_CONTINUATION`: the intervention activated without negative own-cash effects in these one-step branches. That is NOT a full-game improvement or promotion decision.

On any exception, stop at that cell and proceed to the bundle step. Do not reinstall, reset, increase limits, weaken assertions, or repeatedly retry unchanged. A previous interrupted attempt requires a diagnosed cause before the explicit recovery flag is used. Never run the terminal and notebook execution routes concurrently.

### Terminal execution alternative (instead of Run All for the compute cell)

```bash
cd /home/sagemaker-user/kaggriculture_cash_realization
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home()/'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_cash.py run --seconds 180
```

Then open notebook 08 and Run All; it verifies and reuses the completed pass instead of recomputing. The notebook supplies the visual review.

## 4. Save and return the correct results ZIP

Press Ctrl+S in the notebook. In the JupyterLab terminal:

```bash
cd /home/sagemaker-user/kaggriculture_cash_realization
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home()/'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_cash.py bundle
```

Download and return **`kaggriculture_cash_realization_results.zip`**, located inside the `kaggriculture_cash_realization` folder. Do not return the original input ZIP.

The bundle works after a failure. It includes derived feature tables, the separate one-step outcome table, callback checks, episode checkpoints, diagnostics, dashboard and saved notebook. It excludes raw source episode archives and credentials. Latest-callback diagnostics contain chosen actions and a source-observation hash, not the raw private episode.

## 5. Stop compute

Studio → Running instances → stop the JupyterLab application for `kaggriculture-dev`.

Do not delete the space. Closing a browser tab does not stop billable compute. The script's timeout does not stop the AWS application.

## Boundaries of this milestone

There are 158 candidate descriptors (16 per product across nine products, plus 14 aggregate descriptors). They describe post-action sale coverage and conditional immediate cash, not learned feature importance.

Control and treatment use identical route menus, solver objective, tie order, farm actions, fertilizer reserve rule, and hiring rule. Only the state used to compute terminal SELL orders changes. Three nonterminal snapshots per episode provide negative controls. Sequential-source episodes are an additional negative control.

The evaluator makes separate one-step branches from 161 saved states. It uses the recorded rival's action and private state only AFTER our policies produce their outputs. The policies and feature extractor never receive that information. Source interpreter transitions must reproduce the next recorded state (or the final reward at step 718).

**Do not add the 161 cash deltas together and call that a season improvement.** The branches all start from the original saved trajectory. No new complete game, adaptive-opponent evaluation, validation/holdout use, or submission occurs here.

The old callback's three-hired-hands observation boundary is still inherited by this action-equivalent fork. The broader variable-workforce extractor passed separately, but the whole agent is not yet certified for that wider domain. This remains a submission-readiness blocker rather than being silently hidden.
