# Decision-bottleneck findings

**Feature research remains OPEN. No official-score gain or top-score victory is claimed.**

## Executed milestone

On 2026-09-11 UTC the existing `kaggriculture-dev` CPU workspace tested the new
representation and audited 161 saved final-day observations from seven accepted
staffing episodes. The source is `88a6f9d583af1325e508d2e0bd5623967ac1eb64`.
Seventy focused runtime/feature tests passed on AWS in 0.13 seconds. The feature
audit took 6.183 seconds; its supervising process ended after 15.810 seconds.
No new games, model fits, validation or holdout accesses occurred.

The 39 descriptors comprise 28 varying columns and 11 constants. Five pairs of
varying columns have absolute Spearman correlation at least 0.995. These counts
are coverage evidence, not proof of novelty relative to the entire earlier bank.
Every base objective and feasible-set size matched the recorded frozen solver
on all 161 observations. Extraction including route-menu construction took
10.358 ms median, 20.015 ms p95 and 69.609 ms maximum on this CPU run.

## What the representation taught us

Storage was not binding in this observed retained-menu problem: removing one,
five or ten units of room changed utility by zero on every observation. Expanding
room by those amounts likewise added no utility. Recorded best plans left at
least 67 units of storage slack. **Do not spend another sweep on these storage
sensitivities using the same states.** This does not establish that storage is
irrelevant to other policies, stages or stress populations.

Worker-removal values vary substantially. For the coordinated seed-1601 groups,
forcing the main farmer to PASS loses 1,105 conditional utility on average,
while the last hired hand has zero removal value on those same groups. For
coordinated seed1602/seat0, the corresponding means are about 1,509.61 and 2.70.
These are current-plan sensitivities, not marginal hiring profit or causal coin gains.
They expose dependence on worker locations and access rather than worker count alone.

The best/runner-up utility gap is zero on more than half of observations; optimal
plan counts range from one to 44. A justified next representation is the future
opportunity cost of the positions left by tied current-value plans. Avoid arbitrary
tie-breaking penalties without a controlled option-choice ablation.

## Next evidence gate

Use worker/resource opportunity and terminal-position value to define a bounded
option-ranking intervention. Hold staffing and market policies identical across
arms, use fresh development seed groups and unrelated opponents, and require
activation and full-policy latency acceptance before expanding the pilot. Fit
any weights or thresholds only on grouped training episodes. Retain features
only after controlled official-match-score ablation and stability evidence.

The old pilot remains `HALTED_LATENCY_LIMIT` at seven accepted games. Its eighth
attempt and runtime failure are not erased by this zero-game feature audit.
Neither the partial pilot nor these 39 descriptors establish leaderboard strength.
The live top numeric rating could not be verified from the available page response;
no invented target or local-to-leaderboard conversion is used.

Private raw feature rows are versioned in S3; small measured reports, code, tests
and the genuinely executed `04_decision_bottlenecks.ipynb` are public review artifacts.
