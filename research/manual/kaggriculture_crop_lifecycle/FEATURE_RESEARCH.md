# Crop lifecycle: preregistered feature-family experiment

## Evidence and hypothesis
Notebook 14's marginal-price correction passed mechanics but changed zero sampled actions. Stop that test unchanged. The next intervention concerns nominal remaining production and renewal eligibility, not another price adjustment or a larger model.

The official `_daily_refresh_plants` component schedules a finite number of refresh events. For an ongoing crop planted on day p, nominal event days are p + first_yield_day + k*interval, for k=0..max_yield-1. The current parameter table gives TOMATO ages 8,9,10,11 and STRAWBERRY ages 10,12,14,16. Those events assume survival; caps, care, harvesting, decay and the game horizon affect realized goods. Single-yield crops are not classified as empty exhausted merely because they have no nightly-production events.

The existing FeedPolicy offers WATER jobs for unwatered plants and clears weeds for replanting. It does not explicitly add the existing weed-clearing job to empty, fully exhausted ongoing plants. We test whether that representation misses labor and plot-renewal opportunities.

## Registered arms: controlled component ablation
1. **control**: unchanged source policy plus notebook 10's final-callback SELL correction.
2. **retire**: same control, except WATER jobs are removed for ongoing plants with exactly zero held units and no remaining lifetime production event.
3. **renew**: retirement gate plus eligibility for the already existing crop-layout DIG job on those empty exhausted plants. The existing replant cutoff, DIG priority, layout, purchase policy and distance penalty are retained.

The two gates are active only on zero-indexed days 8..27. Original WATER treatment remains for all future producers and all plants holding goods. This is not notebook 12's 'no immediate/next-refresh benefit' deferral. No time-series outcome, seed, opponent inventory or future shop list enters a policy gate. Control and null-fork equality is mandatory. A null fork changes syntax, but no rule.

Primary comparisons: retire-control and renew-control. Component comparison: renew-retire. A common control makes those contrasts correlated; they are not separate independent samples. No final policy is promoted automatically, including after a favorable result.

## Representation
27 per-plant descriptors and 8 state summaries. Several fields are existing primitives, availability masks or diagnostic context; this is not a claim of 35 novel predictive signals. The feature dictionary labels their roles. The replacement first-sale step is only a lower bound using main-farmer travel, DIG, PLANT, maturation and deposit. It omits future maintenance, competing jobs, capacity, price uncertainty and crop loss, and it does not drive actions in this experiment.

## Mechanics, isolation and selection
- Match the installed official refresh function's abstract syntax and crop parameters to the attributed source excerpt, then test 380 calendar cases against that installed function. Test four distinct artificial DIG/replant cases with the installed unit-action function.
- Screen three preserved coordinated episodes: (1601,0), (1601,1), (1602,0). Sample every four callbacks from step 192 to 668, plus boundaries 191,672,695,696: 124 observations per source, 372 total. A sparse screen can miss activation at unsampled turns.
- Require exact source-action parity for the control, null-fork parity, legal observation immutability, and no action difference outside the registered window on the same state.
- Select the first activated source by seed/seat, not reward. If neither treatment changes an action, stop without a continuation.
- For one selected source, run exactly three branches. Replay its 192 recorded prefix transitions in the actual seeded environment, then run 527 consecutive decisions with responsive candidate and opponent policies. Seeds are evaluator-only; no manually fabricated future shops or RNG.
- Reproduce the control's recorded actions/states through the penultimate step and its notebook-10 guarded terminal outcome. Persist each completed branch with a checksum/readback. No fresh Kaggle score is implied.

## Budgets and evidence gates
Screen worker cap 120 seconds; pilot cap 180 seconds, plus two seconds for process cleanup. Ten-second UTC heartbeats. Complete measured callbacks <=500 ms. No GPU, external services, network requests, cloud writes, installs or model fits in the package. These limits do not stop the AWS application.

The pilot finishes one small prespecified three-arm block so both hypotheses receive component comparisons. A harmful arm is rejected and not scaled; it is not repeatedly retried. A timeout or implementation error preserves completed branches and blocks unchanged automatic restart. At most 576 prefix replay plus 1,581 policy-driven suffix transitions are represented. There are no new seeds and no full-season reruns of every prior study.

Per-arm decisions distinguish negative endpoints, no trajectory activation, no endpoint benefit, and a promising but unvalidated development pair. No significance tests over individual turns; no feature selection fitted on outcomes. Future confirmation must use protected/new seed groups and at least two genuinely distinct, source-identified opponents, with both seats. Do not keep picking winners from these two repeatedly examined seeds.

## What remains open
This milestone does not exhaust crop mixes, staggered planting, capital-adjusted replanting, heterogeneous hiring value, land expansion, maintenance bottlenecks, strategic price timing or causal opponent-history features. The complete callback still inherits its <=3 hired hands per farm restriction. The feature table itself is variable-workforce safe, but that is not a whole-agent certificate. A valid submission and comparable official rating remain necessary to assess the user's 3140.0 research target. That target is user supplied, not newly verified here.

## Primary sources and source boundaries
- Kaggle official engine: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py ; installed engine SHA256 required: bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e.
- Pinned FeedPolicy: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_terminal/feed_policy.py ; required Git blob cd180956abf626b772ba761fb37a3fc3a749c225.
- Kaggle observation/mechanics README: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md .
The experiment is derived from simulator mechanics and inspected project source. It does not claim to replicate a verified winning solution or import real-world agronomic correlations into a simulator lacking those mechanisms.
