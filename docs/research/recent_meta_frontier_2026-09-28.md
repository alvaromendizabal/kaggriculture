# Recent meta refresh and controller frontier — 2026-09-28

## Scope

This memo records the Kaggriculture research completed after the prior public checkpoint. AWS/SageMaker remains the canonical execution environment; the public repository contains aggregate evidence and semi-reproducible analysis rather than raw competition assets or the competitive controller implementation.

The period added **4,352 accepted official-engine games** across completed playable-agent studies and **28 small model fits**. No automatic submission occurred in these studies.

## Data and forecasting layer

The recent-data pipeline moved from a 128-episode sampled corpus to a larger replay set assembled from recent public episodes, active-submission ladder games, and previously mirrored data. Requests were content-addressed and mirrored privately; repeated acquisition was avoided through checkpoint reuse.

A 69-feature public-state cash-change model was trained with chronological and source-family-aware evaluation. On the final-date test it achieved MAE 1268.98 versus 1714.86 for a persistence baseline, a **26.0% relative reduction**. The frozen model then achieved MAE 1527.54 versus 2063.93 over 64 later games from the active submissions, again approximately **26.0% lower**.

The forecast therefore transferred as an auxiliary model. It was not presented as a submission agent and did not receive competitive credit without game-level evidence.

## Playable policy studies

### Learned supply execution

The first playable use of the forecast appended a bounded premium-product execution decision to the existing labor controller. It screened strongly (91.67% versus 79.17% for labor) but reached only 74.31% versus 71.18% for labor on the larger confirmation panel. The +3.125 percentage-point gain did not clear the registered uncertainty and withheld-opponent gates.

**Decision: rejected.**

### Whole-order queue planning

A subsequent experiment moved upstream from an appended sale to the ordering of the controller's existing market operations. The market settlement model was checked against the official engine before the game screen. The candidate then regressed to 60.71% versus 80.36% for labor.

**Decision: rejected and closed without threshold tuning.**

### Contextual production-program commitment

The next study moved from market overlays to a higher-level production decision. A contextual selector chose among an existing program bank using public state at a fixed decision point. The experiment completed 1,536 games and 20 small tree fits. Confirmation reached 81.67% versus 80.0% for labor: directionally positive but too small and too concentrated to satisfy the promotion gates.

**Decision: rejected.**

### Whole-controller reference

The strongest recent fixed-panel result came from evaluating an acquired, attributed public controller as a complete policy rather than borrowing another isolated mechanism. The unchanged reference passed its screen and then reached 94.44% family-weighted win/tie versus 85.42% for labor over 320 confirmation games per policy. The gain was +9.03 percentage points, but the paired seed-level 95% interval was approximately **−0.69 to +18.75 points**. External-opponent and held-out subsets were directionally positive but also not decisive.

A project-authored learned-supply add-on scored below the unchanged reference on the screen and was dropped, which prevents external controller strength from being incorrectly credited to the learned overlay.

**Decision: promising but rejected under the registered uncertainty gate. A single larger fresh-seed replication is the next registered test.**

## Validation changes that mattered

Several methodological changes were retained after failure analysis:

- latest-two accepted submissions are handled explicitly as the active scoring pair;
- historical high-rated submissions remain benchmarks but do not overwrite active-slot accounting;
- near-clone public sources are grouped rather than treated as independent opponent families;
- development screens cannot substitute for independent confirmation;
- paired seed-level uncertainty is required for promotion;
- a good auxiliary forecast cannot substitute for game-level gains;
- rejected experiments are closed rather than repeatedly tuned against the same panel;
- restartable, source-bound checkpoints preserve completed games without relabeling old outcomes as new evidence.

## Reliability engineering

The same period exposed and fixed several non-scientific blockers: CSV parsing of CLI hints, rate-limited burst acquisition, null actions in replay labels, malformed market-verification input, and persistent-disk pressure. These were treated as execution failures, not as negative model results.

The current replication package keeps temporary verbose work off the constrained persistent volume, preserves durable compressed checkpoints, and prevents duplicate uploads through an intent journal.

## Semi-reproducibility boundary

Published artifacts retain:

- official-engine evaluation sizes and split logic;
- aggregate win/tie scores and uncertainty decisions;
- active submission references and dated rating snapshots;
- public-state forecasting metrics;
- source-family / holdout methodology;
- execution environment and restart strategy.

The repository withholds:

- raw replays and private S3 mirrors;
- acquired controller implementation;
- exact policy thresholds, action tapes, route tables, program contents, and fitted coefficients;
- private checkpoints and per-game action traces;
- submission archives and credentials.

This boundary keeps the portfolio reviewable without publishing a turnkey competition solution.

## Current registered next step

Run one storage-safe independent replication of the unchanged attributed whole-controller reference using 32 fresh seed groups, ten opponents, and both positions. Do not pool the previous rejected confirmation into the new verdict. If the fixed gates pass, one authorized terminal submission is permitted; otherwise the reference is closed without automatic sample expansion.
