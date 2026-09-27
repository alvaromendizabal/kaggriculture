# Kaggriculture — competitive agent research

**Alvaro Mendizabal · Multi-agent simulation · Controlled ablations · AWS/SageMaker · Reproducible validation**

A notebook-first research project for Kaggle's Kaggriculture environment. The work spans full-season production planning, labor allocation, inventory and market timing, public-opponent reproduction, official-engine simulation, staged promotion gates, and live submission feedback.

## Competitive checkpoint

Latest authenticated submission history captured at **2026-09-27T05:17:23Z**:

| Measurement | Verified value |
|---|---:|
| Strongest completed returned submission | **2048.7** — frozen timing reference (`56471163`) |
| Race-up submission | **1851.5** (`56511669`) |
| Latest labor-treasury submission | **600.0** (`56598411`) |
| Stretch target | **3400** |
| Gap from strongest returned submission to 3400 | **1351.3** |

The latest campaign could not obtain a contemporaneous leaderboard table, so this repository does **not** present a current rank-one gap from mismatched timestamps. The last full leaderboard export published in this repository was captured on 2026-09-23 and is historical.

## Latest research finding

The most important result is a **local-to-live validation failure**.

A project-authored labor-funding intervention passed independent local confirmation:

- **1,440-game confirmation:** labor 86.875% win/tie score, race-up 77.708%, parent 74.167%.
- **720-game champion comparison:** labor 85.0%, race-up 75.0%, timing reference 50.83%.
- In the champion comparison, labor's +10 point gain over race-up was driven by a complete reversal against Shop Router V7 while the other matched opponent results were unchanged.
- The candidate was packaged deterministically and submitted once from the canonical SageMaker workspace.

The live Kaggle result was **600.0**, far below the 2048.7 timing reference.

That outcome invalidates treating the current static local league as a sufficient promotion instrument. The correct conclusion is not that the labor mechanism was useless: it solved the targeted local failure. The conclusion is that the evaluator did not represent the live ladder well enough.

## Start with the evidence

| Entry point | Evidence |
|---|---|
| [Latest validation-gap notebook](notebooks/54_labor_treasury_confirmation_and_live_gap.ipynb) | executed summary of local confirmation, live submission, and the resulting research decision |
| [Live validation-gap memo](docs/research/live_validation_gap_2026-09-26.md) | compact technical interpretation, provenance, and next milestone |
| [Outcome ledger](docs/research/latest_outcomes.md) | current chronology of accepted and rejected directions |
| [Leading-solution matrix](docs/research/leading_solution_reproduction_matrix.md) | reproduced, adapted, rejected, and still-missing mechanisms |
| [Research overview](notebooks/00_research_overview.ipynb) | earlier research story and inline evidence |
| [Timing confirmation](notebooks/48_frozen_timing_reference_confirmation.ipynb) | confirmation of the strongest returned live baseline |
| [Live feedback + incremental data](notebooks/49_live_submission_feedback_and_incremental_data.ipynb) | submission feedback and delta-data workflow |
| [Public frontier reproduction](notebooks/53_public_frontier_reproduction_and_league.ipynb) | controlled reproduction and rejection of a public reference |

## Research standard

Experiments are self-gating:

**source/data integrity → engine checks → smoke tests → representative screen → independent confirmation → broader veto league → deterministic packaging → manual submission review**

The project deliberately keeps separate:

- local coins and margins,
- local official-engine win/tie rate,
- historical public-agent claims,
- live Kaggle rating.

Negative results remain in the record. A candidate is not promoted merely because it wins a familiar matchup or looks strong in a static league.

## Engineering approach

The canonical workspace is AWS/SageMaker. Recent campaigns use:

- `ml.m7i.12xlarge` CPU simulation;
- up to 24 concurrent official-engine games after a measured throughput benchmark;
- isolated agent processes and callback parity checks;
- source/archive SHA-256 binding;
- checkpointed, restartable game evaluation;
- bounded runtime, memory, and storage gates;
- deterministic return bundles and submission archives;
- terminal-originated Kaggle submissions from AWS;
- public GitHub artifacts that exclude raw replay corpora, credentials, private caches, and large generated archives.

GitHub is a curated engineering/research surface, not a mirror of the AWS filesystem.

## Current research question

**What local evaluation instrument actually predicts live Kaggriculture ladder performance well enough to justify the next structural policy search?**

The next ceiling-escape milestone is validation redesign before more policy tuning:

1. refresh only new top-agent/public episode evidence;
2. expand opponent diversity and hold out opponent families;
3. measure which offline metrics correlate with live outcomes;
4. add recent-opponent robustness and distribution-shift gates;
5. resume structural on-policy strategic control / league training only after the evaluator itself earns trust.

## Data and licensing boundary

This repository intentionally excludes raw competition episode archives, private replay corpora, credentials, environments, private checkpoints, submission tarballs, and uncleared third-party controller source. Existing licenses and attribution notices remain authoritative.
