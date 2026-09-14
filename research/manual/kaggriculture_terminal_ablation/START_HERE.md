# Resume notebook 09 after the diagnosed mechanics error

**Use the existing space, source checkout, data, Python environment and notebook number.**
Do not create notebook 10, reinstall packages, pull/reset Git, wipe the space, or
rerun notebooks 05–08. The correction changes the test expectation, not the agent.

## 1. Upload the single updater

Download `apply_notebook09_update.py` from ChatGPT. In the existing SageMaker
JupyterLab space, save the failed notebook and close its tab before updating.
Upload the updater into `/home/sagemaker-user` using the left file browser's
upload arrow. Do not upload it inside a repository or the notebook package.

If starting with only ChatGPT: open AWS Console → SageMaker AI → US West (Oregon)
→ Studio → `QuickSetupDomain-20260902T115323` → profile
`default-20260902T115323` → JupyterLab → `kaggriculture-dev`.
Preserve working image/storage settings; do not reattach the old research
lifecycle script. Starting a stopped application starts billable compute.

## 2. Apply to the canonical files

Open File → New → Terminal. Paste:

```bash
cd /home/sagemaker-user
python3 apply_notebook09_update.py
```

The updater uses only the Python standard library. It does not install anything,
run games, change Git, call AWS APIs, or alter raw data.
It requires the exact original source and known failed mechanics receipt and
refuses to alter a completed or partially completed branch experiment.
It creates a verified timestamped ZIP in `kaggriculture-update-backups`, including
the failed notebook and original diagnostics, before updating files in place.

Expected marker: `MECHANICS_UPDATE_APPLIED`.
`ALREADY_APPLIED` means the source was already updated; do not apply it again.
It does not renew a consumed restart permission.

If the updater refuses because it detects a different failure or unexpected
branch results, do not delete them. Use the bundle command in Step 4 and return
the bundle plus the updater's message.

## 3. Reopen notebook 09 and run it

Open the original canonical path:

```
/home/sagemaker-user/kaggriculture_terminal_ablation/09_terminal_cash_feature_ablation.ipynb
```

Select `Kaggriculture Manual (verified source)`.
Choose Kernel → Restart Kernel, then Run → Run All Cells.
Do not overwrite the revised file by saving an older open notebook tab.

The runner consumes a one-use authorization bound to the corrected code and the
specific failed run. It then runs 86 unit tests, source/data preflight, the real
pinned-engine mechanics gate, and the original paired continuation experiment.

The mechanics gate should report:

| Fixture | Initial WHEAT quote | Expected cash delta | Observed cash delta |
|---|---:|---:|---:|
| early_sale_catches_up | 13 | 0 | 0 |
| last_callback_stranding | 13 | 26 | 26 |

Expected markers: `REVIEWED_MECHANICS_RESTART_AUTHORIZED`, `PREFLIGHT_PASSED`,
`MECHANICS_PASSED`, `BRANCH_CHECKPOINT_SAVED`, `PAIR_COMPLETE`,
`TERMINAL_CASH_EXPERIMENT_COMPLETE`, `NOTEBOOK09_COMPLETE`.
The existing early-stop rules still apply. Completion is not proof of improvement.

The worker cap remains 180 seconds plus termination cleanup; callbacks remain
limited to 500 ms each. Ten-second heartbeat logging and branch checkpoints remain.
The timeout does NOT stop the SageMaker application or cap total idle billing.
The real mechanics gate uses 12 tiny interpreter transitions; the experiment uses
at most 14 final-day branches, not 14 new seasons from initial state.

The notebook contains the existing seven experiment charts plus one new Plotly
mechanics comparison. No AWS experiment result is prefilled in the delivered notebook.

If any new error occurs, stop and bundle. No unchanged automatic retry is authorized.
Do not bypass tests, change the expected value manually, or increase limits.

## 4. Save, bundle, download, and stop compute

Press Ctrl+S. In a JupyterLab terminal paste:

```bash
cd /home/sagemaker-user/kaggriculture_terminal_ablation

PYTHON_BIN="$(python3 - <<'PYCODE'
import json
from pathlib import Path
receipt = Path.home() / 'kaggriculture_manual_resume/state/runtime.json'
print(json.loads(receipt.read_text())['executable'])
PYCODE
)"

"$PYTHON_BIN" run_continuation.py bundle
```

Download `kaggriculture_terminal_ablation_results.zip` from this folder and upload
that ZIP to ChatGPT. The command also works after a failure. It includes the saved
notebook, updated diagnostics, restart receipt, report/feature tables if present,
and completed branch checkpoints; it does not bundle the raw source episodes.

Return to Studio's Running instances and stop the JupyterLab application for
`kaggriculture-dev`. Do not delete the space. Closing the browser tab is not shutdown.

## How to interpret the research outcome

`STOP_NO_TERMINAL_BENEFIT` means that earlier isolated cash receipts did not yield
an endpoint benefit in these paired branches. `STOP_NEGATIVE_TERMINAL_EFFECT`
means the runner preserved a harmful comparison and stopped. A promising outcome
still requires fresh grouped episodes and different opponents. No result in this
notebook is a Kaggle rating, and the 3140.0 target has not been verified or surpassed.

Keep the post-action sellable-inventory feature as the only action-changing
intervention in this test. The twelve exposure candidates remain diagnostic-only.
Subsequent rounds remain joint task opportunity, production and maintenance
value, hiring/land payback, and causal market history, with controlled ablations.
