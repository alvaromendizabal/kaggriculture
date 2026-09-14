# Reproduce and inspect

## Read-only review

Open `notebooks/00_research_overview.ipynb` from a clean kernel with pandas and Plotly.
It reads the committed aggregate CSVs, displays six figures inline, and writes
`docs/research/index.html`. Save and reopen the notebook to inspect persistent outputs.
The generated HTML contains Plotly JavaScript and works when downloaded and opened
locally. GitHub's normal notebook viewer is static; use configured GitHub Pages or a
local browser for interactivity. No rendering service is silently enabled.

## Research execution

The established runtime uses Python 3.12 and the recorded pinned Kaggle engine.
Manual research packages were executed from `/home/sagemaker-user/<package>/` and
read a verified checkout at `/home/sagemaker-user/projects/kaggriculture-manual`.
The additive copies under `research/manual/` preserve that source and its known
artifact expectations. They are not portable full-data bundles.

Do not run historical notebooks as an installation or publication test. Read their
prerequisites and use their documented kernel and data receipts. The new outcome
notebooks reuse the completed service-value screens and execute only one matched
block per family. They do not install dependencies, manage AWS, or publish to GitHub.

## Public publication

The owner prepares a linked Git worktree for the **same public repository**, reviews
its exact files, commits and pushes a branch, then merges through a pull request.
Original source checkouts and runtime artifacts remain untouched during preparation.
After merge, a fail-closed fast-forward checks that the recorded source contract is
unchanged and that remote main contains the approved publication bytes.

Archived standalone test suites keep their package-specific commands; archive-only
pytest discovery is isolated to avoid cross-importing same-named historical modules.
The root baseline test suite is not disabled or changed.

Existing source, historical notes, and licensing remain in Git history. This release
is additive except for a new landing-page README; the preceding README is retained
under `docs/archive/`. Source copied from a manually edited workspace is not silently
substituted into the core baseline.

Primary platform references:
- https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files
- https://git-scm.com/docs/git-worktree
- https://git-scm.com/docs/git-bundle
