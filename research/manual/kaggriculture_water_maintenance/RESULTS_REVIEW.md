# Notebook 11: verified review and decision

Source: `kaggriculture_route_opportunity_results.zip` uploaded in this conversation.
All **28** entries in its BUNDLE_MANIFEST.json were checked against the actual bytes.
The saved notebook has **14 executed code cells**, **zero error outputs**, and the
report records **68 passing tests**, no failures, errors or skips.

## Screen

69 observations from 3 coordinated episodes, 2 previously used seed blocks.
19,581 route rows. First farm commands changed in 42 states; the static assignment
objective improved in those same 42 states. Maximum candidate callback: 120.546 ms.
Reported screen time: 8.961 seconds. This is activation, not predictive validation.

## Endpoint pilot

| Comparison | Own cash control | Own cash candidate | Own delta | Opponent delta | Margin delta | Match delta |
|---|---:|---:|---:|---:|---:|---:|
| Sequential no-change control, 1601 / seat 0 | 44,837 | 44,837 | 0 | 0 | 0 | 0 |
| Coordinated primary, 1601 / seat 0 | 44,840 | 44,838 | -2 | -3 | +1 | 0 |

Both primary arms won. Both ended with zero remaining product inventory.
The primary changed farm actions on 9 same-state comparisons. The opponent's
commands did not change across trajectories. The pilot ran 92 interpreter
transitions; maximum candidate callback 97.590 ms; reported time 5.016 seconds.

The reported decision is **STOP_NEGATIVE_ENDPOINT**. It follows the conservative
registered rule that rejects any loss of own cash, margin, or match result. This is
a tradeoff: own cash fell while margin rose. It is not a lost match, a failed
notebook, or evidence that every routing-feature approach is useless.

The saved trace supports a proxy/outcome mismatch. Different routing and timing
also changed the opponent's receipts despite unchanged opponent commands, so
shared market effects cannot be ignored. The bundle alone does not identify every
sale-level causal contribution; no exact transaction-cause claim is made here.

## What is retained

The notebook-10 final-sale rule remains the reference for this next experiment.
The notebook-11 shortlist intervention is **not promoted**. There is no new official
submission score, no independent validation result, and no support for comparing
in-game coins to the user-supplied 3140.0 leaderboard target.

## New direction

Open the earlier-season maintenance family documented as unfinished in the
repository: alternate-day watering, value-aware water routing, and maintenance
workload. Notebook 12 screens representation across game days 0–28 and changes
one eligibility predicate only on days 20–21. A small paired continuation, not a
new optimizer or an enlarged terminal shortlist, tests whether the freed actions
actually improve the endpoint.
