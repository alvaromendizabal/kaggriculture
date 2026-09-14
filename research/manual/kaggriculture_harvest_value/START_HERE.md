# Notebook 14 — one bounded harvest-value experiment

Keep all existing workspace folders. Do not wipe, clone, install, change the
instance type, or rerun notebooks 05–13. Existing local data and runtime are reused.

## 1. Open the existing space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio →
QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab →
kaggriculture-dev. Keep working settings and old automated lifecycle scripts
unselected. This manually starts billable compute if it was stopped; no GPU is needed.

## 2. Upload and extract

Upload `kaggriculture_harvest_value.zip` into `/home/sagemaker-user` using the file
browser upload arrow. Open File → New → Terminal and run:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
home = Path('/home/sagemaker-user').resolve()
target = home / 'kaggriculture_harvest_value'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(home / 'kaggriculture_harvest_value.zip') as z:
    for member in z.infolist():
        destination = (home / member.filename).resolve()
        if not destination.is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: ' + member.filename)
        if stat.S_ISLNK(member.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected')
    z.extractall(home)
print(target / '14_harvest_value_feature_ablation.ipynb')
PY
```

## 3. Run the notebook

Open `kaggriculture_harvest_value/14_harvest_value_feature_ablation.ipynb`.
Select Kernel → Change Kernel → **Kaggriculture Manual (verified source)**,
then Run → Run All Cells. No code edits or installation should be required.

The notebook verifies the notebook-13 diagnosis and existing dependency hashes,
source commit, engine, interpreter, and 10 restored objects. Nothing is refetched.
It runs local tests and 594 real engine component comparisons. The screen has a
90-second worker cap. The optional one-pair pilot has a 180-second worker cap.
Both stages print UTC heartbeats every 10 seconds. Each stage can use up to two
seconds for graceful termination before forced shutdown. The notebook has an
additional emergency timeout; these are limits, not runtime promises.

Normal markers:

```
PREFLIGHT_PASSED
MECHANICS_PASSED
SCREEN_EPISODE_SAVED
HARVEST_VALUE_SCREEN_COMPLETE
BRANCH_CHECKPOINT_SAVED         # only after activation
HARVEST_VALUE_PILOT_COMPLETE
NOTEBOOK14_COMPLETE
```

`STOP_NO_ACTION_ACTIVATION` is a useful no-change finding, not a crash. No simulator
pair is run. `STOP_NEGATIVE_ENDPOINT` means do not adopt the intervention. A
`PROMISING_SINGLE_DEVELOPMENT_PAIR_REQUIRES_VALIDATION` decision is exploratory,
not approval for scaling or proof of an official score improvement.

If a cell errors, STOP. Save the notebook and bundle. Do not reinstall, reset Git,
remove files, raise a cap, or retry the same failed stage. Completed matching
stages/checkpoints are reusable; failed stages deliberately require diagnosis.

## 4. Save and return the result

Press Ctrl+S. Then run in Terminal:

```bash
cd /home/sagemaker-user/kaggriculture_harvest_value
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_harvest.py bundle
```

Download **`kaggriculture_harvest_value_results.zip`**. This is the result ZIP, not
the input package. Bundling works after failure and includes the saved notebook,
reports, derived tables, checkpoints and logs. It excludes source raw episodes,
credentials and environments. Preserve your source folders and this download.

Terminal-only alternative (same run, not an additional run):

```bash
"$PYTHON_BIN" run_harvest.py screen && "$PYTHON_BIN" run_harvest.py pilot
```

Use the notebook to visualize outputs; matching completed stages are verified and
reused. Do not launch notebook and Terminal stages concurrently.

## 5. Stop compute

Studio → Running instances → stop the application for kaggriculture-dev.
**Do not delete the space.** Closing the browser or reaching a notebook timeout
is not AWS shutdown. Persistent storage may still be billed when compute stops.

Official stopping procedure:
https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Scope and status

The package is not committed, pushed, or merged into GitHub. It makes no remote
writes and does not automatically change branches. Baseline main was checked at
7194116dfc92a8663139611233b5a221dad431a4. Do not claim new work is on GitHub until
it is deliberately published and its tests verified. No submission is made here.

The shipped live notebook is unexecuted. Local validation includes artificial
pricing/driver adapters; it is not a substitute for the mandatory installed-engine
and archived-control checks on AWS. See LOCAL_VALIDATION.json for exact evidence.
