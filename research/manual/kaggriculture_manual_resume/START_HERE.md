# Kaggriculture · Manual workspace recovery

**Reviewed source:** `7194116dfc92a8663139611233b5a221dad431a4` on `main`, September 11, 2026.  
**This milestone:** preserve → synchronize source → verify runtime → restore accepted checkpoints → review feature evidence.  
**New games, training, submissions, cloud-resource changes by these scripts: zero.**

## What was actually verified

GitHub PR #15 is merged. The exact `main` push passed Quality run **34641284139**, completed at **2026-09-11 20:00:00 UTC / 1:00 p.m. PDT**. The AWS space exists with a 30 GiB persistent volume, and its JupyterLab application was stopped (`Deleted`) at inspection. The latest canonical-workspace synchronization receipt that was retrieved records an older commit, `1ce94d0942626d3fbb67124ac35b3d732bf06e12`, at **2026-09-11 03:46:25 UTC / September 10, 8:46 p.m. PDT**. Later research used separate worktrees. This is not a direct inspection of every current EBS file.

The last app had lifecycle configuration `kaggriculture-bottlenecks-20260911`. That configuration can launch an old research dispatcher. **Do not reuse it for this manual session.**

The raw private trajectories are deliberately excluded from public GitHub. Seven accepted staffing episodes and three supporting receipts can be recovered from exact versioned S3 objects, totaling **1,426,257 bytes**. An old workspace ZIP also exists in S3, but its existence is not proof that it includes all raw assets or the latest edits. This package does not restore that old ZIP over anything.

## Do not wipe, reset, or clean the original

Do not delete the SageMaker space, run `git reset --hard`, run `git clean -fdx`, delete `.venv`, or remove the old `projects/kaggriculture` directory. Do not move the old repository: existing Git worktrees and virtual-environment entry points may refer to its current path.

Instead, this package creates a separate checkout:

```text
/home/sagemaker-user/
├── projects/kaggriculture/                    ORIGINAL: left untouched
├── projects/kaggriculture-manual/             clean reviewed GitHub source
├── kaggriculture-private/
│   ├── manual-resume/staffing/                exact private S3 checkpoints
│   └── raw/kaggle-downloads/                  original Kaggle downloads
└── kaggriculture_manual_resume/               this package, notebook and receipts
```

A second checkout is not a backup of the whole volume. It prevents source synchronization from erasing your existing data. Private S3 remains separate durable storage.

## 1. Open the correct AWS space, without its old startup script

1. Open a new browser tab and sign into the AWS console.
2. Search for **SageMaker AI**. Set the region to **US West (Oregon), `us-west-2`**.
3. Open **Studio**. Select domain **`QuickSetupDomain-20260902T115323`**, ID **`d-njhxv1erusdc`**. Use profile **`default-20260902T115323`**. Open Studio.
4. In Studio, open **JupyterLab**, then select **`kaggriculture-dev`**.
5. Before choosing Run space, expand **Space Settings**. Clear **Lifecycle Configuration** to **None / no selected script**. In particular, do not select `kaggriculture-bottlenecks-20260911` or a bootstrap/publication script. Keep the existing 30 GiB storage and image. Do not create or delete a space.
6. Choose **Run space**, then **Open JupyterLab**. This starts billable compute. The existing default is `ml.m5.xlarge`; no GPU is needed for this milestone.

The available UI wording can vary. If the old lifecycle configuration cannot be cleared, stop before Run space rather than knowingly launching it. The read-only checks found no built-in/default LCC in the domain/space settings; the old LCC was in the last app resource configuration and the profile's selectable list.

## 2. Upload and extract this package in your home directory

In JupyterLab's left file browser, navigate to the home directory (not inside the old repository). Click the upload-arrow button and choose **`kaggriculture_manual_resume.zip`** from your computer's Downloads folder.

Open **File → New → Terminal**, and paste this entire block:

```bash
cd /home/sagemaker-user
python3 - <<'PY'
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
home = Path.home()
archive = home / 'kaggriculture_manual_resume.zip'
target = home / 'kaggriculture_manual_resume'
if target.exists():
    print('Existing package preserved. No files overwritten:', target)
else:
    with ZipFile(archive) as z:
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] != target.name:
                raise RuntimeError('Unexpected archive member: ' + item.filename)
            if ((item.external_attr >> 16) & 0o170000) == 0o120000:
                raise RuntimeError('Unexpected archive symlink')
        z.extractall(home)
    print('Extracted:', target)
PY
cd /home/sagemaker-user/kaggriculture_manual_resume
```

The extraction block refuses unsafe member paths and does not overwrite an existing package directory. For a later revised package, preserve existing receipts rather than blindly extracting over them.

## 3. Test, synchronize and verify the notebook runtime

Run:

```bash
cd /home/sagemaker-user/kaggriculture_manual_resume
python3 -m unittest discover -s tests -v && python3 resume.py prepare
```

Proceed only if the tests pass and preparation prints **`PREPARE_PASSED`**.

Preparation has a **300-second stage budget** and does the following:

- Saves a bounded inventory of candidate data/archive paths, original Git status and worktrees. This is not a complete data-provenance audit and does not read credentials.
- Checks that GitHub `main` is still the reviewed SHA. A newer tip causes a safe stop rather than silently using a different version.
- Clones the reviewed source to `projects/kaggriculture-manual`, or reuses that clone only if its origin, SHA and cleanliness match.
- Checks Python 3.12, exact project dependency versions, and the pinned official simulator SHA256.
- Reuses the old project's Python **without installing or changing packages**, unless an existing isolated runtime in the new checkout is already present.
- Installs a **separate** kernel named **Kaggriculture Manual (verified source)**. It binds imports to the new checkout before and after IPython initialization and tests a real kernel. Existing `kaggriculture` kernels are not replaced.

Do not run `uv sync` from the original checkout. A shared runtime is read-only for this workflow. It saves dependency installation work; it does not claim that the environment was copied or that unrelated projects are isolated from later manual package changes.

## 4. Restore the seven accepted staffing episodes

Run:

```bash
cd /home/sagemaker-user/kaggriculture_manual_resume
source state/runtime.env && "$KAG_PYTHON" resume.py restore
```

Expected success: **`RESTORE_PASSED`**, with **7 episodes and 10 verified objects**. The stage budget is **120 seconds**. Completed files are retained, and progress is saved after every object. Rerunning a successful restore checks hashes and does not download the same valid files again.

The downloader requests each recorded S3 **VersionId**, checks the returned version and size, verifies its **SHA256**, and only then publishes it to its final local name. An existing mismatching file is preserved and causes a stop, not an overwrite. The new checkout receives an ignored `artifacts/staffing_episodes` link to these private files after the Git ignore rule is verified. Tracked reports, notebooks and frozen policies are not replaced by old S3 versions.

This restores the current pilot's evidence, **not every historical study**. The earlier files in the original checkout and S3 remain untouched. Do not assume all historical notebook pipelines can be rerun from these seven episodes.

An `AccessDenied` result concerns the notebook execution role, which may differ from the connected AWS inspection identity. Preserve the error; do not paste keys into ChatGPT or grant a broad new policy as a workaround.

## 5. Keep the original Kaggle assets separately

Kaggriculture is a **simulation-agent** competition. The official simulator and saved episodes matter; it is not safe to assume a conventional `train.csv` / `test.csv` workflow. GitHub source, official Kaggle downloads, and generated private episodes are three different things.

The original workspace is still there. `state/inventory.json` lists candidate data/archive paths found there. A file's presence or extension does not prove that it is the complete official data kit.

To make a clearly identified copy of the current official download available:

1. In a separate browser tab, open the Kaggriculture **Data** page and sign into your own Kaggle account. Complete any rule acceptance required for data access.
2. Inspect the listed files and use the available **Download All** option, or download the specific official files that page offers. Do not invent a missing `train.csv`. If no downloadable data files are offered, record that fact rather than creating fake data.
3. In JupyterLab's file browser, navigate to **`kaggriculture-private → raw → kaggle-downloads`**, which preparation creates. Upload the original download file(s) there. If a filename already exists, cancel the overwrite and keep the new download in a date-labeled subfolder; registration scans subfolders. Do not upload `kaggle.json` or an API token to this folder.
4. Return to the terminal and run:

```bash
cd /home/sagemaker-user/kaggriculture_manual_resume
python3 resume.py register-raw
```

This records filenames, byte sizes and hashes, and lists archive member names without extracting or deleting the original archives. It does **not** claim that local hashes establish completeness against Kaggle's listing. Capture the Data-page file list alongside the receipts for that comparison.

For an already authenticated Kaggle CLI, the official read-only listing command is:

```bash
kaggle competitions files kaggriculture --page-size 200 --csv
```

Follow a returned page token if present; one page is not automatically a complete listing. The CLI can also download files directly to this private folder. This package does not install or upgrade the CLI in your research environment, and browser upload avoids needing to alter it.

The saved-evidence notebook can run without a raw archive because it does not start games or read a competition data kit. Raw assets remain an explicitly separate, potentially unresolved readiness item.

## 6. Verify readiness, then use the notebook

Run:

```bash
cd /home/sagemaker-user/kaggriculture_manual_resume
python3 resume.py audit
```

Expected success: **`READINESS_PASSED`**. This means the reviewed source, pinned runtime receipt and ten private objects are verified for **zero-game feature-evidence review**. It does not authorize an expensive study or assert complete official-data coverage.

In JupyterLab:

1. Open `kaggriculture_manual_resume/05_workspace_feature_readiness.ipynb`.
2. Select **Kernel → Change Kernel → Kaggriculture Manual (verified source)**.
3. Choose **Run → Run All Cells**.
4. Check that the first output says **WORKSPACE-VERIFIED MODE**, not reference-only mode.

The notebook displays the preserved staffing failure, the 39-feature bottleneck audit, the confirmed workforce-size coverage gap, checkpoint/data readiness and a five-round feature research agenda. Plotly figures and an HTML dashboard are saved under this package's `outputs/` directory. It performs no simulations or fitting and never overwrites notebooks 00–04 or their publication evidence.

The notebook shipped here was executed in **REFERENCE-ONLY MODE** in the assistant's local environment using the retrieved report fields. Those visible charts are genuine renderings of saved results, not an assertion that your AWS setup steps have already passed. A local execution receipt records that distinction.

**Do not run the README's entire historical reproduction command list or `scripts/execute_notebooks.py` as a setup check.** Those commands have a larger scope and may rebuild historical evidence or run complete studies.

## 7. Save the evidence and stop compute

Run:

```bash
cd /home/sagemaker-user/kaggriculture_manual_resume
python3 resume.py bundle
```

In the file browser, right-click **`kaggriculture_readiness_receipts.zip`** and download it. This private diagnostic ZIP includes JSON receipts and structured events, not raw game trajectories or credentials. Some paths and infrastructure identifiers are included; do not commit it publicly by default.

Return to Studio and choose **Stop space** for `kaggriculture-dev` (or stop the app from Running instances). **Do not choose Delete space.** An idle timeout is not a spending cap; closing a browser tab is not the shutdown procedure. Storage and requests can still incur charges after compute is stopped.

## Troubleshooting: stop at the first failed gate

**`main` moved:** the kit refuses to execute against an unreviewed revision. Keep both checkouts and the error receipt. A new review must cover that SHA; do not reset the old repository.

**No old Python or incompatible runtime:** the source clone remains preserved. Build an isolated environment only in the new checkout. Check that `uv` is available, then use the repository lockfile:

```bash
(
set -e
cd /home/sagemaker-user/projects/kaggriculture-manual
export PATH="$HOME/.local/bin:$PATH"
command -v uv
# A missing uv executable or a linked environment stops this block.
test ! -L .venv
# Only this NEW checkout may receive an environment installation.
timeout --signal=TERM --kill-after=5s 600s uv sync --frozen --python 3.12
cd /home/sagemaker-user/kaggriculture_manual_resume
python3 resume.py prepare
)
```

This is a separate bounded dependency-installation stage, not part of the default no-install path. `uv` should create the new checkout's `.venv`. If `uv` is unavailable, a package version is unavailable, disk is low or the install fails, stop and keep the actual error; do not repeatedly retry or upgrade the old environment. A timeout does not erase valid existing files.

**Hash/version mismatch:** keep the mismatching file/partial and the receipt. The script deliberately does not overwrite the only evidence of a discrepancy.

**Notebook in reference mode:** setup has not produced a valid `state/readiness.json` beside this notebook. Do not treat the packaged charts as proof of AWS readiness.

**Plots do not render:** the notebook also writes a standalone HTML dashboard in `outputs/`; download and open it locally. No external CDN is needed in the combined dashboard.

## What this package does NOT do

It does not launch AWS compute, change IAM, reset the original checkout, push/merge to GitHub, promote a policy, run new games, complete the halted staffing pilot, generate a submission or claim a leaderboard improvement. It prepares the evidence and environment for the next bounded feature milestone. New deliverables in this ZIP are **not yet committed or merged**; existing repository work through PR #15 is merged.

## Sources

- Reviewed main: https://github.com/alvaromendizabal/kaggriculture/commit/7194116dfc92a8663139611233b5a221dad431a4
- Main Quality: https://github.com/alvaromendizabal/kaggriculture/actions/runs/34641284139
- Staffing findings: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/docs/staffing_findings.md
- Workforce proof: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/reports/workforce_scope_audit.json
- Bottleneck report: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/reports/bottleneck_research.json
- AWS stop/delete behavior: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-running-stop.html
- AWS space configuration: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-jl-user-guide-configure-space.html
- AWS lifecycle configurations: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-lifecycle-configurations.html
- Official CLI: https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md
- uv synchronization: https://docs.astral.sh/uv/concepts/projects/sync/
- Competition Data: https://www.kaggle.com/competitions/kaggriculture/data

The competition Data/leaderboard pages did not expose readable file/rating content to the web tool. The value **3140.0** remains the user's supplied research target, not an independently verified current leaderboard value.
