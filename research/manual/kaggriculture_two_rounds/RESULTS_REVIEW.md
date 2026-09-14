# Notebook 16: completed, no automatic promotion

Source: the user's `kaggriculture_renewal_factorial_results.zip` (SHA256 recorded in
`reference/input_review.json`). All **50** manifest-listed files matched. The saved
notebook has **8 executed code cells and no error outputs**. The report records
54 passing tests, 527 archived-action and null-fork checks, and nine action changes.

| Arm | Own coins | Opponent coins | Margin | Local match |
|---|---:|---:|---:|---:|
| Control | 44,840 | 44,082 | 758 | Win |
| Retirement | 41,510 | 41,240 | 270 | Win |
| Clear-only | 42,858 | 42,028 | 830 | Win |
| Retirement + clearing | 43,451 | 41,639 | 1,812 | Win |

Clear-only versus control: **−1,982 own coins, −2,054 opponent coins, +72 margin,
unchanged win**. The existing conservative own-cash guard rejected it. A higher
margin is not a lost match, and a rejected cash guard is not a leaderboard result.
The within-block cash interaction is +3,923; the margin interaction is +1,470.
These are descriptive conditional factorial contrasts from one repeatedly examined
seed, not independent effects, significance tests, or generalization evidence.

Screen time: 19.95 seconds; single new branch: 26.22 seconds. Maximum reported
candidate callback: 77.02 ms in the screen and 135.64 ms in the continuation.
Three prior branches were reused. The new branch represented 719 transitions.

Decision: freeze this result and stop tuning seed 1601. Do not adopt retirement,
clear-only, or combined renewal. The narrow notebook-10 final-sale correction
remains common to the research controls, not a broadly validated winning policy.
The supplied report contains no official submission score. The user-reported
3140.0 benchmark is not comparable to in-game coins or a local match fraction.

## Why the next two rounds are different

The new rounds are proposals based on simulator mechanics, NOT mechanisms proven
by notebook 16's accounting. Round 17 asks whether current crop yield overstates
what a particular worker can harvest after travel. Round 18 asks whether a crop
harvest releases capacity for an imminent production event. They do not change
WATER eligibility, clearing rules, algorithm, layout or staffing. Each alters one
crop-HARVEST value expression, independently against the same baseline.

Two fresh development seeds and two source-distinct opponents are preregistered.
The four paired blocks are balanced, not fully crossed. Shared controls are reused
between rounds only under identical engine/source/protocol/code fingerprints.
