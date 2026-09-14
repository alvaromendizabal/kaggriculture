# Notebook 13 — verified diagnosis, not a new policy win

Basis: the user's `kaggriculture_maintenance_diagnosis_results.zip`.
All 22 manifest-listed files passed SHA256 verification. Its notebook has 10
executed code cells and no error outputs. The report records 46 passing tests,
480 installed-engine component scenarios, 1,438 recorded transitions, 478
reconstructed observations and 3,678 plant-feature rows. Worker time: 11.4764 s.
No new policy calls, new interventions or fitted models were made in that run.

## Reconciled own-cash difference

Control: 44,840; rejected WATER deferral: 44,444; difference: **−396 coins**.
The two final-state and all recorded cash checks passed.

| Accounting component | Difference in cash | Quantity interpretation |
|---|---:|---|
| MILK sales | −465 | 28 units in both branches; mean received price 142.7143 vs 126.1071 |
| FERTILIZER sales | +213 | 45 vs 49 units |
| WHEAT sales | −97 | 59 vs 57 units |
| TOMATO sales | −62 | 24 units in both branches |
| EGG sales | +22 | 44 units in both branches |
| WHEAT seed purchases | −10 | 6 vs 7 seeds bought |
| WHEAT product purchases | +4 | 48 units bought in both branches |
| STRAWBERRY sales | −2 | 4 units in both branches |
| WOOL sales | +1 | 28 units in both branches |
| Hiring | 0 | 30 hires in both branches |
| **Total** | **−396** | Exact accounting reconciliation |

Own wheat harvested fell from 50 to 48 units; wheat WATER-generated bonus units
fell from 34 to 32. Tomato and strawberry harvested quantities were unchanged.
No `cap_masked_water_gain` candidate activated in the 3,678 rows. This evidence
does not support promoting that speculative interaction as the explanation.

## What this does and does not show

The largest negative accounting component is realized milk price, not milk
volume. It does NOT show that milk alone independently caused the full loss,
that crop death caused it, or that a different harvest-value rule will fix it.
Prices, actions, opponent responses and stochastic public context are coupled.
Equal seeds do not guarantee identical later exogenous event paths when policies
consume random draws differently. No evaluator modification is proposed here.

Decision: keep ordinary WATER eligibility. Do not rerun rejected WATER deferral.
Investigate price-aware harvest priorities as a new family. Do not retry early
selling, the rejected route filter, or change multiple decision rules together.

No official Kaggle submission score is recorded. The user-supplied 3140.0 target
is not measured in in-game coins. This report cannot determine the leaderboard gap.
