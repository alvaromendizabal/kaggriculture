# Decision-bottleneck feature research

**Gate: OPEN RESEARCH. Target: strongest verifiable competition performance.**
No leaderboard win, fitted-model improvement, or completed eight-game pilot is claimed.

## Mechanism and missing representation

The frozen terminal route menu solves a coupled allocation problem: workers compete
for unique harvests, deposited goods share finite storage, and shared sales move
prices. Counting workers or separately ranking routes does not reveal which
constraint changes the best attainable decision. The new representation enumerates
at most 9^4 retained combinations once and derives exact discrete sensitivities.

For a retained feasible set F and utility U, a worker's removal value is
max(F) U minus max(F with that worker forced to PASS) U. Resource-removal values
forbid collection of one harvest/manure resource. Capacity effects re-solve the same
menu at room +/-1, +/-5 and +/-10 units, clamped to 0..100. Runner-up gaps and
optimal-plan multiplicity expose interchangeable plans and fragile decisions.

These are not continuous shadow prices, global optima, hiring ROI, or forecasts.
Increased capacity is a hypothetical sensitivity, not a purchasable game action.
Changing capacity does not regenerate the previously pruned route menus; reported
values are explicitly conditional on this retained menu. A route uses current
no-opponent-sale prices and an eight-coin action cost, as in the frozen baseline.

## Sources and scope

The source of game semantics is `src/kaggriculture_terminal/routing.py` at
`f5c63727b2996f6154b07e4e26c6bfbb899d8559`, and the pinned interpreter manifest.
The new objective uses the identical DFS menu order, exact resource exclusion,
capacity constraint and tie-break. It does not change the registered policy.

Assignment under explicit resource/budget constraints is also motivated by Aziz
et al., *Multi-Robot Task Allocation -- Complexity and Approximation* (2021),
https://arxiv.org/abs/2103.12370. That paper's ST-MR-IA problem is not identical to
Kaggriculture; it motivates constrained allocation, not any claimed game result.

## Availability, test and experiment contract

Only generated legal current-observation menus and public current market inventory
enter the extractor. Seeds, final rewards, hidden opponent inventory, future shops
and evaluator state are excluded. Historical checkpoint metadata only identifies
which development observation is being audited; it is not an extractor input.

There are 39 descriptors including contextual/availability controls, not 39 proven
novel predictors. Independent tiny exhaustive cases test the objective, exclusions,
capacity sensitivity, non-mutation and absent-worker semantics. A real AWS audit
then reuses the seven already-preserved episodes: 161 final-day observations, both
seats, two explored development seeds. Base utility and feasible-set size must match
the frozen recorded solver on every observation. It records variation by episode,
constants, high Spearman redundancy and extraction latency. No new games are run.

## Evidence gate and next ablation

Coverage is not predictive utility. No feature is selected for a final model here.
First inspect which sensitivities vary. Do not pursue more storage features on a
sample in which storage never binds. Prioritize worker/harvest opportunity values
that expose actual decision tradeoffs. The next policy ablation must freeze equal
staffing/market rules and compare a feature-informed option choice with the same
baseline on fresh development seed groups and unrelated opponents. Separate
seed groups, not individual turns, for any learned ranking or threshold selection.
Promotion requires official match-score evidence, runtime acceptance, and stable
results across the registered opponent/seed blocks; coin gains alone are insufficient.

## Pilot and benchmark cautions

The original pilot is halted at seven accepted games: game eight exceeded its
500 ms registered runtime gate and its rejected payload was not retained. Do not
call the surviving outcomes an unbiased eight-game estimate. Preserve this failure.
CI had exercised seed 1601 before AWS preregistration, so it is explored development
evidence, not untouched confirmation. Runtime snapshot parity is not live-policy
acceptance and does not authorize relabeling the failed eighth game as a success.

The live leaderboard and evaluation pages were requested on 2026-09-11 UTC but did
not yield readable rating data to this session. The current top numeric rating is
therefore unverified. Do not compare local match fractions to an invented rating.
Feature research remains open; a leaderboard record is a target, not a guarantee.
