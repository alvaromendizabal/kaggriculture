# Kaggriculture — two outcome rounds and one public repository

## Decision
Keep `alvaromendizabal/kaggriculture` public. Do not create another repository,
change visibility, erase history, or follow the superseded source-separation plan.
All research implementation and appropriate notebooks/reports are intended for the
existing public repository. Credentials, runtime environments, raw competition
archives and large episode/checkpoint payloads remain out of Git.

The previous package was not run. There are no round-21/22 outcomes to assume or
undo. This package preserves those two rounds and replaces the publishing workflow.

## Workspace
Use the existing `kaggriculture-dev` JupyterLab space in us-west-2:
Studio -> `QuickSetupDomain-20260902T115323` ->
`default-20260902T115323` -> JupyterLab -> `kaggriculture-dev`.
Keep the working image/storage/kernel and leave old research lifecycle scripts off.
No GPU upgrade, reinstall, raw-data download or destructive Git reset is required.

Upload `kaggriculture_public_release.zip` into `/home/sagemaker-user` and extract it
only if `/home/sagemaker-user/kaggriculture_public_release` does not exist. Validate
archive paths as shown in the response. Do not extract over an existing folder.

## A. Execute the two pending research rounds

Open `research/21_collection_completion_outcome.ipynb` in the extracted folder.
Select **Kaggriculture Manual (verified source)**, restart its kernel and Run All.
Save it. After a normal result, do the same for
`research/22_maintenance_deadline_outcome.ipynb`. Do not run concurrently.

Each notebook verifies the exact completed service-value screen and its original
source. Each runs 64 existing family checks and 16 new diagnostic checks. It then
constructs 12 new diagnostic descriptors without modifying the screened actor,
and runs only registered block b1. The two independent candidates use the same
control, which is reused if compatible: at most three new complete games total.

The control/candidate pair has a 180-second supervised worker budget, 8 GiB worker
RSS limit, and 500 ms measured callback gate. The wrapper's emergency deadline is
195 seconds. Tests have separate 45/30-second limits; diagnostic feature construction
has a 30-second bound. Existing heartbeat and per-game checkpoints are retained.
Actual runtime/cost is unmeasured. At an illustrative $1/hour, the two 180-second
worker budgets total $0.10, excluding startup, tests, publication, storage and idle
compute. This is not a quote of the current AWS instance price.

Expected evidence markers: `REVIEWED_SCREENS_VERIFIED`,
`RELATIVE_FEATURE_ANALYSIS_COMPLETE`, `PAIRED_BLOCK_COMPLETE`,
`ONE_PAIRED_BLOCK_COMPLETE`, and `ROUND_OUTCOME_REVIEW_COMPLETE`.
A normal negative endpoint is a completed research result, not a software exception.
A source, input, runtime or test error means stop and bundle before doing more work.
Do not start b2-b4. Close/reopen saved notebooks and confirm their charts persist.

## B. Inventory and assemble the public branch

In JupyterLab File -> New -> Terminal:

```bash
cd /home/sagemaker-user/kaggriculture_public_release
python3 -m unittest discover -s publication/tests -v && \
python3 publication/publish.py inspect
```

The suite contains 24 supplied publication-safety tests. They have not been run by
the assistant. Proceed only when your run passes and prints `LOCAL_INVENTORY_READY`.
Read `release_state/inventory.json`, including missing older packages, excluded paths,
and saved notebook states. A missing package is not certified as published. A reported
uncommitted core-code change needs explicit reconciliation; it is not thrown away.

Then:

```bash
python3 publication/publish.py prepare
```

This is a user-initiated Git read/fetch and LOCAL copy operation. It verifies the
origin is exactly the existing repository, fetches current main, checks compatibility
with the recorded baseline, makes verified local Git bundles and diff backups, and
creates the `publication/manual-research-21-22` branch in a linked working tree:

`/home/sagemaker-user/projects/kaggriculture-publish`

A linked worktree is another directory for the SAME repository, not another GitHub
repository. The original research checkout remains untouched until the later sync.
Prepare never commits, pushes, changes permissions or runs research. Allow up to
90 seconds per remote-fetch or Git-bundle operation; copy size is capped at 500 MiB
and 25 MiB per reviewed file. A different preexisting destination is preserved and
causes a stop. Backups remain outside the public tree; bundles are not raw-data backups.

Source snapshots go under `research/manual/<original-package-name>/`. Existing
notebook outputs are preserved as evidence and indexed honestly; incomplete notebooks
are not silently relabeled completed. Only selected aggregate reports/dashboards
are copied from output directories. Old source, tests and license notices are retained.
The root README becomes an employer-facing entry page; its predecessor is retained
under `docs/archive/`. Root core source/configuration are not overwritten by older
AWS copies. Unknown/local unmerged core code needs review, not automatic promotion.

## C. Render the employer-facing overview and approve the exact files

Open, in the publication worktree:

`notebooks/00_research_overview.ipynb`

Use the verified kernel, restart, Run All, save and reopen it. It reads aggregate
results only and writes six inline figures plus `docs/research/index.html`.
It does not execute a simulator. Expected marker: `PUBLIC_OVERVIEW_RENDERED`.

Then, back in the original release-package terminal:

```bash
cd /home/sagemaker-user/kaggriculture_public_release
python3 publication/publish.py check
```

Only after `PUBLICATION_CHECKS_PASSED`, inspect the actual files in
`projects/kaggriculture-publish`. Review code, notebooks, reports, license notices,
and the staged landing-page narrative. The scanner is limited; it does not clear
historical commits or guarantee all credentials are detected. It does not delete
or rewrite history. A real exposed credential must be revoked/rotated before any
attempt at history cleanup.

After approving publication of the research source and outputs:

```bash
python3 publication/publish.py seal --acknowledge PUBLISH_RESEARCH_SOURCE
python3 publication/publish.py stage
```

Expected markers: `PUBLIC_SOURCE_APPROVED`, then `READY_TO_COMMIT`.
Only manifest-listed, byte-checked paths are staged. The helper may force-add
INDIVIDUAL approved reports ignored by historical .gitignore files; it never uses
`git add -A`, never stages raw-data globs, and never force-pushes.
No research-performance claim is created by these publication checks.

## D. Commit, push and merge

Follow `publication/GIT_WORKFLOW.md`. The complete commands are supplied there:
existing/public repo verification, optional browser-based GitHub CLI authentication,
staged-diff review, local commit, branch push, PR creation, CI/Files-changed review,
manual merge, and post-merge verification. Nothing is run by the assistant.
Do not bypass a failing check or merge a PR merely because it exists.

## E. Fast-forward AWS after merge

After GitHub confirms that the PR was merged:

```bash
cd /home/sagemaker-user/kaggriculture_public_release
python3 publication/publish.py sync
```

This checks the exact published bytes on current remote main, checks that the active
checkout is clean and can fast-forward, and verifies all protected core/receipt files
are unchanged. It then fast-forwards `projects/kaggriculture-manual` without touching
raw data, environments, package working folders or the old original checkout.

Expected marker: `AWS_CODE_MATCHES_REMOTE_MAIN <actual-full-commit>`.
A failure is a review point; never replace it with reset/clean/force. The original
`projects/kaggriculture` is intentionally preserved as the recovery copy; the sync
certificate applies to the active manual checkout, not every directory on disk.

## F. Return artifacts and stop compute

```bash
cd /home/sagemaker-user/kaggriculture_public_release
python3 publication/publish.py bundle
```

Download `/home/sagemaker-user/kaggriculture_public_release_results.zip` and return
it with the PR URL. The bundle includes both saved research notebooks, available
outcome measurements, publication receipts and sync result. It also works after
an error. It does not include local Git bundles, credentials or raw source episodes.

Finally stop the JupyterLab APPLICATION in Studio -> Running instances. Do not
delete the space. A notebook timeout or closed browser does not stop AWS billing.

## Evidence boundaries
No new project code, tests, notebooks, charts or experiments were executed by the
assistant during this preparation. Only source/static structure and artifact bytes
were inspected. The latest supplied screen reports do not include a submission
score. Neither visibility nor remote main has been independently inspected in the
user's account; the commands you run establish those states.
