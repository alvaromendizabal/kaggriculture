# Kaggriculture — competitive agent research

**Alvaro Mendizabal · Simulation agents · Controlled ablations · Current-meta validation · Reproducible evidence**

A notebook-first research project for Kaggle's Kaggriculture environment. The work connects full-season production, worker allocation, inventory flow, market timing, replay analysis, and controlled opponent leagues to explicit policy hypotheses.

## Competitive checkpoint

The latest verified full leaderboard export captured at **2026-09-23T00:55:21Z** contained 9,875 ranked rows.

| Measurement | Verified value |
|---|---:|
| Strongest current submission | **2047.9** |
| Verified rank | **1621** |
| Second current submission | **2044.9** |
| Observed rank-one rating | **3152.6** |
| Remaining gap | **1104.7** |

The project's **3700** target is a stretch research target, not a claim about the current leaderboard. Ratings are dynamic; the table is a dated checkpoint.

## Latest conclusion

The project has reached a ceiling for recent micro-intervention work, not a proven permanent performance ceiling.

The exact Boatlee V16-RC5 public controller was reproduced as a hash-bound reference and tested on 64 direct games against the two current submission sources. It lost **0–32 against each source** and was rejected before the broader field stage. No submission was made.

Other recent directions were also stopped by prospective gates: terminal crew planning, adjacent-sale action learning, service-route synthesis, crop programs, and route-population routing. Negative results remain part of the research record.

The next ceiling-escape milestone is **incremental current-data refresh + recent full-season route/task-graph synthesis + a broader current-meta veto league**. Historical replay data is reused; only missing/changed recent data should be fetched.

## Start with the evidence

| Entry point | Evidence |
|---|---|
| [Research overview](notebooks/00_research_overview.ipynb) | earlier research story and inline Plotly evidence |
| [Public reference benchmark](notebooks/47_frozen_public_reference_benchmark.ipynb) | controlled reference screening |
| [Timing confirmation](notebooks/48_frozen_timing_reference_confirmation.ipynb) | independent confirmation and export checks |
| [Live feedback + incremental data](notebooks/49_live_submission_feedback_and_incremental_data.ipynb) | live feedback and delta-data pipeline |
| [Terminal planner](notebooks/50_terminal_crew_route_market_planning.ipynb) | rejected joint crew/route/market hypothesis |
| [Counterfactual market learning](notebooks/51_counterfactual_market_action_learning.ipynb) | recent-data model training and validation rejection |
| [Full-season production summary](docs/research/full_season_production_frontier_summary.md) | compact public summary; full output-heavy notebook retained in AWS |
| [Public frontier reproduction](notebooks/53_public_frontier_reproduction_and_league.ipynb) | exact V16 reproduction and decisive rejection |
| [Ceiling-escape review](docs/research/ceiling_escape_2026-09-22.md) | current gap and next structural capability |
| [Leading-solution matrix](docs/research/leading_solution_reproduction_matrix.md) | reproduced, adapted, rejected, and missing mechanisms |
| [Outcome ledger](docs/research/latest_outcomes.md) | compact chronology of evidence |

## Research standard

Experiments are staged and self-gating: source/data integrity → engine checks → smoke tests → development screening → frozen confirmation → broader veto league → manual submission review.

Local coins, local win rate, historical public scores, and Kaggle rating are kept separate. A candidate is not promoted because it looks good in one matchup or resembles an old high-rated public bot.

## Data and privacy boundary

AWS is the canonical research workspace. The compact replay warehouse currently reaches **2026-09-20**; the last verified official index reached **2026-09-21**, so current-meta research requires an incremental delta refresh rather than a historical re-download.

This public repository intentionally excludes raw episode archives, private replay corpora, credentials, environments, private checkpoints, large generated artifacts, and uncleared third-party controller source.

## Current research question

**Can recent top-agent episodes support a compatible full-season policy family that beats both current submission sources on disjoint both-seat confirmation seeds and survives a broader current-meta opponent league?**
