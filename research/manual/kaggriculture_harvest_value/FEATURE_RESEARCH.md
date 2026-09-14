# Milestone 14 — harvest cash-value representation

## Hypothesis and source basis

The pinned `FeedPolicy` at commit
`7194116dfc92a8663139611233b5a221dad431a4` uses **current quote × units** in
both crop and livestock HARVEST priorities. It also uses fixed action priorities
and a distance penalty. This study changes only those two value multiplications.
The null version restores the original multiplication and must match all emitted
actions. The original policy file and previously evaluated policies stay untouched.

Primary mechanics source:
https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
Pinned installed-engine SHA256:
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.

Policy source:
https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_terminal/feed_policy.py
Git blob: `cd180956abf626b772ba761fb37a3fc3a749c225`.

## Exact conditional representation

Let R(I,q) be the revenue from a one-sided sale of q units starting at market
inventory I. Each unit receives the current quote; market inventory increases
only when that unit's price exceeds the one-coin floor. Let b be current
same-product shed stock. Candidate harvest value is:

    R(I,b+q) - R(I,b)

The implementation advances the b-unit sale once, then values q units. Cash
belonging to existing shed stock is not counted as harvest income.

This is a **conditional opportunity-value proxy**, not expected future revenue.
It assumes the existing stock sells first. Feed/fertilizer reserves, future
opponent trades, travel, decay and later demand are not reflected in the
policy-active term. It must earn adoption through an endpoint ablation.

Nineteen task descriptors and eight summaries include raw context and derived
features. They are not all novel or proven predictive. One-plant candidate rows
are not independent observations for significance tests. See the dictionary.

Diagnostic-only arrival values use current visible shops and a same-day earliest
HARVEST→travel→DROP/SELL sequence. The calculation masks routes that cross night
or the final decision: hired hands cannot be projected beyond expiry. It ignores
capacity/competition between workers and unknown rival trades and unlocks. It is
not supplied to the action intervention. Do not add separate task values and call
that feasible joint revenue.

## Controlled design

- Ordinary WATER logic is restored (no deferral). Both arms use the existing
  final-callback sale alignment, not the rejected all-day selling variant.
- Crop/livestock HARVEST values change only on zero-indexed days 20–21.
- Job eligibility, constants, distance penalties, routing, purchases, hiring,
  selling rule, and layout remain unchanged. Changed states may subsequently
  cause different actions and orders; that is part of the trajectory effect.
- Screen all 48 intervention-window callbacks plus four boundary checks for each
  of three coordinated archived episodes: **156 observations**, two known seeds.
- A same-state null fork must equal the control, and the control must match
  recorded actions. No non-window action differences are allowed.
- If there is no action activation, stop without any simulator pair.
- Otherwise select the lexicographically first activated seed/seat, not by reward.
  Replay 480 recorded prefix transitions in each actual seeded environment, then
  advance 239 decisions to the endpoint with a responding opponent.
- One pair maximum. Restore the opponent's clock/state correctly. Supply it only
  its legal observation. No replayed future actions or secret inventories enter
  either policy. No seed reconstruction or future-shop lookup is permitted.
- Observe final own coins, relative margin and local match result. Any negative
  one of those metrics triggers a conservative non-promotion decision. Coins are
  not the leaderboard rating; this secondary safety gate does not redefine the
  competition metric.

## Acceptance and next decisions

Mechanics: 405 marginal-sale cases and 189 demand phase cases must agree with
installed engine functions. Test the wheat logarithmic curve, true floor cases,
duplicate shops, current-turn consumption, and finite-horizon masks.

Runtime: 90-second screen; 180-second pilot; 500 ms per measured callback. Save
violating payloads before stopping. Each completed source/branch has an atomic,
checksummed, read-back-verified local checkpoint. No automatic unchanged retries.
Data remain on the existing persistent space and in the downloaded result ZIP;
this milestone does not upload new S3 versions. Never delete the space.

A positive pair is selected development evidence, not validation. Before adoption:
freeze the intervention, assess untouched development groups and different
source-identified opponents, compare both seats, report losses too, and verify
complete callback coverage. Repeated tuning on these two seeds is not an estimate
of generalization. The existing <=3-hired-hands callback restriction remains
unresolved even though this feature extractor itself has no fixed worker slots.

## Open research ledger — not more simultaneous changes

1. Current-lot/backlog sale value: implemented and locally tested here; live
   activation and paired endpoint outcome pending.
2. Arrival value under public demand and rival supply: diagnostic candidates only;
   future causal history, uncertainty calibration and separate ablation required.
3. Survival/production plus joint worker obligations: current plant interactions
   tested in notebook 13; no policy promoted. Conditional cap masking did not
   activate in that reviewed slice.
4. Marginal hiring and investment value: major open family; requires generalized
   callback coverage and same-budget controls before full-season tests.
5. Broader validation and a valid submission: still missing. No leaderboard gain
   is claimed; no historical record is guaranteed.

Do not turn this ledger into an unbounded sweep. One activated family per bounded
experiment; stop nonactivation or harm and preserve the result.
