# Notebook 10: sale timing and the final sale opportunity

Do not rerun notebooks 05–09, wipe the space, clone, pull, reinstall packages, or redownload data. Notebook 09's corrected run completed and returned a negative result; this is a new narrowly changed hypothesis, not another retry.

## 1. Open the same space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio → QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab → kaggriculture-dev.

Keep the same working image/storage and leave old automated lifecycle scripts unselected. Stop any unrelated experiments. No GPU or new instance type is required. Opening a stopped application starts billable compute.

## 2. Upload the entire input ZIP to your home directory

Download `kaggriculture_sale_timing.zip` from ChatGPT. In JupyterLab upload it into `/home/sagemaker-user`, not inside a repository. Open File → New → Terminal, and paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
root = Path('/home/sagemaker-user').resolve()
target = root / 'kaggriculture_sale_timing'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(root / 'kaggriculture_sale_timing.zip') as z:
    for item in z.infolist():
        dest = (root / item.filename).resolve()
        if not dest.is_relative_to(target) or stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('Unsafe ZIP entry: ' + item.filename)
    z.extractall(root)
print('OPEN:', target / '10_sale_timing_feature_ablation.ipynb')
PY
```

On restart use the existing extracted folder; never overwrite results by extracting again.

## 3. Run the notebook

Open `/home/sagemaker-user/kaggriculture_sale_timing/10_sale_timing_feature_ablation.ipynb`.

Kernel → Change Kernel → **Kaggriculture Manual (verified source)**. Then Run → Run All Cells.

No installation or code editing is required. The notebook verifies prior receipts and dependencies in place, not rerunning old studies. It produces a diagnostic ledger and seven Plotly figures, then saves results in this new package's `outputs` directory.

Expect `DIAGNOSIS_RECONCILED`, `PREFLIGHT_PASSED`, `MECHANICS_PASSED`, up to seven `EPISODE_CHECKPOINT_SAVED` messages, `SALE_TIMING_EXPERIMENT_COMPLETE`, and `NOTEBOOK10_COMPLETE`. A checkpoint reuse message is normal.

The experiment returns the unchanged control action before step 718 and only permits aligned final-sale quantities at step 718. It recomputes at most 154 earlier terminal-day policy callbacks to prove action equality; it does not rerun simulator seasons. It performs at most 14 research interpreter transitions and 38 separate mechanics transitions. There are at most three primary paired sources plus four negative controls.

Worker limit: 180 seconds, with two seconds for termination. Callback limit: 500 ms. Ten-second heartbeats and hash-verified per-episode checkpoints are included. These limits are not runtime estimates and do not shut down your AWS application.

### Interpretation

- `STOP_NEGATIVE_FINAL_EFFECT`: at least one primary endpoint lost coins, margin or match outcome. Do not scale up.
- `STOP_NO_ACTIVATION`: no primary final market action changed.
- `STOP_NO_FINAL_BENEFIT`: action changed but no primary endpoint improved.
- `PROMISING_DEVELOPMENT_ONLY_FRESH_VALIDATION_REQUIRED`: an exploratory benefit, not validation, not a winning agent, and not a leaderboard rating.

If a cell fails, stop there and bundle. Do not increase caps or retry unchanged. Valid checkpoints remain preserved for reviewed recovery; the script does not automatically replay a failed attempt. Completed successful runs are reused after output/dependency verification.

### Terminal alternative (instead of running the notebook's experiment cell)

```bash
cd /home/sagemaker-user/kaggriculture_sale_timing
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home()/'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_timing.py run
```

After the terminal run, open and run the notebook; its experiment cell will reuse the completed report instead of repeating it. A failed attempt is not rerun.

## 4. Save and return the RESULTS ZIP

Press Ctrl+S to save the notebook first. Then run:

```bash
cd /home/sagemaker-user/kaggriculture_sale_timing
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home()/'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_timing.py bundle
```

Download **`kaggriculture_sale_timing_results.zip`** from this directory and upload it in ChatGPT. This is different from the input ZIP. Bundling works after a failure as well. It includes diagnostics, derived tables, checkpoints and your saved notebook, not raw episodes or credentials.

## 5. Stop compute

Studio → Running instances → stop the JupyterLab application for `kaggriculture-dev`. Do not delete the space. Closing the browser does not stop compute; the worker cap does not shut down AWS.

Official shutdown guidance: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Boundaries

The live notebook is unexecuted at delivery. Local tests include actual returned ledger checks plus explicitly synthetic policy/transition tests; they are not acceptance of your installed official engine or private episodes. Live mechanics, action parity, terminal reward and callback checks are mandatory.

GitHub main was read-only verified at `7194116dfc92a8663139611233b5a221dad431a4`. This package is not yet committed/pushed/merged, and it intentionally makes no Git writes. Earlier notebooks and results are preserved. The old three-hired-hand limit in the action callback remains a known submission-readiness gap.
