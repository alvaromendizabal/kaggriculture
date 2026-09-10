# Resource-relationship feature research

## Question and domain rationale

Can a high-yield decision destroy value because delivery capacity, deadlines or working
capital are ignored? Study 1's full scheduler discarded 26 harvested units per game.
This motivates explicit interactions, not arbitrary products of every pair of columns.

The primary domain source is the **installed, hash-pinned Kaggle interpreter 1.32.7**.
The [official description and source](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture)
are the public reference. Real-world rainfall, soil chemistry and crop calendars are not
implemented in this game; importing them would create unsupported signals.

[Gallego and van Ryzin's finite-horizon inventory research](https://business.columbia.edu/faculty/research/optimal-dynamic-pricing-inventories-stochastic-demand-over-finite-horizons)
motivates representing inventory jointly with remaining selling time. Its demand model and
pricing-control assumptions are **not** adopted: here the agent chooses sales quantities,
prices come from the game's market, and future town unlocks are uncertain.

[Hooker, Mentch and Zhou](https://arxiv.org/abs/1905.03151) explain why independently permuting
dependent predictors can produce misleading importance. Accordingly, we profile dependence
and test coherent policy-component interventions. Correlation is not causal benefit.

## Mechanistic hypotheses

| Relationship | Implemented representation | Important qualification |
|---|---|---|
| Yield × storage × delivery | Current room, room after selling, ready-wave overflow, unit travel/slack, value per delivery action | A full ready wave is a conservative scenario, not predicted same-day harvest |
| Maturity × labor × land occupancy | Capped-ready crops, avoidable unit-days, minimum maturity/decay times, route feasibility | Cap collection intervention is local, not a global scheduler |
| Water × fertilizer × capacity | Marginal WATER gain, next-refresh rescue, fertilizer increment conditional on water, overflow interaction | Refresh-phase predictions exclude prior decay and assume treatment availability |
| Seed spending × staffing × receipts | Costed staffing runway, spendable cash, shortfall, cash/reserve ratio | Earliest maturity is a conditional receipt scenario, not guaranteed liquidity |
| Own wave × rival supply × town demand | Bulk sale impact, current-shop demand, demand-only price scenario, visible rival supply stress | Rival private shed/carry and future shops are never inputs |
| Feed × care bank × production cap | Survival, feed-rescued output, delayed care bank, saturation | Tested against engine; crop-only rollouts do not establish livestock utility |
| Historical prices × inventory × cash | 1- and 24-turn changes, log price changes, explicit availability masks | Episode-local, consecutive causal history; no target encoding |

`relationship_features.py` adds 374 descriptors, including 40 history descriptors, to the
original 244. **618 is the state/history schema size**, not the count of useful predictors.
The first study's 13 action-feature templates are a different level of representation and
are not added to this number. No parameter search, learned model or final selection occurs.

## Registered development design

`configs/relationship_research.json` was created before the two full-game smoke checks.
The smoke outcomes were not used to tune the intervention rules. The complete design is:

- Seeds 1101–1104 only; both seats; all eight capacity/capital/maturity ON/OFF combinations.
- 64 full 719-action games versus the exact frozen previous full crop scheduler.
- Reference source SHA-256: `52db5557b6bb71a4f0c7bfe5ce6faf7fb92d878dfc5b2d353781c9dc28f1d806`.
- 1,020-second experiment budget within the workspace runner's 20-minute process deadline.
- Exact game checkpoint, source/engine/protocol lineage and immediate private S3 persistence.
- Per-game conservation: harvested = sold + final held + discarded.
- Every fourth legal observation plus the final callback is profiled: 181 states per game.
  Causal history is updated at every callback, including unsampled turns.

All-off calls the frozen scheduler unchanged. Capacity routes carried goods toward storage
when the currently visible harvest wave would overflow, and replaces destructive overflowing
DROP with bounded PLACE where possible. Capital reserves staffing costs before seed orders.
Maturity collects an already capped mature one-time crop when a worker is on that tile.
Priority order is maturity adjustment, then capacity adjustment, then shared-inventory shadow
execution and feasible sales. The factorial study explicitly tests their interactions.

Main effects average ON-minus-OFF over nuisance factors. Pairwise contrasts are differences
of differences, and the triple contrast compares the pairwise effect across the third factor.
Intervals resample four complete seed clusters, with both seats and every arm kept together.
These are descriptive development intervals, **not confirmatory significance tests**.
No random turn-level split, holdout reuse, multiplicity claim or leaderboard claim is made.

## Feature screening and limitations

The full bank is checked for finite values, schema/order consistency (including checkpoint
reload), legal availability, variation, exact duplication and absolute Spearman correlation
at least 0.995. Constant and duplicate flags identify coverage/redundancy questions, not
automatic rejection. Every feature remains provisional for final-model selection.

Farm actions precede sales, and sales precede nightly dumping. The town consumes at the
**current action's step**, including step 0 and multiples of 4/24; the demand helper tests
this alignment. Same initial seed does not guarantee identical future shop paths after
policy-dependent weed/RNG consumption. Crop projections and animal refresh predictions are
tested against the corresponding official phases over ages, caps and treatment states.

The stronger opponent addresses a weakness in study 1, but one stronger policy and four
reused development seeds are still inadequate for a feature-completion claim. See the
[coverage ledger](feature_coverage.md) for experiments that remain blocked or unperformed.
