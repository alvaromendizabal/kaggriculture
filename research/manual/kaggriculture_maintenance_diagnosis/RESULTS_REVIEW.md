# Notebook 12 — verified negative-result review

The supplied `kaggriculture_water_maintenance_results.zip` contains a completed run,
not a crash. All 29 entries in its bundle manifest match their SHA256 hashes.
Notebook 12 has 15 executed code cells, no error outputs, and eight Plotly outputs.

| Measurement | Result |
|---|---:|
| Tests passed | 63 |
| Official-component plant fixtures | 736 |
| Saved-observation screen | 468 observations / 3 source episodes / 2 seed blocks |
| Screen action changes | 51 |
| Primary continuation pairs | 1 |
| Control own final cash | 44,840 |
| WATER-deferral own final cash | 44,444 |
| Own cash difference | −396 |
| Opponent final cash difference | −241 |
| Coin-margin difference | −155 |
| Local match outcome | Win in both branches |
| Final residual products | Zero in both branches |
| Candidate same-state action changes | 15 |
| WATER commands | 78 control / 68 deferral |
| Maximum candidate callback, screen / pilot | 30.47 ms / 21.47 ms |
| Recorded stage execution, screen / pilot | 18.62 s / 26.89 s |
| Official submission score | Not supplied |

The recorded decision is `STOP_NEGATIVE_ENDPOINT`. Do not promote or retry the
unchanged WATER-deferral intervention. There is no basis for inferring from fewer
WATER commands that work was saved productively.

## What the existing evidence can and cannot explain

The cash difference reached +1,045 and −1,443 during the suffix before finishing
at −396. At the end of day 20 it was +173; at the end of day 21 it was −239.
Temporary cash balances therefore cannot substitute for terminal outcomes.

The report contains commands and aggregate cash, but not the complete crop and
inventory states along the deferral branch or a committed-trade ledger. It does
not establish that plant deaths, a missed fertilizer bonus, storage overflow,
later buying, or worse sale prices caused the loss. Those remain distinguishable
hypotheses, not findings. The prospective source screen had zero rows combining
deferral eligibility, an ongoing harvestable crop, active fertilizer, and a next-
refresh production event; no existing evidence proves cap-masking caused this loss.

Notebook 13 reconstructs these already-recorded trajectories. It does NOT run the
rejected policies again, alter an action, choose a new arm, or fit a model. Seeds,
full evaluator state, and both private inventories remain outside feature inputs.

## Carried-forward performance state

Notebook 10's final-callback sale correction remains separate provisional evidence
(+42 in one inspected primary case). Notebook 11's shortlist change and notebook
12's deferral change are not accepted. No current Kaggle submission score or verified
leaderboard rating is established by these files. The user-supplied 3140.0 objective
is not comparable to game coins or a local win fraction.
