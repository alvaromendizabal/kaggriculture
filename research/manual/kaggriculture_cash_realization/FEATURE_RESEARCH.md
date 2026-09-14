# Feature research — post-action realizable cash

## 1. What the returned evidence actually says

Notebook 07 passed on 161 final-day observations from seven accepted, latency-censored development episodes. It generated 2,418 candidate rows, passed 30 component-parity checks, and recorded 73 passing tests. Its extraction maximum was 3.132844 ms; that was NOT a complete-callback measurement.

The no-deadline probe changed 19 of 602 worker decisions: 0/344 in seed 1601, 19/258 in seed 1602. The other three removal probes changed no first commands. Independent top tasks were contested in 99/161 states. Those are diagnostics of an independent-worker, one-collection probe, not defects demonstrated in the stronger joint policy.

The returned notebook 06 also passed. Its 124 aggregate descriptors and variable-length worker/task tables remain useful research assets, but not proof that the full frozen policy accepts larger workforces.

## 2. Compare against the actual existing implementation before claiming novelty

The frozen terminal route generator already has explicit collection-to-deposit deadlines, task exclusion, capacity constraints, up to two collections, optional WATER→HARVEST, and fertilizer collection. Merely adding those concepts to a simplified prototype does not improve the real baseline.

The source-supported missing interaction is between the chosen farm action and its associated sell order:

1. `FeedPolicy` simulates its own farmer/hand actions on a copy.
2. It computes terminal market orders from that post-action inventory.
3. `StaffingPolicy('coordinated')` can replace the farm actions with a different route assignment.
4. It keeps `base_action['market']` rather than recomputing the same rule on the replacement actions' inventory.

Because unit actions precede market resolution, a product deposited this turn can be sold this same turn. Orders computed for a different action can omit newly deposited goods or request goods that were not deposited. The effect near the last callback can differ from a one-turn cash acceleration earlier in the day. Incidence and magnitude on the saved episodes must be measured, not assumed.

## 3. Hypothesis and implementation

**Hypothesis H08:** conditioning the unchanged terminal sell/reserve rule on the farm actions actually emitted will alter sell coverage and immediate cash in at least some coordinated-source states, without changing farm actions or non-SELL orders.

The feature family is post-action realizable inventory/cash. It explicitly represents nine products, inventory before and after our candidate actions, requested versus actually sellable units, policy reserves, uncovered sellable inventory, unsold stock, and one-seller conditional liquidation value. There are 158 descriptors, not 158 independently validated signals.

Control preserves the frozen action. Treatment runs the same terminal market rule on the effects of the emitted actions. Source routing is retained, with the existing faster price-curve assignment implementation. Both arms pay for identical base/routing/feature construction. This is a forward-only fork; frozen code is not edited or monkeypatched.

We do not fit models or choose numerical thresholds from outcomes. The source's rule constants remain unchanged, and action parity against saved source decisions checks the optimized implementation. Before introducing any learned scorer, all learned weights/thresholds must be trained on separate episode groups.

## 4. Information availability and leakage

Feature inputs: the current legal observation; our proposed farmer/hand commands; copied own-farm effects computed with official deterministic unit primitives; current public market information; and explicit control/treatment order lists.

Forbidden feature inputs: recorded rival actions, rival private holdings, next states, rewards, seed, terminal outcome, simulator RNG state, or future shops. The extractor has no parameters for these. Rival private state and the recorded rival action are passed only to a separate evaluator after the policy calls complete.

The conditional feature valuation assumes no rival trade. The evaluator can measure a different realized amount under the fixed recorded rival trade. Keep these quantities separately named. Outcome columns live in `one_step_effects.csv`, not the predictor namespace. Only columns beginning `cash.` are feature columns; seeds, episode ids, seats and source arms are grouping/provenance fields, not learned predictors by default.

## 5. Gates and negative controls

Unit tests → previous artifact and source verification → five synthetic official-engine fixtures → saved-state full-callback replay → exact interpreter next-state parity → grouped inspection.

Required checks: control action equals saved action; identical control/treatment farm actions; identical non-SELL/hire orders; unchanged input; same terminal market-rule implementation reproduces the base planner's orders when applied to its own actions; three preterminal source snapshots per episode are unchanged; source next states match exact interpreter transitions; both arms' maximum actual complete callback time is at most 500 ms.

Each replayed episode is checkpointed. A latency violation records actual timings and action payloads before stopping. Synthetic fixtures are mechanics checks, not scored games. The last-callback fixture checks terminal status and newly deposited inventory liquidation.

## 6. What would justify more compute?

No activation → stop this family on this slice; do not spend on full games merely to obtain a result.

Negative or ambiguous one-step effects → inspect those exact states, reserves and simultaneous trading first.

Positive one-step activation with all correctness/runtime gates passed → a separate, small paired continuation experiment is justified. It must compare accumulated final cash, residual goods, ineffective actions and match result under the same prefix, staffing rules and opponent. One-step cash advances may cancel later; do not aggregate them into a fictitious season gain.

Before full seasons, verify the complete callback across the intended legal workforce domain and additional state regimes. Inventory development and CI seed use, register fresh disjoint groups, and include at least two source-identified opponents and both seats. No automated full-game stage is included in this package.

## 7. Remaining feature rounds — still OPEN

| Round | Mechanism and candidate family | Evidence still needed |
|---|---|---|
| Cash realization (this round) | Action-conditioned sale coverage and terminal inventory accounting | Callback parity, one-step realized cash, then paired continuation |
| Route commitment | Progress to cash, first-action alternatives, cost of switching destinations, completion-versus-replanning | Activated actions, bounded paired horizon tests; compare actual frozen richer menus |
| Crop economics | Remaining production schedule, watering/fertilizer response, decay timing, location-adjusted labor and cash-return delay | Seasonal states, exact boundary tests, controlled family ablations |
| Livestock economics | Feed opportunity cost, escape risk, capped held yield, delayed care-bank payout, fertilizer reuse | Production-event coverage and isolated fold/season evidence |
| Capital allocation | Incremental workers, accessible task value, land payback, working capital and investment alternatives | Broad-workforce action-path acceptance and meaningful stress regimes |
| Public market history | Known demand cycles, public supply changes, observable rival production and causal history uncertainty | Strict episode resets, diverse opponents and isolated temporal evaluation |

No candidate counts, test totals, charts or local win fraction establish a leaderboard rating. The user-supplied 3140.0 benchmark remains a target, not a verified score attained by this project.

## Primary sources and provenance

- User-uploaded `kaggriculture_action_feature_results.zip`; SHA256 and findings in `reference/input_review.json`.
- Frozen staffing callback: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_staffing/policy.py
- Frozen base rules: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_terminal/feed_policy.py
- Existing route representation: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_terminal/routing.py
- Faster action-equivalent assignment: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/src/kaggriculture_runtime/routing.py
- Official Kaggle engine: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py . Live execution must verify package 1.32.7 and SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`; current upstream documentation is not substituted for that pin.
- Official observation and action documentation: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md
- Aziz et al., Multi-Robot Task Allocation — Complexity and Approximation (AAMAS 2021), https://arxiv.org/abs/2103.12370 . Conceptual support for coupled allocation; not evidence of feature uplift in this simulator.
