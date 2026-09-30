# Reproducing the September 29–30 final sprint

## Local clone

1. Install Python 3.12 and `uv`.
2. Run `uv sync --frozen`.
3. Run `uv run pytest -q tests/test_final_sprint.py`.
4. Run `uv run python scripts/verify_final_sprint.py`.
5. Open `notebooks/56_final_sprint_ladder_alignment.ipynb` to inspect the executed evidence summary.

These steps reproduce the public validation logic and verify the published aggregate evidence.

## Full official-engine reproduction

A full competitive rerun additionally requires:

- `kaggle-environments==1.32.7` (already pinned by `pyproject.toml`);
- authorized Kaggle competition access;
- public replay retrieval for the registered episode IDs;
- immutable public-controller acquisition where applicable;
- the same chronological splits and game seeds recorded by the protocol documents.

The public repository does not contain credentials, Kaggle tokens, private S3 mirrors, raw replay
blobs, third-party controller source, or submission tarballs. This is intentional. External
sources must be acquired from their authoritative public location and verified against the
recorded content identity before use.

## Evidence semantics

`reports/final_sprint_2026-09-30.json` contains machine-readable aggregate results extracted from
the verified return bundles. Negative scientific results are included. The native-harvest entry
is explicitly an execution failure and must not be interpreted as evidence against that policy.
