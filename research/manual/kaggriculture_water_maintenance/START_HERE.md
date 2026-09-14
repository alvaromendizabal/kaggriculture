# Notebook 12 — crop maintenance feature ablation

Do not wipe the space, clone again, install packages, change instance type, delete
checkpoints, or rerun notebooks 05–11. This package uses the existing verified
manual checkout and private recovered source episodes.

## 1. Open the existing space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio →
QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab →
kaggriculture-dev. Preserve the working image and storage. Keep old automated
research lifecycle scripts unselected. Start the existing app only if stopped.

## 2. Upload and extract

Upload `kaggriculture_water_maintenance.zip` to `/home/sagemaker-user` using
JupyterLab's upload arrow. Open File → New → Terminal. Paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
root = Path('/home/sagemaker-user').resolve()
target = root / 'kaggriculture_water_maintenance'
archive = root / 'kaggriculture_water_maintenance.zip'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        destination = (root / item.filename).resolve()
        if not destination.is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: ' + item.filename)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected: ' + item.filename)
    z.extractall(root)
print('OPEN:', target / '12_water_maintenance_feature_ablation.ipynb')
PY
```

## 3. Open the notebook and run

Open `kaggriculture_water_maintenance/12_water_maintenance_feature_ablation.ipynb`.
Choose Kernel → Change Kernel → **Kaggriculture Manual (verified source)**, then
Run → Run All Cells. No manual code edits are needed.

The first stage checks the package, reviewed notebook-11 result, earlier source
fingerprints, pinned engine, and ten restored objects. It does not rerun earlier
experiments. It then tests plant scenarios against real engine components and
screens saved observations. The second stage runs at most one pair, only after
action activation. It replays old actions for the prefix; this is not a new policy
fit or a from-scratch policy search.

Markers:

```text
PREFLIGHT_PASSED
MECHANICS_PASSED
SCREEN_EPISODE_SAVED
WATER_MAINTENANCE_SCREEN_COMPLETE
PREFIX_REPLAY              # only if the screen activates
SUFFIX_PROGRESS
BRANCH_CHECKPOINT_SAVED
WATER_MAINTENANCE_PILOT_COMPLETE
NOTEBOOK12_COMPLETE
```

Screen cap **120 s**, pilot cap **180 s**, measured callback cap **500 ms**;
up to two extra seconds for termination. Notebook emergency deadlines add startup
and shutdown overhead. These are work limits, not estimated runtimes or AWS
shutdown timers. Heartbeats appear every ten seconds.

Read the decision:

- `STOP_NO_ACTION_ACTIVATION`: no qualifying changed action; no simulation pilot.
- `STOP_NEGATIVE_ENDPOINT`: cash, margin, or match result decreased.
- `STOP_NO_TRAJECTORY_ACTIVATION` / `STOP_NO_ENDPOINT_BENEFIT`: no useful effect.
- `PROMISING_SINGLE_DEVELOPMENT_PAIR_REQUIRES_VALIDATION`: exploratory only.

A null-fork mismatch, source discrepancy, altered intervention scope, or timing
violation is a failure, not an outcome. Stop on error and bundle. Do not retry an
unchanged failure, weaken assertions, or increase caps. Completed states and
branches are preserved and hash-checked. A completed stage can be reused; a failed
or interrupted stage requires diagnosis before another attempt.

## 4. Save and return the results

Press Ctrl+S. Open a JupyterLab terminal and paste:

```bash
cd /home/sagemaker-user/kaggriculture_water_maintenance
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_maintenance.py bundle
```

Download **kaggriculture_water_maintenance_results.zip**, not the input ZIP.
Bundling works after a failure too. It includes the saved notebook, report,
feature tables, derived branch checkpoints and logs. It excludes raw source
episodes, credentials, and environments. The bundle itself is a persistent local
copy; it is not a confirmed S3 backup until separately uploaded and verified.

## 5. Stop compute

Studio → Running instances → kaggriculture-dev → Stop. Do not delete the space.
Closing the tab does not stop compute; experiment timeouts do not stop AWS.
Official instructions: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Terminal-only execution alternative

Use the notebook path above for the charts. For the same stages in a terminal,
use the verified interpreter and run one command at a time:

```bash
cd /home/sagemaker-user/kaggriculture_water_maintenance
# Set PYTHON_BIN with the receipt command in step 4 first.
"$PYTHON_BIN" run_maintenance.py screen
# Proceed only after screen completion; pilot automatically skips nonactivation.
"$PYTHON_BIN" run_maintenance.py pilot
```

Do not run notebook and terminal stages simultaneously. The stage locks reject a
second launch. Reopening a completed notebook reuses the verified stage outputs.
No code pushes, cloud changes, submissions, or package installations occur.
