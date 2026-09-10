# Livestock, feed and fertilizer: registered development study

This study addresses the 78 animal state/feed-care descriptors that never varied
in the preceding crop-only supply study. It adds 234 resource descriptors and a
fixed mixed farm that can activate all three species, feed purchases, care banks,
renewable manure, ongoing crops and treatment opportunity costs.

The active bank has 1,500 descriptors: 1,266 supported previous descriptors plus
234 new ones. The 42 earlier cash-bound descriptors require own sale-only product
trading. Because the new farm buys wheat, those 42 are explicitly excluded from
this study, while remaining documented project candidates. They are not silently
given invalid values or rejected as unhelpful.

## Mechanisms and hypotheses

The pinned interpreter is authoritative. A surviving unfed animal can produce a
base unit, but feeding preserves a banked care bonus at its production event.
Two consecutive unfed refreshes cause escape. CARE enters the bank *after* that
night's production; its return must be timed to a later event. Overflow can erase
that return. Fertilizer is a single renewable slot per animal, not an accumulating
daily inventory. Collection must be routed, and application competes with sale.

| Component | Testable hypothesis | Availability and limits |
|---|---|---|
| Selective feed | Rescue and bonus-conversion deadlines reduce wasted wheat/work | Visible fed/unfed state and production calendar; wheat source and purchase curve |
| Selective care | Bank headroom, conversion date and terminal delivery identify wasted care | Conditional future survival, feeding and collection; current prices are scenarios |
| Fertilizer allocation | Net treatment gain can exceed manure sale and displaced work | Exact seven-day single-tile counterfactual; fixed water/collection continuation |

Animal layout, crop layout, acquisition, staffing, transport and harvesting rules
are fixed across arms. Goose/cow/sheep targets are two each. Crop targets are
four wheat, three strawberry and three tomato tiles in the initial quadrant.
The work opportunity charge is fixed at 8 coins/action; it is an assumed value,
not a real expense or fitted estimate. No outcome-driven parameter search occurs.
Treatment scenarios include travel delay, watering displaced by fertilization,
inclusive fertilizer duration, yield capacity and feasible terminal banking.
They do not predict unknown shops, future market quotes or competing worker tasks.

## Design fixed before registered outcomes

Four fresh development seeds (1401–1404), both seats, two opponents and four arms
give 64 games. Opponents are frozen MarketPolicy(10) and the new routine mixed-farm
reference. Arms are routine → selective feed → selective care → fertilizer.
Primary contrasts are feed−routine, care−feed, fertilizer−care and fertilizer−routine.
These are sequential component contrasts, not factorial main effects.

Primary outcome is match score: win=1, tie=0.5, loss=0. Coin margin, feed/care work,
manure application/collection, escape, missed manure slots, production overflow and
discarded units diagnose the mechanism. Both seats/opponents/arms stay within a
seed cluster. Exploratory 95% percentile intervals resample four seed means 4,000
times with seed 4401; four clusters cannot support strong generalization claims.
Initial seed pairing does not force identical later shops after policy-induced
RNG divergence. No validation/holdout games, final fitting or submissions occur.

Mechanism preflight uses separate seed 61. One action-only run checked species and
task activation; an instrumented preflight checks schemas, accounting and restart.
Failures before registration included a shallow-copy mutation, a price-impact
expectation, a history serializer API mismatch and terminal shared-field extraction.
They were corrected before
collecting any 1401–1404 outcome. Preflight win/loss is not a policy-tuning signal.

## Research basis

Hasturk et al. distinguish immediate known costs from uncertain continuation while
enforcing constraints in inventory routing. We transfer that separation to exact
farm/market mechanics and conditional tile rollouts; their learned RL/optimization
system is not implemented here. [Primary paper](https://arxiv.org/abs/2503.05276).

Ruiz-Hernandez et al. analyze maintenance scheduling using restless bandits. The
useful analogy is state-dependent service urgency under scarce work capacity.
Shared wheat, workers and prices break independent-arm assumptions, so we make
no claim of an optimal Whittle index or of satisfying indexability.
[Primary paper](https://arxiv.org/abs/2401.14055).

Agarwal et al. motivate reporting finite-run uncertainty and performance spread.
Here the independent unit is the seed cluster, not 719 correlated callbacks.
Intervals and mechanisms remain development evidence rather than leaderboard
predictions. [Primary paper](https://arxiv.org/abs/2108.13264).

## Recovery and acceptance

Source, engine, runner, protocol and all job identities are hashed at registration.
Each batch starts at most eight new games or 240 seconds of new work, finishing
an in-progress game atomically. Valid checkpoints are reused; mismatched lineage
or corrupted bytes fail. Every completed game is written locally before its
private versioned S3 upload. A transfer failure preserves the completed work.

Every callback must be consecutive and observation-safe. A separate replay must
reproduce actions, diagnostics, all sampled vectors and periodic policy/history
restores. Evaluator-only paired private views audit actual market execution,
feed and fertilizer consumption, collection, sales, losses and terminal inventory
for each product. Public history bounds are tested against truth only after
features/actions have been reconstructed. All four previous studies remain intact.

Schema, finite values, variation, exact duplicates, correlation, action activation,
paired component results and runtime are reported separately. No candidate is
called predictive merely because it varies, and no family closes solely because
this study completes. Land, joint routing, worker assignment, adaptive crop/herd
mixes, opponent diversity and robust continuation values remain research tasks.
