# Notebook 16 — one missing factorial branch, not another setup round

Use the existing `kaggriculture-dev` space, Oregon (`us-west-2`), domain `QuickSetupDomain-20260902T115323`, profile `default-20260902T115323`. Keep working image/storage settings and leave old automated lifecycle scripts unselected. No GPU, instance change, installation, data download, Git reset or clone is required. All prior folders and raw data remain unchanged.

## 1. Upload the complete package

Download `kaggriculture_renewal_factorial.zip` from ChatGPT. In JupyterLab's file browser, go to `/home/sagemaker-user` and use the upload arrow. Open **File → New → Terminal**.

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
home=Path('/home/sagemaker-user').resolve()
target=home/'kaggriculture_renewal_factorial'
if target.exists():
    raise SystemExit('Folder already exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(home/'kaggriculture_renewal_factorial.zip') as z:
    for member in z.infolist():
        dest=(home/member.filename).resolve()
        if not dest.is_relative_to(target):
            raise SystemExit('Unsafe ZIP path: '+member.filename)
        if stat.S_ISLNK(member.external_attr >> 16):
            raise SystemExit('ZIP symlink rejected')
    z.extractall(home)
print(target/'16_renewal_factorial_feature_ablation.ipynb')
PY
```

## 2. Open and run the notebook

Open `/home/sagemaker-user/kaggriculture_renewal_factorial/16_renewal_factorial_feature_ablation.ipynb`.

Select **Kernel → Change Kernel → Kaggriculture Manual (verified source)**. Restart this notebook's kernel, then **Run → Run All Cells**. Do not run the separate terminal alternative simultaneously.

Expected stages:

```text
PREFLIGHT_PASSED
MECHANICS_PASSED
SCREEN_DAY_SAVED
RENEWAL_FACTORIAL_SCREEN_COMPLETE
CLEAR_ONLY_CHECKPOINT_SAVED
RENEWAL_FACTORIAL_COMPLETE
NOTEBOOK16_COMPLETE
```

The screen checks 527 control-path observations. It has a 120-second worker cap, with a ten-second heartbeat and daily checkpoints. If there is action activation, the pilot has a separate 120-second cap and runs just one new branch: 192 prefix replay steps plus 527 responsive decisions. Candidate, control, null and opponent callbacks must each take no more than 500 ms. Worker cleanup allows up to two extra seconds. These caps are not runtime estimates or automatic AWS shutdown.

If all 527 actions are verified identical, the final result reuses the control endpoint by an explicit full-path identity proof; no new game transitions are required. The method is reported as `full_control_path_action_identity_no_new_transitions` rather than a newly simulated game.

All three completed notebook-15 branches are reused. Previous notebooks are checked but not rerun. The new ordinary WATER expression remains unchanged; indirect later actions may change because the state changes.

## 3. Interpret the result

`FACTORIAL_DIAGNOSIS_COMPLETE_NO_AUTOMATIC_PROMOTION` means four cells have evidence. It is not a claim that the agent improved. Read `new_arm_decision`, `contrasts.csv`, and `factorial_effects.csv`.

The report separates competitive interpretation (local win/draw/loss and coin margin) from the existing conservative no-decline guard (which also includes own cash). A higher margin with less own cash is mixed evidence, not silently converted into an accepted strategy or called a lost match. No p-values, confidence intervals, independent-seed claims or leaderboard score are generated.

No action activation or no endpoint benefit means stop this unchanged intervention. A positive known-block result requires fresh groups and different opponents before adoption. This is the final missing comparison in this block, not authorization for more threshold tuning on the same seed.

## 4. Save and bundle — also after an error

Press **Ctrl+S** to save the notebook. In a terminal:

```bash
cd /home/sagemaker-user/kaggriculture_renewal_factorial
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path.home()/'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(p.read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_factorial.py bundle
```

Download **`kaggriculture_renewal_factorial_results.zip`** from this folder and attach it to ChatGPT. Do not send the original input ZIP. The result includes your saved notebook, available results, derived features, daily checkpoints, the new branch (if completed), logs and dashboard; it excludes source raw episodes, credentials and environments.

On failure, stop. Do not reinstall, reset Git, delete checkpoints, raise caps or retry unchanged. The runner refuses an unchanged failed/active/interrupted stage. A successfully completed stage can be reopened and verified without repeating computation.

## 5. Stop compute

Return to Studio → **Running instances**, find `kaggriculture-dev`, and choose **Stop**. Do not delete the space. Closing the browser or reaching the timeout does not stop the application. Persistent storage can still incur charges when compute is stopped.

Official AWS shutdown documentation: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Terminal alternative (instead of notebook execution)

Use `bash RUN_TERMINAL.sh` from this extracted folder to run screen then pilot, export the dashboard, and bundle. This does not execute/save notebook outputs; to populate the notebook afterward, open it and Run All. Verified completed stages will be reused.

## GitHub and local file boundaries

Reviewed baseline: `7194116dfc92a8663139611233b5a221dad431a4`. This package is a new local manual package, not a committed/pushed/merged repository change. It does not modify AWS resources or either checkout. The runtime preflight checks the pinned baseline, complete engine manifest, prior result hashes, necessary dependency hashes and all ten recovered objects. The complete callback's existing workforce-domain limitation is unchanged.
