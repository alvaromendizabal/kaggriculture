# Findings from the first crop-feature experiment

The full scheduler won 16/16 development games and averaged 34,584.6 banked coins. Removing
labor features reduced its local match score to 0.75. The other three ablations also won
16/16: this opponent suite is too easy to establish their value on the primary win/tie metric.
Coin gains are useful diagnostics, not official Kaggle ratings.

## Paired evidence

Each difference is full minus ablated, pairing the same seed, opponent and seat. Intervals
are descriptive 95% percentile bootstrap intervals over four entire seed clusters.

| Removed family | Mean coin difference | Descriptive interval | Local match-score difference |
|---|---:|---:|---:|
| Crop value | +23,457.7 | +20,968.9 to +26,012.0 | 0.00 |
| Water urgency | +742.2 | −789.1 to +2,653.2 | 0.00 |
| Labor | +27,499.1 | +24,659.8 to +31,303.9 | +0.25 |
| Terminal banking | +4,926.0 | +3,990.6 to +5,950.9 | 0.00 |

Crop choice and labor allocation have large effects within this fixed scaffold. Terminal
planning has a smaller, consistently positive coin difference across these development
seed clusters. Water urgency is unresolved: the full policy loses about 1,194 coins on seed
1103 after averaging both seats and opponents. Its interval crosses zero, so a blanket
improvement claim would be unjustified.

The labor intervention combines hiring and distance weighting. This batch does not identify
which component causes how much of its effect. All effects are conditional on fixed scheduler
rules and weights. There was no coefficient tuning after inspecting comparative results.

## What the trajectories revealed

Daily irrigation alone gives 4 wheat and 3 carrot units, below their advertised caps of 6 and
4. The interpreter-parity tests verify these conditional yields. Fertilizer remains a plausible
high-value family, not an automatic multiplier applied to every crop-value estimate.

The richer trajectories reveal shed congestion that the narrow initial reference did not
exercise. Final unsold inventory misses produce discarded earlier at a deposit. The separate
[conservation audit](../reports/feature_behavior_audit.json) checks every game: harvested units
must equal sold units, held units and storage/disposal losses. It reconstructs only observable
own-farm actions and verifies sale quantities against available inventory. It does not alter
the policy or use evaluator metadata as a policy input.

Conservation passed for all 80 games. The full policy discarded **26 harvested units per
game** and reached a minimum observed cash balance of **10 coins** in every game. Its mean
harvest was 325.125 units, of which 299.125 were sold. These are concrete storage and
working-capital weaknesses despite the high local win rate. Standing crop yield is reported
separately because it includes immature produce and is not liquid cash.

The full policy's median callback time was 2.15 ms, with a 2.61 ms 95th percentile on the AWS
run. This excludes evaluator logging and is not a submitted-agent sandbox benchmark. There
were zero ineffective farm actions under the official action function in all 80 games.

## Decision for the next bounded milestone

Keep all 13 templates provisional. Prioritize storage-aware delivery, harvest congestion,
working-capital reserves and observed market pressure. Include the frozen full scheduler as
a stronger development opponent so the primary win/tie metric is less saturated. Separate
hiring from distance weighting before assigning credit to individual labor features.

Notebook 02 remains open. Livestock, fertilizer, richer market/town signals, temporal features,
stronger opponents and broader seed coverage still need study. No validation or holdout
episode has been used, no final policy selected, and no competition submission made.

Sources: [registered design](feature_experiment.md), [paired results](../reports/feature_ablations.csv),
[per-game outcomes](../reports/feature_games.csv), [executed notebook](../notebooks/02_feature_research.ipynb).
