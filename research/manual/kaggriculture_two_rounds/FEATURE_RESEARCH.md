# Two independent feature investigations: rounds 17 and 18

**Status: open research. No feature-performance claim, new official score, or
submission-readiness claim is made by this document.**

## Evidence and research basis

The notebook-16 facts are confined to RESULTS_REVIEW.md and its retained report.
They do not establish that either proposed feature is the cause of previous losses.
The game-specific reference is the pinned Kaggle interpreter (SHA256
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`).
Kaggle's public documentation/source:
https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture

The task-allocation literature motivates representing task values conditional on
worker access and time, rather than treating independent current rewards as joint
achievable rewards. It is not evidence of Kaggriculture effectiveness:
Aziz et al., Multi-Robot Task Allocation—Complexity and Approximation (2021),
https://arxiv.org/abs/2103.12370.
Chen et al., Decentralized Task and Path Planning for Multi-Robot Systems (2020),
https://arxiv.org/abs/2011.10034.

Blocking supports comparisons under matched nuisance conditions:
NIST randomized block designs,
https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm.
The protocol uses deterministic game seeds as blocks, not independent turn-level
samples, and makes no p-value or significance claim from its small pilot.

## Round 17 — arrival-adjusted harvestable stock

Hypothesis: a remote ready crop can lose units between the current decision and
the worker's harvest command. Current `units * quote` may overrank that task.
The policy already has travel penalties and terminal feasibility filters; this is
an incremental *arrival-unit* hypothesis, not a claim those features were missing.

Intervention: replace the one crop HARVEST valuation by
`predicted_same_day_arrival_units * current_quote`. A harvest happens before decay
on its own callback, so decay on the arrival callback is excluded. If arrival
crosses midnight, retain the original value and mark the scenario unavailable;
we do not assume a hired worker survives expiry or inject future nightly outcomes.
No route-size, job-eligibility, price-forecast, harvest-priority constant, or
algorithm change accompanies the feature. A zero-valued harvest still retains the
base job priority; the intervention is deliberately a value ablation, not a new
legality filter or guarantee that every bad task is avoided.

Representation: 32 descriptors per worker/crop option; 12 current-state summaries.
Travel, decay phase, retained stock, liquidation deadlines, survival ratios, own
inventory context and masks are documented in the round-17 dictionary. Context
fields are not called novel. Multiple worker rows can refer to the same crop;
row sums are not achievable aggregate harvests or independent samples.

Explicit component tests cover expiry parity, action/decay order, zero stock,
same-day boundaries, future metadata isolation, input immutability, both seats,
and variable numbers of workers in the *extractor*. The action callback remains
limited to its original admitted <=3-hands domain on both farms.

## Round 18 — production headroom released by harvest

Hypothesis: currently held crop stock can block an impending capped production
increment. Harvesting may have an additional benefit beyond collecting that stock.
The existing livestock scorer already includes a production-overflow signal;
this round targets **crops only** and does not claim that animal overflow was new.

Intervention: add `conditional extra next-refresh units * current_quote` to the
original crop HARVEST value. Compare HOLD and HARVEST paths after same-day travel,
then apply remaining decay and the next crop refresh using current watering and
fertilizer state. The extra production is the difference in newly produced units,
not a double count of harvested stock. Use zero extra value when no remaining
refresh exists, the crop is not ongoing, arrival crosses midnight, or the crop
cannot be harvested on arrival. Scheduled production after the crop's finite
lifetime is not included. Survival/death and decay-to-weed remain explicit.

Representation: 32 task descriptors and 12 summaries, matched to round 17 in
volume. Features distinguish capacity, schedule, survival, watering/fertilizer
interaction, current versus released value, and scenario availability. The
projection assumes no additional WATER or competing harvest before refresh.
It is **not** a guaranteed sales increment: future worker decisions, transport,
market reactions, crop survival, and prices can prevent that income.

The feature is evaluated independently of round 17. No automatic ensemble or
stacked policy is built. It receives the same test, screen, pilot and plotting
workflow, rather than a smaller second-stage appendix.

## Information availability and inference controls

Only own current legal observation fields and fixed mechanics enter descriptors.
No evaluator seed, future recorded action, reward, future shop draw or opponent
private inventory enters either policy. Current market quotes are not forecast
prices. Evaluator seed/config handling is in experiment.py, with separately copied
observations for each player. Learned thresholds/weights, target encodings and
model fits are absent. Any later learned selection must be trained in grouped
training episodes, never these pilot outcomes or a public leaderboard alone.

Null forks substitute the original expression and must match unchanged baseline
actions exactly. The screen checks those actions against the restored episodes.
In fresh games the null and control run on each candidate observation to check
that the feature is the only direct rule change. Day 29 is untouched apart from
the existing common final-sale correction. Later actions and opponent responses
can differ because states diverge; that is an outcome, not another rule edit.

## Registered evaluation and budgets

1. 348 fixed archived development observations per round (three coordinated
   episodes, every six callbacks before day 29). This is a sparse activation
   screen, not exhaustive evidence or feature selection.
2. Mechanics against the installed pinned engine: 480 arrival-decay cases in
   round 17; 288 two-path production cases in round 18.
3. If the screen activates, up to four fresh matched game pairs per round:

| Block | Seed | Candidate seat | Opponent |
|---|---:|---:|---|
| b1 | 2026091217 | 0 | LivestockPolicy('fertilizer') |
| b2 | 2026091217 | 1 | CropPolicy('full', max_hands=3) |
| b3 | 2026091218 | 1 | LivestockPolicy('fertilizer') |
| b4 | 2026091218 | 0 | CropPolicy('full', max_hands=3) |

This balances seats and opponent labels overall, but is not fully crossed.
Within-block treatment comparisons are matched; separate seat/opponent/seed
main effects are not identifiable from this design. Source-distinct opponents
are not necessarily strong leaderboard opponents. Their actual market and action
paths are retained to assess scenario coverage, not presumed diverse enough.

The seeds are screened against repository literals and registered seed metadata.
They are new development seeds within that checked inventory; unrecorded remote
history cannot be ruled out. The same blocks are intentionally shared by the two
rounds; round 18 is not independent confirmation of round 17. Both proposals and
blocks are frozen before those fresh outcomes are observed.

4. One pair per explicit cell, 180-second maximum (up to two complete games).
   Screening is capped at 120 seconds. Full callback cap: 500 ms; heartbeat: 10 s.
   Record and checksum complete games before proceeding. An interruption cannot
   erase a completed control; an incomplete game receives no endpoint score.
5. A negative own-cash, margin or match delta stops subsequent blocks in that
   round, retaining the existing conservative rule. Competitive match/margin
   interpretation is reported separately. Another round may proceed after a
   methodological no-activation or negative result, but not after a shared
   engine, source, data, or runtime integrity error.
6. No automatic adoption. A positive result requires further independent seeds,
   fully crossed opponent/seat stress testing, workforce robustness and a valid
   comparable submission. Never treat stopped blocks as zero effects.

At maximum: four shared controls plus eight candidates = 12 new games, not 16.
If round 17 stops early, round 18 creates only its missing matching controls.
No new jobs are launched in the assistant's environment or on AWS by this package
until the user explicitly runs the notebook cells. It contains no network writes,
Git commands that mutate history, installations, or submission commands.

## Remaining avenues, not declared exhausted

Adaptive crop mix and planting cohorts; state-dependent marginal staffing;
maintenance deadlines and joint service routes; land expansion with realistic
labor/capital opportunity cost; causal opponent-supply histories and uncertainty;
full worker-count support; stronger population evaluation; deployment artifact
verification. Raw feature counts and nice plots do not close any of these.
