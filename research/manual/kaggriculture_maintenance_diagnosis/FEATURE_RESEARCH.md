# Maintenance diagnosis and interaction features

## Question and scope

First reconcile why the previous feature intervention lost 396 coins. Then inspect
prospective features for mechanisms a one-refresh comparison cannot represent.
No new policy intervention is included. Hypotheses are not rewritten as findings.

## Source-derived constraints

The reviewed official engine processes unit actions, market trades, town demand,
crop decay, and nightly refresh in order. WATER can add a crop-specific immediate
bonus; fertilized ongoing crops receive their extra nightly yield only when watered.
Harvesting an ongoing crop empties its held yield without removing the plant.
Dry streaks and caps interact with those events. Hired hands expire at night.
Source: Kaggle/kaggle-environments, kaggriculture.py; reviewed Git blob
`3c202c7ee921da239356789e266b694635103fc4`; required installed interpreter SHA256
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.
https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py

The existing policy and coverage ledger distinguish maintenance, crop lifecycle,
production, fertilizer, delivery, labor and market context as open research.
https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/docs/feature_coverage.md

## Implemented prospective representation

Twenty-two per-plant descriptors plus eight state summaries. Some are context or
previous primitives, not novel variables. None has been selected for deployment.

1. **Harvest–WATER complementarity.** Compare PASS/PASS, WATER/PASS,
   PASS/HARVEST, and WATER/HARVEST on the same tile on the current and next callback.
   Follow crop decay and the next refresh. Total units means collected units plus
   units held by the plant, not cash. An interaction term measures whether the
   marginal WATER effect changes when a following harvest is included. A full crop
   can otherwise conceal a potential fertilized production bonus. This mechanism
   is tested in artificial fixtures, not asserted to explain notebook 12.
2. **Two-refresh survival buffer.** Compare WATER now with no WATER now, then no
   additional intervention through two refreshes. Availability is explicit near
   the terminal boundary. These pathways quantify a conditional maintenance debt,
   not a prediction of future worker behavior or plant death.
3. **Deadline and access context.** Nearest and second-nearest current worker,
   single-task service effort, survival-only deadline slack and current-night
   access counts. Workers are not capped or truncated by this extractor. No hired
   worker is assumed to persist into tomorrow. Distances and independent task
   counts are not a solved joint service schedule.

## Leakage and information availability

`interaction_features.extract` sees current own public farm and clock plus fixed
crop mechanics. It does not read rewards, seeds, future actions, evaluator states,
or opponent private inventory. It ignores additional observation metadata and
preserves its inputs. Feature rows are written separately from trade and outcome
ledgers. No training, feature selection, target encoding or learned thresholds occur.

These 478 reconstructed observations include the rejected branch and are already
exploratory development data. Treat turns as repeated measurements in one seed,
not independent samples. There are no confidence intervals, generalization claims,
or unseen-validation scores in this milestone.

## Accounting, not another experiment

Parse and bind the logged action stream to the two accepted branch checkpoints.
For each branch, replay the 480-step shared recorded prefix followed by its 239
recorded actions, including its recorded opponent responses. Compare all recorded
cash balances and the original final-state SHA256. No actor is called.

Separately instrument original market function bodies on deep copies; log only
successfully committed units and cash changes, plus actual hiring/land spending.
No module globals are modified. Every turn's cash and both players' endpoint cash
must reconcile. Compare simulated crop action, decay and nightly-refresh phases
to live replay crops, preserving cohorts by position and planted day.

Sales revenue is decomposed descriptively into quantity and average-price terms
where both branches sell a positive quantity. Prices respond to the trajectories,
so this arithmetic identity is NOT a separate causal estimate. Zero-quantity
branches have no fabricated mean price. Inventory loss channels not explicitly
logged remain outside the crop ledger; do not claim complete goods conservation.

## Tests and gates

Local tests bind the actual supplied action log and verify formulas, both seats,
input isolation, caps, deadlines, branch artifacts, and instrumentation safety.
The local component adapter is an explicit small independent implementation,
NOT the installed Kaggle environment. The live run checks 480 conditional scenarios
against real installed `_apply_unit_action`, `_decay_plants` and
`_daily_refresh_plants` before any accepted diagnostic replay.

Accept only with exact source, report, code, raw-checkpoint and final-state hashes;
478 trace checks; 1,438 represented recorded transitions; and zero accounting
residual for both players. Stop at the first disagreement and preserve diagnostics.
The stage cap is 120 seconds. No unchanged failed-run retry or scale-up is automatic.

## What the result earns

A successful run earns an explanatory ledger and a tested candidate representation,
not a stronger policy. The following intervention should target the measured loss
channel: for example, retain productive WATER–HARVEST combinations or constrain
maintenance debt when the ledger supports that mechanism. Keep other rules fixed,
then run an action screen and paired endpoint test. Do not turn the scenario values
into a multi-feature score without a separately registered ablation.

Fresh groups, distinct opponents and an official valid submission remain necessary.
The complete callback's old workforce boundary is not repaired by this extractor.
Real weather, soil and satellite features are not introduced: they do not have
corresponding mechanisms in this simulator.
