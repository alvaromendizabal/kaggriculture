# Kaggriculture: two complete manual feature-research rounds

Run **17**, then **18**, in the same package folder. Do not run them concurrently.
Each round has its own feature code, dictionary, tests, mechanics gate, activation
screen, four registered paired blocks, outcome review, and ten Plotly views.
Neither candidate is combined with the other. Both use the unchanged research
control plus the existing final-callback sale correction.

## 1. Open the existing space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio →
QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab → kaggriculture-dev.
Keep the current image/storage. Leave old automatic research lifecycle scripts
unselected. Do not wipe, clone, install, reset Git, change instance type or rerun
notebooks 05–16. Starting the existing application starts billable compute; no GPU
is needed. Closing your browser does not stop it.

## 2. Upload one ZIP, once

Upload `kaggriculture_two_rounds.zip` into `/home/sagemaker-user` with JupyterLab's
upload-arrow button. File → New → Terminal, then paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
home = Path('/home/sagemaker-user').resolve()
target = home / 'kaggriculture_two_rounds'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebooks; do not overwrite it.')
with zipfile.ZipFile(home / 'kaggriculture_two_rounds.zip') as z:
    for item in z.infolist():
        path = (home / item.filename).resolve()
        if not path.is_relative_to(target) or stat.S_ISLNK(item.external_attr >> 16):
            raise SystemExit('Unsafe ZIP entry: ' + item.filename)
    z.extractall(home)
print('Open:', target)
PY
```

## 3. Run round 17

Open `17_arrival_harvest_feature_ablation.ipynb`.
Kernel → Change Kernel → **Kaggriculture Manual (verified source)**.
Restart the kernel, then Run → Run All Cells, or execute the cells one at a time.
Every game-pair cell is a separate checkpointed, bounded milestone.

Expected markers: `PREFLIGHT_PASSED`, `MECHANICS_PASSED`, `FEATURE_SCREEN_COMPLETE`,
then `GAME_CHECKPOINT_SAVED` / `GAME_CHECKPOINT_REUSED`, `PAIRED_BLOCK_COMPLETE`,
`ROUND_COMPLETE`, and `ROUND17_COMPLETE`.

A `STOP_NO_ACTION_ACTIVATION` screen skips all games. A `STOP_NEGATIVE_ENDPOINT`
pair skips later pairs in that round. These are research conclusions, not software
errors. The notebook still builds the report and plots the actual available data.
No outcome is fabricated for skipped blocks.

If there is an exception, stop and bundle. Do not change thresholds, reinstall,
delete status files, or repeat the failed stage unchanged. An engine/source/data
integrity failure must be reviewed before running round 18. If round 17 completes
normally with no activation or a negative endpoint, round 18 remains independent
and can run as designed.

## 4. Save, then run round 18

Press Ctrl+S. Open `18_production_headroom_feature_ablation.ipynb` in the same folder.
Choose the same verified kernel; restart it; Run All Cells.

Round 18 repeats the same quality gates for its different feature hypothesis.
It reuses matching fresh controls from round 17 and runs only missing candidates
and any missing controls. It does **not** use round 17's candidate as its baseline.
There is no installation or second ZIP to upload.

Limits: 120 seconds per screen, 180 seconds per pair, 500 ms per measured callback.
The supervisor allows up to two seconds for shutdown; notebook emergency limits
allow supervisory cleanup. Heartbeats appear every ten seconds. There are at most
four pairs per round. At most twelve new games total when all eight pairs run and
four identical controls are reused. No automatic extension to additional seeds.
These are caps, not runtime estimates or automatic AWS shutdown instructions.

## 5. Save and bundle

Press Ctrl+S in both notebooks. In the JupyterLab terminal:

```bash
cd /home/sagemaker-user/kaggriculture_two_rounds
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
receipt = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(receipt.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_research.py bundle
```

Download **kaggriculture_two_rounds_results.zip** from this folder. Return that ZIP,
not the original input package. It includes both saved notebooks, available tables,
new-game action/diagnostic checkpoints, plots and logs. Raw source episodes,
credentials and environments are excluded. Bundling also works after an error.

## 6. Stop AWS compute

Studio → Running instances → kaggriculture-dev → Stop application.
**Do not delete the space.** Completed artifacts survive application shutdown.
The experiment time limits do not shut down the AWS application.

## Terminal alternative (same stages as notebooks; do not run both in parallel)

Use the `PYTHON_BIN` assignment above, then:

```bash
"$PYTHON_BIN" run_research.py screen --round 17
"$PYTHON_BIN" run_research.py pair --round 17 --block 1
"$PYTHON_BIN" run_research.py pair --round 17 --block 2
"$PYTHON_BIN" run_research.py pair --round 17 --block 3
"$PYTHON_BIN" run_research.py pair --round 17 --block 4
"$PYTHON_BIN" run_research.py summary --round 17
```

Repeat those six commands with `--round 18`. Stop at an exception. Completed stages
are reused only after checksum and lineage verification; a failed stage is not
automatically retried. Reopen notebooks to render the result charts.

## Interpretation

The source is still pinned at `7194116dfc92a8663139611233b5a221dad431a4`.
This package is not committed/pushed/merged; no external writes occur. The code
checks the exact original FeedPolicy blob before an in-memory expression change.
Two newly registered development seed groups are not a final holdout. Balanced
seat/opponent coverage is not a fully crossed study. Shared controls correlate the
two rounds. Feature activity, intermediate quote value, and local coins are not
Kaggle rating points. There is no automatic adoption and no submitted score here.
