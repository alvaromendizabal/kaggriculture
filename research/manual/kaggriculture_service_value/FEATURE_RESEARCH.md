# Two independent service-value feature investigations

## Status and evidence boundary

These are implementations and tests **prepared for user execution**. No new tests,
notebooks, component fixtures, or experiments have been executed by the assistant.
Static source inspection is not test execution. Prior results come from the
uploaded artifacts, with the accounting in RESULTS_REVIEW.md.

The immediate milestone is two bounded archived screens. The paired-game driver
is supplied, but both notebooks stop before games. A later experiment requires
review of actual screen evidence and an explicit screen-report hash on the CLI.

## Primary research sources

1. Official Kaggriculture interpreter:
   https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
2. Official game specification/readme:
   https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/README.md
3. Google Route Optimization documentation, time-window semantics:
   https://developers.google.com/maps/documentation/route-optimization/concepts/time-windows
4. Aziz et al., Multi-Robot Task Allocation — Complexity and Approximation:
   https://arxiv.org/abs/2103.12370

Sources 1–2 define the mechanics. Sources 3–4 motivate separating service time,
deadlines, and coupled resource allocation; they do not prove that our proposed
scoring rules improve Kaggriculture. No verified leading-solution writeup or
current top leaderboard rating was retrieved. Do not attribute these features
to a winning solution. The local engine must match the recorded 1.32.7 manifest;
current public master is not silently substituted into experiments.

## Round 19 — Collection-to-sale completion time

**Question.** Does the outbound-only task effort term undervalue the return and
deposit needed to convert collected products into banked money?

The pinned FeedPolicy scores a job using `job.priority / (1 + travel)`. The
numerator, candidate tasks, reservations, distance geometry, and min-key/tie
selection remain unchanged. Only HARVEST and COLLECT_FERTILIZER jobs can use the
new denominator, only before the final day.

Let d be outbound distance, r the distance from the resource to shed access,
N the callbacks until the next refresh, and s the current decision step.
Manual HARVEST at offset d, then movement and DROP, allows SELL at offset
`d + 1 + r`. Automatic night deposit follows that turn's market; its first sale
opportunity is offset N. The manual path is admitted only before the nightly
reset and terminal boundary. The night path requires collection before reset
and an actual later selling callback. The minimum admitted sale offset plus one
is the candidate score denominator. Unavailable scenarios retain the original
score and have explicit masks; they are not labeled worthless.

**Important assumptions.** This is conditional elapsed time, not labor utilization
or a guarantee of deposit capacity. It does not forecast competitor trades,
future prices, intervening decay or task allocation. It can undervalue efficient
multi-collection routes. Existing guardrails and the outcome experiment, not a
claim of optimality, decide its usefulness. Overnight automatic deposit is
represented; it is not incorrectly treated as a same-callback sale.

**Representation.** 32 numeric descriptors per worker/resource/operation plus
12 state summaries. They include inbound/outbound effort, both banking paths,
time masks, current goods, shed room, current cargo, and alternative-worker
access. Several fields are primitives or alternative views of the same
quantity, not 44 independent novel signals. Only the candidate denominator
enters the changed score; other fields are diagnostics.

**Tests.** 32 round-specific tests plus 32 shared tests, all supplied unexecuted.
The installed-engine gate compares movement, collection and DROP primitives;
it also checks both seats' automatic deposit versus market ordering. Artificial
fixtures do not count as games or metric evidence.

## Round 20 — Survival-critical maintenance completion slack

**Question.** Does the current urgency score distinguish a critical task that a
worker can finish comfortably from one that just fits before the next refresh?

The pinned policy already boosts death/escape prevention. This round does not
claim that urgency was absent. It tests the additional representation of slack
after travel and service. No WATER/FEED job is removed. No ordinary watering,
feeding, crop-renewal, purchasing or hiring rule is disabled.

For an unserviced plant/animal with dry/unfed streak >=1, the next refresh is
survival-critical. Let d be outbound distance and N callbacks until refresh.
`slack = N - (d + 1)`. For a feasible critical job whose resource is available
(carried wheat for FEED), multiply the existing score by `N / (slack + 1)`.
All other scores remain unchanged. There is no next-refresh bonus on the final
day. The multiplier is in [1,24] on the documented domain and is an engineering
hypothesis, not a learned estimate or optimal scheduling rule.

The extra urgency may misallocate workers by favoring long trips, can duplicate
information in existing priorities, and need not improve wins. These are reasons
to test it independently, not promises of benefit. Ready alternative workers,
held production and remaining nominal events are logged but not added as extra
hidden score terms. Future care/production values remain conditional context.

**Representation.** 32 numeric worker/task descriptors plus 12 state summaries:
clock, completion effort, deadline masks, criticality, carried versus stored
feed, nominal production/headroom, feasible alternative workers and resulting
score factors. No job deletion, new fitted coefficients or policy stacking.

**Tests.** 32 round-specific tests plus the same 32 shared tests, all unexecuted.
The installed-engine gate uses five species and independent WATER/FEED resource
and survival cases. It does not pretend to prove an urgency heuristic correct
from the fact that mortality mechanics match.

## Screening design and stopping boundary

Each round uses the three preserved coordinated development episodes. Sampling
is every third callback plus all callbacks at hours 20–23 on days 0–28:
319 states per source, **957 per round**. The different schedule is motivated by
the previous screen's missing late-day coverage, not by inspecting held-out
outcomes. All sources remain heavily reused development evidence.

For each sampled state: reproduce archived control action; reproduce the null
fork; check input immutability; measure complete callback time; compare immediate
farm and market commands; record state and option features. No feature fitting,
labels, cross-validation tuning or official metric estimate occurs here.

The two screens are independent and may both run in sequence without selecting
anything from the first. An integrity/runtime exception stops work and must be
reviewed. No action changes produces STOP_NO_ACTION_ACTIVATION for that round.
Action changes produces REVIEW_REQUIRED_BEFORE_GAMES, not permission for Run All
to launch games. A row count or passing unit test cannot bypass this boundary.

The 180-second cap includes tests, preflight, mechanics and screening. Completed
sources are stored with code/config/engine/data fingerprints. RSS is monitored
for the worker with an 8 GiB limit; fit count and full-game count are zero. Ten
second heartbeats include the last completed-work event and measured worker RSS.

## Prepared endpoint ablations — not the current run

After inspecting an activated screen, the provided driver can run one matched
block at a time. Control versus candidate differ only in the registered score
term. The opponent receives only its own live observation and responds anew.
The evaluator owns the seed; it is never exposed as a feature. Blocks use the
previously proposed but unexecuted 2026091217/2026091218 seeds, both seats and
source-distinct crop/livestock opponents. Exact definitions are in PROTOCOL.json.
The preflight checks available repository/evidence seed records, not unrecorded
account history. This is balanced development, not a fully crossed factorial
or an untouched final holdout.

Shared controls are reused only with identical fingerprints and matched initial
states. Maximum eventual work is four blocks per round, up to 12 distinct games
across both, one pair per explicit invocation. No automatic next block. Each
pair has a 180-second budget and all actors a 500 ms measured callback gate.
Incomplete games are not accepted endpoints; completed controls survive a later
failure. A single negative pair stops expansion under the preserved conservative
cash guard. This is a resource decision, not a universal scientific rejection.

Report local win/draw/loss separately from own coins and coin margin. The prior
conservative guard additionally forbids decreased own cash or margin; it is not
the official Kaggle rating. Do not pool turns as independent samples. With two
seed groups, report paired values and sensitivity, not spurious narrow confidence
intervals. Shared controls make the two rounds correlated. No automatic promotion
and no feature combination is authorized by an exploratory result.

## Remaining gaps and next roadmap

The complete baseline still rejects either farm with >3 hired hands. These new
extractors do not silently truncate a longer own-worker list, but that does not
repair or certify the complete agent. Submission packaging must resolve this
separately, preserve rule/runtime compliance, and produce a user-run valid agent
submission and receipt. A CSV prediction file is not assumed for this game.

No comparable official rating is recorded. 3140.0 is the user-supplied target;
local coins and fractions cannot be mapped onto it. Before more tuning, review
activation in both rounds, choose at most one justified outcome block, inspect it,
then decide. Broad validation, uncertainty, workforce support, and submission
measurement must not be postponed indefinitely behind candidate generation.
