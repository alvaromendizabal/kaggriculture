# Crop maintenance: defer only when the current service has no measured near-term benefit

## Evidence and sources

**Returned evidence:** notebook 11 improved its static route objective in 42/69
sampled observations but its one primary endpoint changed own cash by -2, opponent
cash by -3, and margin by +1, without changing the win. `RESULTS_REVIEW.md` records
the complete scope and the prior rejection. It does not support enlarging the
same route shortlist test.

**Repository source:** the pinned `FeedPolicy` offers a WATER job whenever a plant
has not been watered. Its priorities already represent death risk and an immediate
watering bonus. The completion ledger explicitly leaves alternate-day maintenance
and value-aware water routing open. We are not claiming to invent survival or
maturity features, or treating the older 1,621-candidate union as an adopted model.

- Source policy: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_terminal/feed_policy.py
- Completion ledger: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/docs/feature_coverage.md
- Official simulator: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
- Official game documentation: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md

The runtime requires the already-reviewed interpreter SHA256
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` and version 1.32.7.
Reading a current upstream page is not permission to update that runtime.

## Mechanistic basis, not real-world agronomic extrapolation

The game exposes plant age, water state, consecutive unwatered days, yield,
fertilizer expiry, production intervals, and lifespan. These govern survival and
production. A WATER action may reset the survival counter, add a capped immediate
single-yield bonus, or enable an ongoing-crop fertilizer bonus on a production
refresh. A plant can also decay before that refresh.

These relationships are implemented in a closed-form current-state scenario and
checked against the installed official `_apply_unit_action`, `_decay_plants` and
`_daily_refresh_plants` functions. The scenario holds subsequent harvesting,
fertilizing, watering, digging and replanting fixed. It is not a prediction of the
agent's complete future behavior or future market prices.

## Hypothesis

When a crop is not in immediate survival danger, WATER adds no units immediately,
and the WATER-now scenario adds no next-refresh survival or yield, omitting that
job may release a worker for a better current task. This **does not make deferral
globally safe**: it transfers an obligation to tomorrow, and travel, competition
between workers, later treatments, or crop death can make the policy worse.

The new representation includes 30 numeric plant descriptors and 11 state
summaries. Several are previously used primitives or bookkeeping. The new
intervention is the explicit deferral eligibility rule and its maintenance-debt
representation. Counts are not novelty claims or proof of predictive strength.

## Controlled implementation

`maintenance_policy.py` verifies the Git blob of the pinned source file, parses
only `FeedPolicy.__call__`, and requires exactly one matching WATER eligibility
condition. It replaces that one condition in a separate in-memory subclass.
It does not change files, monkey-patch module globals, reorder jobs, fit weights,
or alter the other branches. A null fork always returns the original condition.
Its actions must exactly equal the original callback on every tested state.

Treatment is enabled only on zero-indexed game days 20 and 21, selected before
new measurements as a bounded established-production window. It is not a
validation partition or a threshold tuned to a favorable episode.

All priorities, tie-breaking, staffing rules, buy/sell rules, layout, and final-day
router remain unchanged. The notebook-10 final-sale rule is shared by both arms.
Market *rules* are fixed; quantities can change as a consequence of changed farm
actions and state. That is an intended mediated effect, not a separate market
intervention. The callback's inherited three-hired-hands restriction remains.

## Leakage contract

The feature functions receive the current legal observation and public crop
parameters. They do not use opponent private stock, rewards, seeds, future shops,
or replay outcomes. Seed, seat, and source-arm columns are audit/group identifiers,
not fitted predictors. Current day and hour are legal state variables.

The evaluator may use the recorded seed to recreate the environment, and both
private views to verify it. It passes only each player's own legal view to that
player's callback. No seed is inserted into the actor configuration.

## Stages and decision gates

1. **Local unit tests, live preflight, and live mechanics parity.** Stop on any
   source, environment, data, logic, or input-mutation discrepancy. Live parity
   covers 736 artificial plant fixtures / 1,472 WATER-vs-no-WATER component paths.
2. **Screen 468 saved observations.** Use hours 0,6,12,18 on days 0–28, plus every
   hour on days 20–21, in the three coordinated source episodes. Verify original
   source and null-fork actions. Sample frequencies overrepresent the intervention
   window; aggregate activation is not full-season incidence or importance.
3. **Select the first activated source by seed/seat order.** Do not choose by
   endpoint gains. If no action changes, skip the pilot and stop unchanged scaling.
4. **One paired endpoint pilot.** For each arm, replay 480 recorded transitions
   in the real seeded official environment and verify the prefix. Then run 239
   reactive decisions through the endpoint. The real environment is essential:
   this suffix crosses random nightly weed/shop events. No invented random state
   or replay-injected future shop sequence is used.
5. **Control checks.** The control must reproduce all recorded pre-final actions
   and states, and notebook-10 final rewards. The null fork must match the original
   on every current state. Outside days 20–21, the candidate must equal the
   same-state control. After treatment, states and downstream actions may diverge.
6. **Outcome decision.** Keep the existing conservative rejection of any lower
   own cash, margin, or match result; report tradeoffs explicitly. Otherwise stop
   for nonactivation or no benefit. A positive pair is exploratory, not adoption.

Limits: screen 120 s; pilot 180 s; callbacks 500 ms; 10-second supervisor
heartbeats; verified episode/branch checkpoints; no repeated automatic retry after
failure. At most 1,438 interpreter transitions (960 replay + 478 continuation),
not an unrestricted training sweep. A failed attempt's completed branches remain.
No automatic S3 publication, GitHub writes, or Kaggle submissions are performed.

## What this does not establish

Three source episodes represent two already-examined seeds. Neither turns nor
mirrored seats are independent replicates. There are no confidence intervals or
out-of-sample superiority claims from one pilot. A positive result requires new
grouped seeds, both seats, meaningfully distinct opponents, full-season deployment
coverage, repeated timing checks, and an actual comparable submission metric.

Only one predicate is ablated here, not every underlying descriptor separately.
The four field groups (survival, immediate yield, next-refresh treatment effect,
maintenance debt) require additional controlled interventions if this gate merits
further investigation. No feature family is declared mature.

## Subsequent high-value rounds (not auto-launched)

| Round | Question | Required experiment |
|---|---|---|
| Maintenance debt and routing | Does reduced current upkeep create tomorrow's service bottleneck? | Deadline-load and travel interactions under equal staffing; stable endpoint effects |
| Crop cohorts and regeneration | Which repeated planting/harvest patterns monetize before decay/end? | Joint maturation, replant, delivery and crop-mix action ablations |
| Marginal labor | When does one additional hired hand cover its escalating cost? | Worker-capacity/route return test after broad-workforce callback correctness |
| Land and working capital | Is extra capacity usable before its cost can be recovered? | Time/labor/cash-adjusted expansion with explicit capital stress |
| Opponent-aware sales | Do causal supply beliefs improve competitive outcomes? | Unrelated opponents and fresh groups; no hidden inventories or outcome leakage |

These are prioritized, testable avenues, not claims that all will improve the
score. The user-supplied 3140.0 leaderboard target remains unverified in this run;
local coins and match fractions cannot be mapped to it.
