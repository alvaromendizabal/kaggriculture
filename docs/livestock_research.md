# Study 5: livestock, feed, care and fertilizer

The registered 64-game development study is complete. Selective feeding alone
saved wheat but harmed score: daily care often occurred without the feeding needed
to bank its benefit. Adding selective care and supporting feed recovered the
losses and won all 16 matches against two fixed opponents. Conditional fertilizer
allocation increased average coin margin by 2,539.25 over care, without increasing
match score. Both arms already won every match in this limited comparison.

**Feature research remains open; final optimization is blocked.** These results
support coupled resource decisions in this fixed mixed farm. They do not establish
individual-feature predictive value, general superiority, or a Kaggle ranking.

## Registered question and scope

Study 4 left all 78 animal state/feed-care descriptors constant. This study creates
actual goose, cow and sheep trajectories and tests how survival, bonus production,
collection, wheat and fertilizer compete for labor and sale revenue. The
[protocol](livestock_protocol.md) and [registration](../reports/livestock_registration.json)
fix four development seeds (1401–1404), both seats, two opponents (`market10` and
`livestock_routine`), four arms and four contrasts: 64 full games, 719 callbacks
each. The source archive and registration reached versioned S3 before the first
registered game. Validation and holdout seeds remain untouched.

All arms use the same six-animal layout (two of each species), ten crop plots
(four wheat, three strawberry, three tomato) and at most three hired hands.

| Arm | Intervention |
|---|---|
| routine | Daily feeding and care; sell collected manure |
| feed | Select feeding to protect survival/production bonuses; retain daily care |
| care | Add valuable, convertible care and feeding that supports it |
| fertilizer | Add conditional manure allocation after transport, work and sale opportunity costs |

These are sequential conditional interventions, not factorial main effects. A
preflight fixture used seed 61, excluded from registered outcomes. No arm changed
after registration. All earlier feature/experiment sources and the five new core
source files retain their registered hashes.

## Domain mechanisms and research translation

The pinned interpreter, `kaggle-environments==1.32.7`, determines the simulated
domain. Real rainfall or soil associations have no implemented causal mechanism
here. Engine/source hashes are recorded in every episode and the
[machine-readable report](../reports/livestock_research.json).

| Mechanism | Feature or decision consequence |
|---|---|
| Two consecutive unfed refreshes cause escape; surviving unfed animals can still produce a base unit | Separate survival rescue, base production and protected care bonus |
| CARE is banked after tonight's production, only when fed | Measure conversion delay, future feeding, cap room and sale feasibility |
| Production caps can erase bonus units | Price collectable marginal output and collection urgency rather than nominal bank size |
| Manure occupies one renewable boolean slot | Collecting frees tomorrow's slot; uncollected days do not accumulate additional stock |
| Fertilizer has an inclusive activity window and crop-specific watering effects | Compare treatment/no-treatment paths with travel, displaced water, collection and terminal sale constraints |
| Feed consumes carried wheat; farm actions precede the shared market | Couple purchase/provisioning, worker routes, capital and nonlinear sale opportunity cost |

These are checked against the [official implementation](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py)
and executable parity tests. The conditional fertilizer scenario spans seven days
(168 callbacks), assumes continued water/collection service and values output at
current sale curves. Eight coins per action is a fixed opportunity-cost assumption,
not a fitted parameter. This scenario does not solve the joint workforce schedule
or forecast the market.

Inventory-routing research motivates separating exact immediate cost and feasibility
from uncertain continuation value. We implement that distinction in features,
without claiming to implement its learned hybrid optimizer.
[Hasturk et al., 2025](https://arxiv.org/abs/2503.05276).
State-dependent maintenance allocation motivates service urgency and delayed
payoff features. Shared wheat, workers and market impact violate the independence
needed for simple per-animal index optimality; no such guarantee is claimed.
[Ruiz-Hernandez et al., 2024](https://arxiv.org/abs/2401.14055).
Evaluation uses whole-seed uncertainty rather than counting correlated callbacks
as independent trials. [Agarwal et al., 2021](https://arxiv.org/abs/2108.13264).

## Outcomes and uncertainty

All entries are means over eight games per opponent/arm; there are only four
independent seed clusters. Score is 1 for a win, 0.5 for a tie and 0 for a loss.

| Opponent | Arm | Score | Own coins | Coin margin |
|---|---|---:|---:|---:|
| livestock_routine | routine | 0.500 | 41,557.25 | 0.00 |
| livestock_routine | feed | 0.000 | 37,640.25 | −5,527.25 |
| livestock_routine | care | 1.000 | 40,569.75 | 916.75 |
| livestock_routine | fertilizer | 1.000 | 43,639.50 | 2,816.25 |
| market10 | routine | 1.000 | 52,289.50 | 15,674.25 |
| market10 | feed | 1.000 | 44,992.25 | 6,700.50 |
| market10 | care | 1.000 | 51,661.75 | 13,549.75 |
| market10 | fertilizer | 1.000 | 54,620.00 | 16,728.75 |

| Registered pooled contrast | Score change | Margin change | Descriptive 95% seed-bootstrap interval for margin |
|---|---:|---:|---:|
| feed − routine | −0.25 | −7,250.50 | [−8,542.00, −5,214.75] |
| care − feed | +0.50 | +6,646.63 | [5,887.88, 7,262.00] |
| fertilizer − care | 0.00 | +2,539.25 | [1,531.25, 3,547.25] |
| fertilizer − routine | +0.25 | +1,935.38 | [257.38, 2,906.50] |

The registered bootstrap uses 4,000 resamples of four whole seed means, keeping
both seats and opponents together. Identical score contrasts across four seeds
produce degenerate score intervals; that is not zero population uncertainty.
The fertilizer-versus-routine margin was negative for seed 1403 (−601.5), despite
its positive pooled result. Fertilizer-versus-care margin was positive in all four
seed means. Four seeds, related references, multiple exploratory contrasts and a
fixed layout limit inference. The primary score is saturated for care/fertilizer.
More coins cannot establish additional ranking benefit here.

Care's own coins can decrease relative to routine while its relative performance
improves: the opponent and market are part of the outcome. The experiment estimates
the total effect of each policy change, including its market response, rather than
holding the opponent's realized revenue constant. Full paired values are in
[livestock_effects.csv](../reports/livestock_effects.csv).

## Mechanism diagnostics and a remaining defect

Post-registration descriptive replay separates 192 game/species rows and 576
game/product rows. These explain observed trajectories; they were not additional
preregistered outcome tests or a basis for changing the arms.

Selective feed alone saved 54.125 wheat units per game relative to routine, but
still spent about 52.75 care actions per game on animal nights without feeding.
Those actions cannot add a care bonus. Adding the care intervention increased
feeding by 42.125 units and reduced care actions by 24.625 per game relative to
feed. All observed care-bank additions in care/fertilizer were converted; no
bonus was lost to production caps. Routine lost four cow bonus units per game
to caps. Every arm avoided escapes and discarded inventory in this population.

Terminal timing remains imperfect. There is no final day-29 refresh. Action totals
minus observed night flags identify the following mean services with no subsequent
refresh; animals were not removed in these trajectories:

| Arm | Final-day feed units | Final-day care actions |
|---|---:|---:|
| routine | 6.000 | 5.875 |
| feed | 5.000 | 5.250 |
| care | 3.000 | 0.000 |
| fertilizer | 2.875 | 0.000 |

The care gate recognizes terminal conversion, but feeding can still protect a
hypothetical refresh that will never occur. That is an explicit next-study
terminal-feasibility hypothesis. Fixing it now would invalidate the registered
comparison. The raw outcomes and frozen policy remain unchanged. Species details
are in [livestock_species.csv](../reports/livestock_species.csv); product accounting
is in [livestock_products.csv](../reports/livestock_products.csv).

## Feature coverage and runtime

The study adds **234** descriptors: 138 production-timing, 18 service-routing,
18 feed/inventory/capital and 60 fertilizer-scenario features. Of these, 192 vary.
Seventy of the 78 previously constant animal descriptors now vary. This addresses
a real trajectory-coverage gap without proving each column useful.

The supported joint bank has **1,500** candidates: 1,205 varying, 295 constant,
157 nonconstant exact-duplicate groups and 1,775 highly correlated pairs. All
11,584 sampled observations were screened. No final feature was retained or
rejected by model selection. The project-wide union is 1,542 descriptors: 42 old
cash-history candidates are excluded from this study because own wheat buying
violates their sale-only identification contract. They are not silently filled
with zeros or removed from historical evidence.

The recorded policy p95 was 8.46 ms. A separate causal replay of one saved
fertilizer trace measured the full history-plus-feature pipeline: p95 5.42 ms,
maximum 29.61 ms over 181 vectors, with exact value agreement. This local CPU
profile excludes policy execution, serialization and I/O; it is not a deployment
deadline or memory guarantee. The original feature-assembly timer excludes
history updates and must not be interpreted as the full pipeline.

## Integrity, persistence and recovery

The independent audit checked 46,016 callbacks, 11,584 complete feature vectors,
1,984 policy/history restores, 92,032 actual private farm/market transitions,
322,112 stock-bound checks, 321,664 sale-bound checks and 1,152 product balances.
There were **zero mismatches**. Only the post-run auditor accesses private
inventories. Decision features use current/past legal observations. The audit and
registration bind engine, protocol, source and raw episode identities.

Completed episodes survived execution-service interruptions. An actual S3 restore
probe recovered a missing checkpoint and reused it with zero new games. Later
operational invocations ran at most one new game, within the registered maximum
of eight; the original runner finally revalidated and reused all 64. A reporting
adapter normalizes absent optional command counters to zero before grouping,
while preserving the frozen experiment and paired estimator. Its hash and this
correction are explicit in the report.

All raw episodes, the feature matrix, original source archive, 64-entry audit
archive and small evidence files are in private encrypted versioned S3. The
[remote verification receipt](../reports/livestock_cloud_verification.json) checks
the 82 required objects by downloaded bytes, SHA256, size, version, ETag and
AES256 headers. No new SageMaker compute was started. Registered simulation time
totals 722.27 seconds; this excludes audits, reporting, transfers and CI.

Canonical notebook 02 preserves the prior 23 code-cell sources and adds five
cells with results, paired contrasts, mechanisms, coverage and independent audit
checks. Its separate [execution receipt](../reports/livestock_notebook_execution.json)
records the genuinely executed artifact; the old supply receipt is preserved.
The [recovery runbook](livestock_recovery.md) specifies restoration, source checks,
bounded execution, reporting and publication without repeating completed games.

## Next bounded research questions

1. Register a terminal-aware feed intervention and joint service/delivery
   opportunity features; test whether avoided final-day work is actually banked.
2. Introduce stronger unrelated specialists and stress opponents. Current perfect
   scores cannot distinguish care from fertilizer on the ranking objective.
3. Test herd/crop mix, feed purchases, capital stress, land expansion and shared
   worker assignment. Two animals of each species do not settle optimal land use.
4. Generalize the cash-observation contract to own purchases before recombining
   its 42 descriptors; test continuation uncertainty and cross-product beliefs.

The [coverage ledger](feature_coverage.md) keeps all 18 research areas visible.
Further development remains within feature research; no validation/holdout run,
final model optimization or Kaggle submission is part of this milestone.
