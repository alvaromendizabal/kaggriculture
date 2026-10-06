# Reproducing the September 29–30 final sprint

The sprint is a dated research record. Its aggregate verification and evaluation utilities
are reproducible from an authorized checkout; the complete private competitive pipeline is
not included. The [repository reproduction guide](../REPRODUCIBILITY.md) is the main entry point.

## Clone-time verification

Use Python 3.12 and the committed lockfile:

```bash
uv sync --frozen
uv run pytest -q tests/test_final_sprint.py
uv run python scripts/verify_final_sprint.py
python3 scripts/verify_portfolio_review.py
python3 examples/run_demo.py
```

These steps verify the published aggregate record and demonstrate paired evaluation on
synthetic outcomes. They run no competitive games and require no AWS credentials. Initial
installation downloads dependencies. Open
[notebook 56](../../notebooks/56_final_sprint_ladder_alignment.ipynb) for the executed sprint
summary and [notebook 57](../../notebooks/57_portfolio_review.ipynb) for a compact review.
Notebook 57 can be regenerated with a real Jupyter kernel using
`uv run python scripts/execute_portfolio_review.py`, followed by
`python3 scripts/verify_portfolio_review.py --notebook artifacts/portfolio-review/57_portfolio_review.ipynb`
to check the newly saved result. The default verifier path checks the canonical notebook in
`notebooks/` instead.

The normal CI suite is broader: it also executes small official-engine foundation tests.
It should not be described as a no-game check or a competitive retraining run.

## Requirements for a full competitive rerun

The [reproduction manifest](../../reports/final_sprint_reproduction_manifest.json) records
engine, environment, handoff, and return-bundle identities. A full rerun additionally needs:

- the exact keeper and candidate artifacts used in the registered comparison;
- Kaggle Environments 1.32.7 and the recorded runtime/source identities;
- authorized access to the required competition data and replay episodes;
- recorded chronological splits, seeds, and both-seat pairing;
- exact keeper replay parity before interpreting counterfactual results;
- a separate responsive-opponent safety check after chronological qualification.

The checkout does not supply every item. Raw replay blobs, private checkpoints, private
orchestration, third-party controller source, and submission archives remain outside the
repository. Public upstream references, where available, must be acquired under their
applicable terms and matched to the recorded content identities. Competition access alone
is not sufficient to regenerate the private pipeline.

## What a verification pass means

`reports/final_sprint_2026-09-30.json` records aggregate outcomes extracted from the archived
AWS return bundles. Passing repository checks establishes internal consistency, expected
decisions, and reviewable saved notebook output. It does not independently authenticate
unavailable raw bundles or regenerate their game outcomes.

Negative scientific results are retained. The native-harvest entry is an execution failure;
its prepared recovery artifact has no completed competitive result in this record. The
newest-24 holdout remained untouched after rolling boundary-rule rejection. Earlier local
panel promotions must be reconsidered in light of the subsequent validator correction.

Official ratings are dated snapshots. A new live result requires a new qualifying private
run and the applicable submission process; it is not produced by these publication checks.
