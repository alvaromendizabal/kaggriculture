# Kaggriculture — agent evaluation under changing opponents

**Alvaro Mendizabal · Sequential decision-making · Simulation · Experimental design · AWS/SageMaker**

A research project for Kaggle's competitive farming simulation: build legal-observation
agents, reproduce reference controllers, and test whether policy changes survive realistic
opponents. The strongest contribution is the evaluation system and the decision to correct
it when strong local results failed to transfer to the leaderboard.

**Start with the [executed portfolio notebook](notebooks/57_portfolio_review.ipynb)** for
results, charts, and a small runnable evaluation example. The
[case study](CASE_STUDY.md) explains the engineering decisions; the
[reviewer guide](docs/REVIEWER_GUIDE.md) maps claims to evidence.

## What the work established

- **Detected a validation mismatch.** The incumbent appeared nearly perfect against a fixed
  local panel. Exact reconstruction of 48 recent ladder episodes instead measured
  **18 wins / 10 ties / 20 losses: 47.9% win/tie score**.
- **Tested transfer rather than assuming it.** Historical controller ablations, whole-route
  transfer, public adaptive agents, and learned intervention rules failed their registered
  gates. Their negative results remain in the record.
- **Preserved expensive evidence.** A rolling chronological analysis reused **1,084** accepted
  branch/calibration results without replaying games.
- **Separated reliability from modeling.** A harvest/service experiment failed during
  post-game diagnostics. It is recorded as an execution failure, with no claim that its
  policy succeeded or failed scientifically.

## Competitive evidence — historical snapshot

These are the recorded September 30, 2026 results, **not live leaderboard readings**.

| Measurement | Recorded result | Interpretation |
|---|---:|---|
| Strongest historical returned submission | **2048.7** | Earlier reference; outside the snapshot's latest-two scoring pair |
| Keeper in the latest-two pair | **1691.0** | Submission `56656845` |
| Other submission in that pair | **1516.2** | Submission `56598411` |
| Highest returned leaderboard row | **3084.1** | Paginated export; not verified as exhaustive rank one |
| Keeper gap to that returned row | **1393.1** | Same snapshot; no claim that the gap has since closed |

Official ratings, local win/tie scores, and auxiliary forecast errors measure different
things. The corrected evaluator strengthens the evidence; it does not establish a new
competitive best. See the [outcome ledger](docs/research/latest_outcomes.md) and
[machine-readable sprint report](reports/final_sprint_2026-09-30.json).

## My contribution and the reference boundary

Project-authored work includes observation-safety checks, paired candidate comparisons,
chronological evaluation, counterfactual intervention research, restartable experiment
infrastructure, artifact provenance, and promotion/release controls. External controllers
are attributed in the [leading-solution matrix](docs/research/leading_solution_reproduction_matrix.md).
Reproducing a reference's inference behavior does not reproduce its author's private
training process, establish original authorship, or guarantee its historical score transfers.

AWS/SageMaker is the canonical research environment. Published records describe CPU
simulation, isolated agent processes, bounded runs, reusable game checkpoints, source hashes,
and duplicate-submission protection. This repository review does not require an AWS account.

## Reproduce the review surface

For an authorized clone, use Python 3.12 and install the committed environment with
`uv sync --frozen`. Then run the bounded checks below from the repository root.

```bash
uv run pytest -q tests/test_final_sprint.py
uv run python scripts/verify_final_sprint.py
python3 scripts/verify_portfolio_review.py
python3 examples/run_demo.py
```

These commands check aggregate evidence and demonstrate paired evaluation on synthetic
outcomes. They do not launch competitive games, train a model, or submit to Kaggle.
The existing full CI suite also runs small official-engine foundation tests; it is broader
than this review path. See [reproducibility scope](docs/REPRODUCIBILITY.md) and the
[example guide](examples/README.md).

## Research status and limitations

The latest recorded native harvest/service attempt ended in a diagnostics transport error;
its repaired runner was prepared, but the report contains **no completed competitive rerun**.
Recent replay tapes cannot react to changed actions, so responsive-opponent safety remains a
separate gate. The 48-episode correction is a small, dated sample, and older promotions made
against the saturated panel require reconsideration under the revised evaluation.

The repository contains reviewable code, executed notebooks, protocols, and aggregate
results. Raw replay corpora, private checkpoints, credentials, submission archives,
third-party controller source, and the exact current competitive implementation are
excluded. **A full private competitive rerun is not available from this checkout alone.**
Repository access remains subject to its existing visibility and permissions.
