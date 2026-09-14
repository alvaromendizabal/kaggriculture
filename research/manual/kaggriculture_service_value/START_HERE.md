# Next milestone: two service-value screens, notebooks 19 and 20

## What to run now

Run the two notebooks **sequentially through their screen/review boundary**. Do
not launch paired games yet. Both feature implementations, their tests and the
future single-pair driver are included. No test or notebook in this package has
been executed by the assistant. See PREPARATION_STATUS.json.

Round 19: collection-to-sale completion time. Round 20: critical WATER/FEED
completion slack. Each has 32 option descriptors, 12 summaries, 32 round-specific
tests plus 32 common tests, installed-engine mechanics checks, and ten inline
Plotly views. The common tests overlap: 96 distinct methods, not 128 unique tests.

## 1. Open the established environment

Starting with only ChatGPT open, open the AWS console in another browser tab.
Choose SageMaker AI, US West (Oregon) / us-west-2, Studio,
QuickSetupDomain-20260902T115323, profile default-20260902T115323,
JupyterLab, and kaggriculture-dev. Open the existing space; if stopped, keep its
working image/storage settings and old research lifecycle scripts unselected.

Do not wipe, clone, install, reset Git, redownload data, or rerun notebooks 05–18.
The source/runtime/data receipts from manual resume and the seven restored
episodes must still be present. Current AWS/GitHub account state was not checked.
Use the existing Kaggriculture Manual (verified source) kernel, Python 3.12.
No GPU or instance-type change is required for the prepared screens.

## 2. Upload and extract once

Upload `kaggriculture_service_value.zip` into `/home/sagemaker-user` with the
JupyterLab file browser upload-arrow button. Open File → New → Terminal:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat
import zipfile
home = Path('/home/sagemaker-user').resolve()
target = home / 'kaggriculture_service_value'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebooks; do not overwrite it.')
with zipfile.ZipFile(home / 'kaggriculture_service_value.zip') as z:
    for member in z.infolist():
        path = (home / member.filename).resolve()
        if not path.is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: ' + member.filename)
        if stat.S_ISLNK(member.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected')
    z.extractall(home)
print(target)
PY
```

## 3. Run notebook 19 to its review boundary

Open `kaggriculture_service_value/19_collection_completion_feature_ablation.ipynb`.
Select Kernel → Change Kernel → Kaggriculture Manual (verified source).
Restart this notebook's kernel, then Run → Run All Cells.

It runs 64 supplied tests, preflight, installed-engine fixtures, and a 957-state
archived development screen. Passing tests is not a performance gain. The real
engine fixtures must pass even when the unit tests pass.

Expected markers, only if successful:

```
PREFLIGHT_PASSED
MECHANICS_PASSED
SCREEN_PROGRESS
SCREEN_SOURCE_SAVED
FEATURE_SCREEN_COMPLETE
ROUND_REPORT_SAVED
ROUND19_REVIEW_GATE
```

`STOP_NO_ACTION_ACTIVATION` means no sampled commands changed.
`REVIEW_REQUIRED_BEFORE_GAMES` means action changes require inspection, not that
the feature helps. Either is a valid completed screen. Both save evidence.
No screen marker authorizes Run All to start full games; no pair cells are in
these notebooks. The optional outcome views read existing results only.

A Python exception, source mismatch, resource violation or failed test is
**not** an acceptable screen result. Stop and bundle; do not retry unchanged.

## 4. Save notebook 19, then run notebook 20

Press Ctrl+S. Open
`kaggriculture_service_value/20_maintenance_slack_feature_ablation.ipynb`, choose
the same kernel, restart it, and Run → Run All Cells. Do not run both at once.

This is an independent screen against the unchanged control. A normal
nonactivation result in 19 does not invalidate 20. An integrity/runtime exception
should be returned first rather than worked around. Round 20 has its own 64 tests,
mechanics fixtures, 957-state screen and ten inline figures. Its final marker is
`ROUND20_REVIEW_GATE`.

Save with Ctrl+S. Close/reopen each saved notebook once without rerunning it and
confirm its charts and outputs remain visible. The renderer writes Plotly MIME
and inline notebook HTML; an HTML dashboard also supplements the notebook. Do not
replace inline figures with file paths. If charts are absent, return the saved
notebook and its browser/kernel symptom; do not reinstall blindly.

## 5. Return the combined results

After saving both notebooks, in a terminal:

```bash
cd /home/sagemaker-user/kaggriculture_service_value
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_service.py bundle
```

Download `kaggriculture_service_value_results.zip` from this folder and attach it
to ChatGPT. Do not return the input ZIP instead. The bundle contains both saved
notebooks, tests/fixture receipts, screen reports, option and state tables,
checkpoints, logs and dashboards. No raw source episodes or credentials are
included. Bundling works after failure; it does not rerun an experiment.

## 6. Stop AWS compute manually

In Studio choose Running instances, locate kaggriculture-dev and Stop its
application. Do **not** delete the space. Closing the browser or hitting a script
timeout does not stop billable AWS compute. Source: AWS Studio stop documentation,
https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html.

## Limits and cost assumptions

Each screen's supervised worker has a **180-second cap**, including tests,
preflight and mechanics, plus up to two seconds for termination. The notebook's
emergency wrapper deadline is 195 seconds, not a second allowance for research.
The worker RSS limit is 8 GiB; the inherited environment and plotting process can
consume additional memory. No model fits and no complete games run in this
milestone. Input hashes and schemas are checked before research.

Ten-second heartbeats show elapsed time, worker RSS and the last genuine work
progress event. Completed sources have atomic checksummed checkpoints and
readback verification. At most 957 screened states per round. Resource limits
are safety ceilings, not promises of completion or performance.

The two worker budgets together allow at most six minutes of research processing,
plus termination, plotting, startup, your interaction and idle time. At an
*illustrative*, not quoted, instance rate of $1/hour, six minutes is $0.10;
$2/hour makes it $0.20. Actual pricing, instance rate and bill are not verified.
Use your displayed AWS rate; EBS/storage and other existing charges remain.
There are no new instance requests, account changes or network writes in the code.

## Safe interruption

Interrupt the notebook cell once. The wrapper asks the supervisor to terminate;
the supervisor records a failed/interrupted stage and stops its worker. Wait for
the interrupt output, save and bundle. Do not remove the execution lock or change
a failed status to COMPLETED. Completed artifacts remain available for diagnosis;
restarting a failed stage requires a reviewed correction, not repeated retries.
The tests include a tiny deliberate subprocess interruption to check a completed
checkpoint remains readable. That is not a claim of mid-game resumability.

## Terminal alternative for the same screens

Use this only instead of the notebook's execution cell, not in parallel with it.
After defining PYTHON_BIN as above:

```bash
"$PYTHON_BIN" run_service.py screen --round 19
"$PYTHON_BIN" run_service.py summary --round 19
# Inspect the return code/output before proceeding.
"$PYTHON_BIN" run_service.py screen --round 20
"$PYTHON_BIN" run_service.py summary --round 20
```

Then open the notebooks to display the saved results; the screen stage reuses a
verified completed result rather than rerunning. Save both before bundling.

## Later steps, not part of this run

Review both screens together. Decide whether either feature changes relevant
first commands often enough, passes complete callback timing, and appears worth
one paired development block. Future paired-game code is included, but the CLI
requires the exact reviewed screen hash; see FUTURE_PAIRS.md. We do not infer
metric improvement from action changes. No automatic feature adoption, stacking,
more seeds, account operation, public publishing or Kaggle submission occurs.

Source-only manual Git publication is documented separately in GIT_WORKFLOW.md.
Remote GitHub state has not been verified. Preserve the working environment and
raw data regardless of a publication or source-compatibility issue.
