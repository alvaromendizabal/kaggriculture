# Kaggriculture: next manual milestone

## What already passed

The uploaded receipts record the manual checkout at commit
`7194116dfc92a8663139611233b5a221dad431a4`, the Python 3.12.14 runtime, all ten recovered
objects, and notebook 05 in WORKSPACE-VERIFIED mode with eight executed code cells,
four charts and no error outputs. `reference/input_review.json` preserves the review.
GitHub main was checked again during preparation and still matched that commit.

Do **not** wipe the space, clone again, run preparation again, rebuild the environment,
or redownload Kaggle files. This milestone reuses the verified setup and saved episodes.
The registered Kaggle ZIP lists AGENTS.md and README.md; this stage does not need to
extract or execute those documents.

## This milestone only

Implement and validate a **new, standalone, variable-workforce feature extractor**.
The output has 124 aggregate candidates, one row for every worker, and explicit task
rows. Existing/frozen policies and their old observation boundary remain unchanged.
There is no model fit, full new game, leaderboard submission, pip installation,
cloud-resource mutation, Git push, or automatic policy promotion.

Sequence: unit tests → source/engine/data checks → four mechanics transitions →
161 saved observations from seven accepted episodes → five Plotly figures → receipts.
The worker receives a **180-second execution budget**, with up to two seconds for
termination before a forced kill. A 10-second heartbeat and per-episode receipts
make progress visible. This is an execution limit, not a completion-time guarantee.

## 1. Open the same JupyterLab space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio.
Use domain `QuickSetupDomain-20260902T115323` (ID `d-njhxv1erusdc`) and space
`kaggriculture-dev`. Open JupyterLab. If it is already running, leave it running.
If stopped, retain your working image/storage and do not reattach the old research
lifecycle script. Run only the existing space; no GPU is needed for this audit.

Your verified checkout remains:
`/home/sagemaker-user/projects/kaggriculture-manual`

Your original checkout, runtime and private data remain untouched.

## 2. Upload and extract this ZIP in your home directory

Download `kaggriculture_workforce_milestone.zip` from this conversation. In JupyterLab,
open `/home/sagemaker-user` in the left file browser and use the upload-arrow button.
Open File → New → Terminal. Paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
root = Path('/home/sagemaker-user').resolve()
archive = root / 'kaggriculture_workforce_milestone.zip'
target = root / 'kaggriculture_workforce_milestone'
if target.exists():
    raise SystemExit('Package folder already exists. Do not overwrite it. Reopen its notebook to resume, or report a version conflict.')
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        p = root / info.filename
        if not p.resolve().is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: ' + info.filename)
        if stat.S_ISLNK(info.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected: ' + info.filename)
    z.extractall(root)
print('READY:', target / '06_workforce_observation_contract.ipynb')
PY
```

Extraction refuses an existing folder rather than overwriting your work. For a
restart, reuse the existing extracted folder; do not re-extract the same ZIP.

## 3. Run notebook 06 only

Open:
`/home/sagemaker-user/kaggriculture_workforce_milestone/06_workforce_observation_contract.ipynb`

Choose Kernel → Change Kernel → **Kaggriculture Manual (verified source)**.
Then choose Run → Run All Cells.

No code edits or package installation should be necessary. The notebook launches
the audit with the verified interpreter and creates outputs inside the new package.

### Required success marker

```text
WORKFORCE_COVERAGE_PASSED
```

A successful report requires 46 tests with no failures/errors/skips, ten input hashes,
12 engine observation views across two hiring seats, four mechanics transitions,
161 saved observations, 124 aggregate feature names, finite outputs, unchanged input
observations, and seven durable replay checkpoints.

The exact number of varying candidates, worker rows, task rows and runtime will be
measured on your AWS machine—not filled in from reference data.

**Expected limitations remain visible:**

```text
Full-callback acceptance: NOT_RUN
Official metric improvement measured: False
```

These are not errors. This stage verifies representation coverage, not a full agent.

### On failure

Stop at the failed cell. Do not run historic studies, reinstall packages, relax hash
checks, or retry unchanged errors. Valid checkpoints remain saved. Proceed to step 4
so the result archive includes the failure and any completed work.

### Restart behavior

After an interruption, reopening and rerunning this notebook verifies hashes and
reuses completed episode checkpoints. Corrupted or different-source checkpoints
cause a stop instead of being silently overwritten. Persistent failures need diagnosis.

## 4. Save the notebook and create the return ZIP

Choose File → Save Notebook (Ctrl+S). This matters: bundling a notebook before saving
could omit its executed cell outputs.

In the JupyterLab terminal paste:

```bash
cd /home/sagemaker-user/kaggriculture_workforce_milestone
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_milestone.py bundle
```

The bundle command also works after an audit failure. Download from the file browser:

`kaggriculture_workforce_milestone/kaggriculture_workforce_results.zip`

Return that one ZIP in this chat. It contains the saved notebook, report/failure,
checksummed derived checkpoints, feature tables, five-chart dashboard, and logs.
It does not include your raw episode archives, credentials, or environment.

## 5. Stop compute

In Studio → Running instances, stop the JupyterLab application for
`kaggriculture-dev`. Do not delete the space or storage. Closing the browser tab is
not stopping compute; stopping compute does not remove persistent storage charges.

## Terminal alternative (not an additional step)

The notebook already performs the run. Only use this alternative when intentionally
running without notebook execution; do not run both simultaneously:

```bash
cd /home/sagemaker-user/kaggriculture_workforce_milestone
PYTHON_BIN="$(python3 -c 'import json; from pathlib import Path; print(json.loads((Path.home()/"kaggriculture_manual_resume/state/runtime.json").read_text())["executable"])')"
"$PYTHON_BIN" run_milestone.py run --seconds 180
```

Open notebook 06 afterward for visual review; the same run will reuse verified
checkpoints. Do not launch two workers concurrently.

## What comes afterward

The next decision is action-path integration and measured full-callback acceptance,
not another environment rebuild or an uncontrolled large simulation. Only after that
can one-family, equal-staffing paired experiments quantify contribution to game outcomes.
Feature counts and green coverage tests do not justify a claimed score improvement.

## GitHub status

The reviewed baseline is merged. **This new downloadable package is not committed,
pushed or merged.** No repository was changed by this response. It is intentionally
kept outside the checkout until its actual AWS report is reviewed. Preserve original
policy files, Study 7 evidence and raw episode artifacts in any subsequent publication.
