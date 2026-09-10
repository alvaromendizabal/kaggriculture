# Legal-history supply research

## Research question

Can legally observable history identify rival market supply that a current-board
snapshot misses? The market/logistics experiment found rival same-product sales
during 174 of 343 product-holding events. Visible ripe crops are not the same as
already harvested goods: crops disappear from the board before workers deliver
them or the rival sells them. This study addresses that information gap before
another policy intervention is introduced. The prior findings are descriptive,
not proof that a hidden-inventory estimator will improve decisions.

The milestone is a development-only identification study using the existing 48
market/logistics episodes, not 48 new games. It implements a new causal feature
family, checks its mechanics against the official interpreter, and evaluates
whether its bounds contain evaluator-only ground truth. It does not train a
predictor, choose a new policy, consume validation/holdout seeds, change the
official score, or reopen completed experiments. Notebook 02 remains open and
its three previously executed studies remain unchanged.

## Domain mechanisms and information boundaries

The pinned interpreter is the primary specification. At each callback both agents
choose actions; the engine applies farm work, processes market orders, consumes
town demand, applies crop decay and, when scheduled, performs the night refresh.
The next observation is the first point at which the previous action's public
consequences are available. A feature emitted at callback t may use observation
t and its own previously submitted action, never the opponent's simultaneous
action or observation t+1. [1]

Two features that look similar require different claims. Public market inventory
change plus known consumption identifies aggregate net trade in the preceding
turn. It does not universally identify gross rival sales. Wheat and fertilizer
can be bought as products, so buying and selling may cancel in the same observed
inventory change. Furthermore, sales at a quote of one coin do not increase market
inventory. Treating zero net change as zero rival selling would therefore be an
incorrect inference, not a useful imputation. [1]

Seven products cannot be bought: carrot, tomato, strawberry, melon, egg, milk and
wool. Their previous-turn sales can be bounded using stock conservation. When
the post-market quote is above the floor, market inventory was monotonically
increasing through those sales and the known own-sale quantity can be subtracted
exactly. At the floor, the calculation returns a range, not a fabricated exact
quantity. Own sale quantities are reconstructed from the agent's own legal
private inventory and submitted action, including same-turn deposits, repeated
orders, the ten-order cap and atomic planting-request validation. [1]

Public crop disappearance is also ambiguous. DIG can remove a crop without
collecting anything. Decay, death and night refresh can change the same tile.
The extractor therefore computes a possible-collection upper bound, not a
harvest label. Only workers already located on a tile can harvest it in that
turn; moving and harvesting are different actions. Co-located workers can water
before another harvests, and three can fertilize, water and harvest in sequence.
Those possibilities must be included even when the rival's private fertilizer
stock is unknown. [1]

## Set-valued state representation

Partial-observation control distinguishes the observed state from a belief over
unobserved state. Belief-state reductions are a formal foundation for decision
making with incomplete information. They do not make an arbitrary rolling average
a sufficient statistic or turn a hand-written scenario weight into a calibrated
probability. [2] This implementation deliberately calls its output a bound, not
a posterior distribution.

Set-membership estimation propagates feasible sets under bounded uncertainty and
intersects them with measurement and physical constraints. de Paula and colleagues
develop substantially more general constrained-zonotope methods and discuss how
set approximations introduce conservatism. [3] The application here uses simple
scalar conservation bounds, not their algorithm or its experimental guarantees.
The methodological connection is explicit uncertainty propagation; the farming
formulae below are derived from this interpreter.

Let I be public market inventory, D the consumption scheduled from the previous
observation, and q_own the known own-sale quantity for a non-buyable product.
The observed total effective trade is `flow = I_next + D - I_previous`. Below the
price floor threshold, rival gross sales equal `flow - q_own`. At a floor-censored
transition, a conservative lower bound is `max(0, flow - q_own)`; the upper bound
is limited by both possible available rival stock and the 100-unit shed capacity.
Wheat and fertilizer expose net-flow histories but have explicit zero support
masks for gross-sale and hidden-stock estimates.

The hidden-stock upper bound starts at zero only at the genuine initial callback,
where the default game initializes private inventories empty. Before incorporating
sales it increases by possible collection. It then decreases by the lower bound
on rival sales. Night delivery empties carried inventories into a capped shed,
so the next stock upper bound is additionally capped at 100. Discarded goods only
make this upper bound looser. The lower stock bound stays zero: this first model
does not infer that ambiguous disappearance guarantees retained inventory.

This is a per-product bound. It does not assert that all product upper bounds
can occur simultaneously: crops compete for workers and share storage. It also
does not identify the split between shed and carried goods, the timing of the
next delivery, or whether the rival plans to sell. A positive upper bound is a
possible supply risk, not an expected sale. The future policy study must respect
these distinctions instead of always substituting the upper bound as a forecast.

## Candidate schema

The new bank contains 333 candidate descriptors, separate from the earlier
933-column bank. Their concatenation would have 1,266 columns, but this milestone
does not claim a jointly screened or policy-validated 1,266-feature representation.

| Component | Descriptors | Role |
|---|---:|---|
| Previous transition, nine products | 99 | Availability, effective net trade, known demand, quote change, sale support, sale lower/upper bounds, identification, floor censoring, possible harvest and stock upper bound |
| Rolling windows of 4, 12 and 24 turns | 216 | Observed count, trade sum/dispersion, cumulative quote change, sale bounds, possible collection and identification frequency |
| Confirmed-sale recency | 18 | Whether a positive lower-bound sale has been seen and its age |
| Total | 333 | Provisional candidates, not 333 demonstrated improvements |

Window statistics only summarize observations already seen. Their count reports
how much history is available, preventing a short opening window from being
mistaken for a full day. Sale recency is paired with a seen mask, so its initial
zero cannot be interpreted as a just-observed sale. Stock-related zeros for the
two unsupported products must likewise be read with their support masks.

## Development replay and audit design

All 48 original games are reused: six development seeds, both player seats and
the four registered delivery/holding arms. Each candidate trajectory has 719
callbacks. Existing file hashes, semantic episode hashes, engine fingerprints,
source fingerprints and the full seed-seat-arm grid are verified before the
analysis accepts a trace. No turns from an episode are assigned to separate
training or evaluation folds; there is no fitting in this study.

The causal module receives one candidate observation, emits its features, and
records only that candidate's selected action. Only after those operations does
the evaluator inspect the rival's private record. The evaluator checks every
supported product's stored quantity against the stock bound and previous sales
against the sale interval. Those checks are assertions: a violation fails the
analysis instead of being averaged away into a flattering mean error.

Coverage diagnostics distinguish actual positive stored stock, a positive upper
bound, positive upper bounds when stock is empty, exact bounds, average excess
and maximum excess. A separate count identifies positive hidden stock when no
ready crop/product is visible on the board. That count addresses the gap in the
earlier visible-wave representation; it is not a precision estimate for a future
sale forecast. Results are retained by seed, seat, arm and product as well as in
aggregate, making concentration and inactive families visible.

Screening identifies constant columns and exact nonconstant duplicates across
the replayed development rows. These findings are specific to these trajectories:
a constant livestock history in crop-only episodes is a coverage warning, not a
domain-wide reason to reject livestock. No importance ranking, target encoding,
SHAP value, permutation score or official-metric attribution is claimed without
an appropriate fitted model and grouped evaluation.

Serialization is checked at day boundaries and the final callback. The saved
state contains a whitelist of legal observation fields, bounded history, known
own-action consequences, supply bounds and recency state. A checksum and contract
identifier reject accidental corruption and incompatible formats. Tests cover
prefix behavior, player-swap symmetry, additional hidden metadata, missing actions,
skipped turns, cold starts, reset behavior, concurrent floor sales and calendar
boundaries. Serialized-state size and feature-plus-action bookkeeping latency
are measured locally; neither is a competition runtime certification.

## Measured findings

The full replay emitted **34,512 vectors of 333 features**. All 241,584 supported
product/callback stock checks and 241,248 preceding-transition sale checks passed
with zero bound violations. The audit reused all 48 games and ran zero new games.
There were 1,488 successful serialized round trips; the largest sampled serialized
state was 53,857 bytes. Exact runtime measurements are in the machine-readable
report because local timing depends on concurrent processes and is not a Kaggle
runtime guarantee.

| Product | Stored-positive callbacks | Stored-positive with no visible ready yield | Empty but stock upper bound positive | Floor-censored transitions |
|---|---:|---:|---:|---:|
| Carrot | 1,602 | 360 | 72 | 0 |
| Strawberry | 1,954 | 180 | 6,062 | 0 |
| Melon | 2,856 | 984 | 19,536 | 1,812 |
| Tomato, egg, milk, wool | 0 | 0 | 0 | 0 |

Each individual product has 34,512 observed callbacks and 34,464 preceding
transitions. Repeated turns and both seats are correlated; these are diagnostic
counts, not independent Bernoulli trials. No significance claim is made from the
large number of callbacks. The report preserves the six development seed groups.

The new representation contains possible supply where the visible-wave model
would contain none: **1,524 product/callback observations** had positive hidden
stock without visible ready yield. However, a possible-supply bound is not an
accurate point estimate. Melon produced 19,536 false-positive possible-stock
callbacks and a maximum excess of 105 units; strawberry produced 6,062 such
callbacks and a maximum excess of 36. The bounds accumulate uncertainty from
unidentified floor sales and ambiguous collection/retention. Treating these upper
bounds as the most likely rival stock would be methodologically unjustified.

The sale audit identified all 568 carrot and 3,640 strawberry units in the
evaluated transitions. For melon, actual sales totaled 8,784 units, while the
causal lower bounds summed to only 3,810. Floor censoring is therefore material
in the actual trajectories, not just a theoretical corner case. The wide melon
intervals need additional legal evidence or calibrated uncertainty before a
history-conditioned market rule can be trusted.

Of the 333 candidates, **178 varied and 155 were constant**; there were **12 exact
nonconstant duplicate groups**. All remain provisional, with zero final retained
or rejected predictors. The four inactive products still need on-policy coverage,
and the wheat/fertilizer stock masks remain unsupported by design. No fitted
importance scores, cross-seed predictive gains or official win-rate improvements
were estimated. The 933-column earlier bank and the new 333-column bank have not
been jointly screened or jointly ablated.

## Interpretation and next decision

The machine-readable output is `reports/market_history_research.json`; the
reproduction entry point is `scripts/analyze_market_history.py`. Original raw traces stay private and no new
paid cloud experiment is required for this milestone.

Passing conservation checks would establish that these descriptors respect the
tested information boundary and contain relevant past supply information. It
would not establish a win-rate improvement. The next policy experiment should
separate history information from a more conservative selling rule: compare a
frozen no-history action rule with the same rule given historical supply bounds,
then examine their interaction. Use fresh development seeds and opponent variety,
keep seed/seat clusters together, register decision and budget limits before
running games, and retain the untouched validation and holdout pools.

Important missing relationships remain. Wheat/feed and fertilizer need joint
buy/sell and consumption bounds. Stored-versus-carried stock requires delivery
and position constraints. Crop disappearance may be disambiguated further by
the complete public transition, worker assignments and cash changes. Belief
calibration, probabilistic scenarios and opponent-policy adaptation require
grouped development fitting and out-of-seed checks. Livestock, land expansion,
crop mix, joint routing and robust feature-family ablations remain open in the
completion ledger. None of these can be declared exhausted by this replay alone.

## Sources

1. Kaggle. [Official Kaggriculture interpreter](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py).
   Pinned package 1.32.7; interpreter SHA-256
   `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.
   Domain claims refer to that pinned file, not an unverified private deployment.
2. Feinberg, E. A., Kasyanov, P. O., and Zgurovsky, M. Z.
   [Markov Decision Processes with Incomplete Information and Semi-Uniform Feller Transition Probabilities](https://arxiv.org/html/2108.09232v6).
   Version 6, 2022. Used for the belief-state distinction, not a claimed game solver.
3. de Paula, A. A., Raimondo, D. M., Raffo, G. V., and Teixeira, B. O. S.
   [Set-based state estimation for discrete-time constrained nonlinear systems](https://arxiv.org/html/2211.05912v1).
   2022. Used for set-valued estimation and approximation conservatism; CZDC is not implemented here.
