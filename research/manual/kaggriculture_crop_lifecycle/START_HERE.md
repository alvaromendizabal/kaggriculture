# Run notebook 15: crop lifecycle feature ablation

## 1. Open the existing space
AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio → QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab → kaggriculture-dev.
Use the existing working image/storage and kernel. Do not reattach an old automatic-research lifecycle script. Do not wipe, clone, install packages, redownload raw data, or rerun notebooks 05–14.

## 2. Upload and extract
Upload `kaggriculture_crop_lifecycle.zip` to `/home/sagemaker-user` using the file browser's upload arrow. Open File → New → Terminal:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
home = Path('/home/sagemaker-user').resolve()
target = home / 'kaggriculture_crop_lifecycle'
if target.exists():
    raise SystemExit('Folder already exists. Reopen its notebook; do not overwrite.')
with zipfile.ZipFile(home / 'kaggriculture_crop_lifecycle.zip') as z:
    for m in z.infolist():
        if not (home / m.filename).resolve().is_relative_to(target):
            raise SystemExit('Unsafe ZIP path')
        if stat.S_ISLNK(m.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected')
    z.extractall(home)
print(target / '15_crop_lifecycle_feature_ablation.ipynb')
PY
```

## 3. Run the notebook
Open `kaggriculture_crop_lifecycle/15_crop_lifecycle_feature_ablation.ipynb`. Select Kernel → Change Kernel → Kaggriculture Manual (verified source), restart the kernel, then Run → Run All Cells.

The notebook re-verifies existing evidence, without repeating prior experiments. Screen: 372 observations, 120-second worker cap. Only after action activation: one three-arm block, 180-second cap. Up to two additional seconds permit worker cleanup. The notebook has a separate emergency deadline. A 500 ms callback gate saves violating measurements before stopping.

Expected: PREFLIGHT_PASSED; MECHANICS_PASSED; SCREEN_EPISODE_SAVED; CROP_LIFECYCLE_SCREEN_COMPLETE; optionally BRANCH_CHECKPOINT_SAVED; CROP_LIFECYCLE_PILOT_COMPLETE; NOTEBOOK15_COMPLETE. Matching checkpoints show reuse messages.

STOP_NO_ACTION_ACTIVATION means continuations were skipped. For a completed block, inspect each contrast and renew-minus-retire. Completion is not a performance claim. No policy is promoted automatically.

If a cell fails, stop and bundle. Do not change limits, reset Git, remove checkpoints, reinstall or retry unchanged. Completed branches are preserved. Failed/active stages are not silently restarted.

## 4. Save and bundle
Press Ctrl+S, then run in the terminal:

```bash
cd /home/sagemaker-user/kaggriculture_crop_lifecycle
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_lifecycle.py bundle
```

Download `kaggriculture_crop_lifecycle_results.zip`, not the original input ZIP. Bundling also works after failure; it includes saved notebook, measurements, logs and derived checkpoints, not raw source episodes or credentials.

## 5. Stop compute
Studio → Running instances → kaggriculture-dev → stop its application. Do not delete the space. Browser closure and notebook deadlines do not stop AWS billing. Files persist when the app stops. AWS reference: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html .

## Terminal alternative
After defining PYTHON_BIN above, run `"$PYTHON_BIN" run_lifecycle.py screen && "$PYTHON_BIN" run_lifecycle.py pilot` from this folder instead of the notebook experiment cells. Opening the notebook later reuses verified stages for plots. Do not launch terminal and notebook experiments concurrently.

## GitHub and original files
Main was checked at 7194116dfc92a8663139611233b5a221dad431a4. This package is not committed, pushed or merged. It modifies no repository source, AWS resource or submission. Raw data and prior checkpoints remain intact. No git pull or reset is needed.
