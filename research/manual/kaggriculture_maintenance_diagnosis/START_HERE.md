# Notebook 13 — one bounded diagnostic milestone

Notebook 12 completed but its deferral intervention lost 396 own coins. Do not
rerun it, adopt it, reinstall packages or reset Git. This package replays existing
recorded actions, reconstructs the missing crop/trade evidence and evaluates
prospective interaction features. It does not compute new policy decisions.

## 1. Open the same JupyterLab space

AWS console → SageMaker AI → US West (Oregon), us-west-2 → Studio →
QuickSetupDomain-20260902T115323 → default-20260902T115323 → JupyterLab →
kaggriculture-dev. Keep the working image/storage and old research lifecycle scripts
unselected. No GPU or instance-type change. Opening a stopped application starts
billable compute; closing its browser does not stop it.

## 2. Upload the complete ZIP to /home/sagemaker-user

Upload `kaggriculture_maintenance_diagnosis.zip` using JupyterLab's file-browser upload
arrow. File → New → Terminal, then paste:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path
import stat, zipfile
home = Path('/home/sagemaker-user').resolve()
target = home / 'kaggriculture_maintenance_diagnosis'
if target.exists():
    raise SystemExit('Folder exists. Reopen its notebook; do not overwrite it.')
with zipfile.ZipFile(home / 'kaggriculture_maintenance_diagnosis.zip') as z:
    for member in z.infolist():
        path = (home / member.filename).resolve()
        if not path.is_relative_to(target) or stat.S_ISLNK(member.external_attr >> 16):
            raise SystemExit('Unsafe ZIP member: ' + member.filename)
    z.extractall(home)
print(target / '13_maintenance_loss_and_interaction_features.ipynb')
PY
```

## 3. Run the notebook

Open `kaggriculture_maintenance_diagnosis/13_maintenance_loss_and_interaction_features.ipynb`.
Kernel → Change Kernel → **Kaggriculture Manual (verified source)**.
Run → Run All Cells. No installation or source edits are needed.

Expected: PREFLIGHT_PASSED → MECHANICS_PASSED → PREFIX_REPLAY →
RECORDED_SUFFIX_REPLAY → RECORDED_BRANCH_VERIFIED (control and defer) →
MAINTENANCE_DIAGNOSIS_COMPLETE → NOTEBOOK13_COMPLETE.

One stage has a 120-second hard cap, with up to two seconds for termination before
forced shutdown. Ten-second heartbeats and per-branch, SHA256-verified checkpoints
are saved. The stage timeout does not stop your AWS application. The accepted
report should reproduce **−396**, not show a new improvement. That is a successful
reconstruction of a rejected policy, not a repeated failed performance trial.

The notebook displays eight Plotly views after the live replay. The first two use
already-verified notebook-12 evidence; the other six require the new diagnostic
outputs. A feature can be correctly implemented and never activate; that is not an
error and is not feature importance.

On any new error, stop and bundle. Do not reinstall, delete files, increase limits,
weaken assertions or retry unchanged. Completed prior files are read-only.

## 4. Save and bundle

Press Ctrl+S. In JupyterLab Terminal:

```bash
cd /home/sagemaker-user/kaggriculture_maintenance_diagnosis
PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads((Path.home() / 'kaggriculture_manual_resume/state/runtime.json').read_text())['executable'])
PY
)"
"$PYTHON_BIN" run_diagnosis.py bundle
```

Download **kaggriculture_maintenance_diagnosis_results.zip** from this folder and
upload that results ZIP to the chat, not the original input package. Bundling works
after an error and excludes raw source episodes, environments and credentials.

## 5. Stop compute

Studio → Running instances → stop kaggriculture-dev's application. Do not delete
the space. Stop preserves files; delete removes the space's storage.
https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html

## Scope and status

GitHub baseline verified for this handoff: 7194116dfc92a8663139611233b5a221dad431a4.
This package is not pushed, committed or merged. No Git pull is required to run it.
Do not run notebooks 05–12 again. This step does not submit to Kaggle or deploy
features. The live experiment is not claimed as tested in ChatGPT; see LOCAL_VALIDATION.json.
