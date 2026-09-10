# Study 3: market timing × delivery opportunity cost

Design registered before the 48 outcome games. This document describes a feature-policy
experiment, not a final agent, a learned demand model or a promise of leaderboard rank.

## Hypotheses and fixed interventions

Study 2 showed that eliminating storage loss can still hurt competitive outcomes. A
delivery action consumes work that could harvest or water a more valuable plant. Its
value also depends on when the opponent can supply the shared market. We therefore
test these coupled mechanisms rather than adding arbitrary product interactions.

| Factor | OFF | ON |
|---|---|---|
| Delivery | Frozen maturity baseline's farm commands | Divert carried goods only when conditional early-sale value exceeds overnight-sale value plus estimated displaced crop work; preserve local harvest and deadline-critical watering; bound overflowing deposits |
| Market timing | Sell all observable shed products immediately | Enumerate every integer current sale quantity and compare a remaining-stock liquidation after at most four callbacks under quiet and visible-rival stress scenarios |

The fixed baseline is `RelationshipPolicy("001")`; the frozen opponent is
`RelationshipPolicy("101")`. The all-off action is exactly the baseline action. All
four arms use three hired hands and retain the original seed purchase/hiring decisions.
There is no tuning of scenario weight, horizon, opponent or crop scores after outcomes.

Quiet path: own immediate sale → known-shop consumption → remaining own sale.
Stress path: own immediate sale → eligible visible rival supply → known-shop consumption
→ remaining own sale. The fixed score averages both scenarios with weight 0.5 each.
These weights are **not calibrated probabilities**; the stress path is not an exact
prediction of the rival's hidden inventory, worker allocation or order timing. Delivery
uses a maximum positive new-crop value-per-work-action proxy, not a global route optimum.

All sale curves account for per-unit price impact and the non-accumulating $1 floor.
Concurrent same-product sales are implemented and parity-tested separately; the policy
does not pretend the rival always uses the same order slot. Holds expire after four
callbacks; equal values prefer earlier banking. Sale timing is forced before a nightly
deposit and at the last legal sale callback, step 718. The nightly automatic deposit
happens after market trading, so it is not available for an earlier sale.

## Feature bank

`market_features.py` adds 315 descriptors to the prior 618, giving 933 fixed columns:

| Block | Count | Availability / interpretation |
|---|---:|---|
| Nine-product post-decision inventory | 63 | Visible own/rival ripe supply, own shed/carry, capacity-limited conditional quantity, optimistic rival arrival, current liquidation value |
| Nine products × three horizons × eight fields | 216 | 4/12/24-callback masks; known-shop demand; demand-only inventory/price; quiet/stress revenue; rival penalty; holding premium |
| Four worker slots × nine fields | 36 | Presence mask, carried units, shed travel/deposit requirement, slack, immediate/night scenarios and shared overflow pressure |

The 24-callback descriptor horizon is not the policy's four-callback maximum hold.
Unavailable terminal horizons and absent workers are masked. Rival supply envelopes
use only currently harvestable public tiles and current workers, never unseen carry or
shed stocks. Independent jobs may overlap; later watering, growth, decay and unknown
shop additions are excluded. These are explicit conditional descriptors, not forecasts.

## Frozen evaluation boundary

`configs/market_research.json` specifies six **new development** seeds 1201–1206,
both seats and arms 00/01/10/11: 48 games. They are disjoint from previous development,
validation and holdout pools. Six whole seed clusters—not turns or individual seats—
are resampled 4,000 times for descriptive intervals. Main contrasts are average
ON-minus-OFF; the pair contrast is a difference-in-differences. Local win + half tie
is primary; banked coins, margin, waste and minimum cash are diagnostic. Intervals do
not correct for every historical hypothesis or establish broad opponent generality.

Every full game has 719 candidate callbacks and 181 feature samples. All callbacks are
recorded and observed by causal history, even when matrices are sampled. Checkpoints
are keyed by source, engine, protocol, seed, seat and arm; valid results are reused.
The run is bounded to 48 games / 1,020 research seconds inside a 1,200-second setup
process. Completed episodes upload immediately. This is a process limit, not an AWS
account spending cap. Raw observations and matrices remain private.

Independent replay checks recompute all sampled feature vectors, observable sale
availability, ineffective farm actions and exact product conservation. Registry screens
measure finite values, variation, duplication and correlation. They do **not** select
predictive features. Negative effects remain published. The feature-completion gate
stays closed regardless of which of these four arms wins locally.

## Pre-run mechanical corrections

Before registered outcomes, tests corrected default market-parameter handling (the
default engine omits the optional override dictionary) and an invalid test fixture that
fabricated already sold goods as still held. No outcome-driven policy change resulted.
Two deterministic smoke games use seed 43, outside all registered evaluation pools.
See [domain research](domain_research.md) for sources and the remaining research agenda.
