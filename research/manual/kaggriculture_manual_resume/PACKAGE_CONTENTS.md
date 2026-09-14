# Package contents and verification scope

| File | Purpose |
|---|---|
| `START_HERE.md` | Exact AWS, upload, terminal, raw-data, notebook and shutdown steps |
| `resume.py` | Bounded non-destructive source preparation, runtime binding, S3 restore and evidence receipts |
| `tests/test_resume.py` | 26 local tests; uses a temporary Git repository and mocked S3, not paid cloud execution |
| `05_workspace_feature_readiness.ipynb` | Eight genuinely executed code cells; four Plotly figures; reference-only execution is explicitly marked |
| `FEATURE_RESEARCH_PLAN.md` | Five prioritized investigation rounds with information contracts and stop/retain gates |
| `research_rounds.json` | Machine-readable research agenda used by the notebook |
| `staffing_manifest.json` | Seven private episode references plus three receipts, with exact S3 versions, sizes and hashes; no raw data or credentials |
| `verified_evidence.json` | Selected fields from connected GitHub/AWS reads; unresolved facts identified |
| `VALIDATION_REPORT.json` | Actual local test, notebook execution and limitation report |
| `outputs/feature_readiness_dashboard.html` | Self-contained reference-mode dashboard |
| `outputs/notebook_execution.json` | Execution mode and dashboard hash |
| `CHECKSUMS.sha256` | Package-file checksums before user execution |

The bundle contains no Kaggle data-kit redistribution, no game trajectories, no credentials, and no model weights. Restore calls fetch the user's own seven private episode files from S3 when the user runs the workflow.

Generated `state/` receipts and any subsequent notebook outputs belong to the user's manual execution. This ZIP does not say that AWS has already run the new code. New recovery code has not been committed, pushed, merged or tested in GitHub CI. The existing repository's main-CI result applies to reviewed main, not to this new ZIP.

To check the original package bytes before running the notebook, use `sha256sum -c CHECKSUMS.sha256` from the package directory. The notebook and its output hashes will legitimately change when it is executed again; preserve the resulting execution receipt rather than expecting pre-execution checksums to stay the same.
