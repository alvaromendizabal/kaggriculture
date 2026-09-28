# Kaggriculture — competitive agent research

**Alvaro Mendizabal · Multi-agent simulation · Controlled ablations · AWS/SageMaker · Reproducible validation**

A notebook-first research project for Kaggle's Kaggriculture environment. The work spans full-season production planning, labor allocation, inventory and market timing, public-opponent reproduction, official-engine simulation, recent-episode data engineering, staged promotion gates, and live submission feedback.

## Competitive checkpoint

Latest authenticated active-slot snapshot in the published evidence: **2026-09-28T05:21:12Z**.

| Measurement | Verified value |
|---|---:|
| Active scoring submission · race-up | **1760.7** (`56511669`) |
| Active scoring submission · labor | **1712.2** (`56598411`) |
| Strongest historical returned submission | **2048.7** — frozen timing reference |
| Stretch target | **3400** |

A leaderboard-page snapshot captured at **2026-09-28T05:10:10Z** showed **3034.4** for the highest returned entry on that page. Because the leaderboard and active-submission snapshots have different timestamps and the leaderboard export was paginated, this repository does **not** present a synchronized rank-one gap from those values.

The competition's scoring rule means only the latest two accepted submissions are treated as the active scoring pair in this research workflow. Historical stronger bots remain benchmarks, not active-slot substitutes.

## Latest research frontier

Since the previous public checkpoint, the project completed **4,352 accepted official-engine games** across new playable-agent studies and **28 small model fits**. The main result is a clearer separation between predictive models, narrow decision overlays, and full-controller strength.

### 1. Recent-data pipeline + auxiliary forecasting

A public-state opponent cash-change model was trained from recent replay data using chronological and family-aware holdouts. It reduced final-date mean absolute error by approximately **26%** versus a persistence baseline, and the frozen model retained approximately the same relative error reduction on **64 later ladder games** from the two active submissions.

That result was useful but intentionally **not** treated as a playable-agent improvement. The repository separates forecasting quality from win/tie performance.

### 2. Playable learned-supply intervention

The learned supply-execution policy produced a strong development screen (**91.67%** family-weighted win/tie score versus **79.17%** for labor), then weakened on independent confirmation (**74.31%** versus **71.18%**). The gain did not clear the registered uncertainty and withheld-opponent gates, so the candidate was rejected.

### 3. Whole-order queue planning

A market-order scheduler was verified against the official mechanics, then failed competitively: **60.71%** versus **80.36%** for labor on its screen. The direction was closed rather than tuned further against the same panel.

### 4. Contextual production-program selection

A contextual selector over an existing production-program bank completed **1,536 games and 20 fits**. It reached **81.67%** versus **80.0%** for labor in confirmation—a small, non-decisive gain—and was rejected.

### 5. Whole-controller reference

The strongest recent fixed-panel result came from an **externally authored, attributed public controller** tested unchanged. It scored **94.44%** family-weighted win/tie versus **85.42%** for labor across 320 confirmation games per policy, a **+9.03 percentage-point** gain. The paired seed-level interval still crossed zero, so it was **not promoted** under the registered gates.

A project-authored learned add-on reduced that reference's screen score and was dropped. The current registered next step is one larger fresh-seed replication of the unchanged reference before any release decision.

## Start with the evidence

| Entry point | Evidence |
|---|---|
| [Recent meta/frontier notebook](notebooks/55_recent_meta_frontier.ipynb) | executed summary of the data refresh, forecasting transfer, playable experiments, and current controller frontier |
| [Recent research memo](docs/research/recent_meta_frontier_2026-09-28.md) | technical narrative, validation design, public/private boundary, and next registered step |
| [Outcome ledger](docs/research/latest_outcomes.md) | chronology of accepted and rejected directions |
| [Leading-solution matrix](docs/research/leading_solution_reproduction_matrix.md) | reproduced, adapted, rejected, promising, and still-missing mechanisms |
| [Machine-readable frontier](reports/recent_meta_frontier.json) | aggregate experiment evidence without competitive implementation details |
| [Prior validation-gap notebook](notebooks/54_labor_treasury_confirmation_and_live_gap.ipynb) | earlier labor intervention and initial live-feedback checkpoint |

## Research standard

Experiments are self-gating:

**source/data integrity → engine checks → smoke tests → representative screen → independent confirmation → held-out/family-aware checks → deterministic packaging → terminal-originated submission**

The project deliberately keeps separate:

- public-state predictive accuracy,
- local coins and margins,
- official-engine win/tie rate,
- source-family ancestry and duplicate risk,
- live Kaggle rating.

Negative results remain in the record. A candidate is not promoted merely because it wins a familiar matchup, improves a development screen, or looks strong under an auxiliary forecast.

## Engineering approach

The canonical workspace is AWS/SageMaker. Recent campaigns use:

- `ml.m7i.12xlarge` CPU simulation;
- up to 24 concurrent official-engine games under resource gates;
- isolated agent processes and callback-parity checks;
- source/archive SHA-256 binding;
- checkpointed, restartable game evaluation;
- paced external acquisition with bounded backoff;
- chronological / source-family-aware data splits;
- bounded runtime, memory, disk, and temporary-storage guards;
- deterministic return bundles and submission archives;
- terminal-originated Kaggle submissions from AWS with upload-intent / duplicate protection.

GitHub is a curated engineering/research surface, **not** a mirror of the AWS filesystem.

## Current research question

**Does the strongest newly acquired whole-controller reference retain its broad fixed-panel advantage under a larger, fresh-seed replication?**

A pass permits one gated terminal submission. A failure closes that reference without automatically expanding the sample or relaxing thresholds.

## Semi-reproducibility and competitive boundary

The public repository exposes enough to evaluate the research process: experiment designs, aggregate outcomes, evaluation methodology, engine/version context, active-slot handling, failure analysis, and reproducible notebooks over published summary data.

It intentionally excludes the pieces that would publish the competition implementation itself:

- raw episode corpora and private replay mirrors;
- acquired third-party controller source;
- exact policy thresholds, route tables, action tapes, and fitted coefficients;
- private AWS caches/checkpoints and per-game action traces;
- credentials and submission tarballs.

Third-party licenses and attribution notices remain authoritative for any externally authored reference evaluated in the private research workspace.
