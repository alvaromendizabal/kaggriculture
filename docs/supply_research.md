# Cash-constrained rival supply: identification before prediction

This milestone asks two different questions: can public cash tighten our legal
opponent-stock bounds, and does that extra information improve decisions under
a fixed policy? A valid bound is not automatically a useful predictor. All
features remain provisional and the feature-completion gate stays closed.

## Why this relationship matters

The previous holding experiment lost coins on all six development seed clusters.
The subsequent 48-game history audit found 1,524 product/callback combinations
with actual rival stock but no visible ready crop. However, simply accumulating
possible harvests made melon upper bounds increasingly conservative: the price
floor concealed sales, leaving stock warnings even after inventory was gone.
Those findings are development evidence motivating this study, not validation.
See [the earlier audit](market_history_research.md).

The important domain is the actual simulation, not real-world crop biology.
Market orders, storage, public accounting, simultaneous trading, crop maturation
and the finite season determine what can be inferred. Mechanics are checked
against the pinned [official interpreter](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py).
The package is `kaggle-environments==1.32.7`; all relevant engine file hashes are
included in each checkpoint. The mutable upstream link is explanatory, not the
reproducibility pin.

## Research connection and scope

Set-membership estimation combines a model-propagated feasible state set with
measurement constraints. De Paula and colleagues study constrained nonlinear
systems and show why interval propagation can become conservative. Our useful
adaptation is to intersect stock-flow feasibility with public-money feasibility.
We implement scalar integer bounds, **not** their constrained-zonotope/DC
algorithm, and inherit none of that paper's numerical performance claims.
[de Paula et al., 2022](https://arxiv.org/html/2211.05912v1).

Recent censored-demand research reinforces the distinction between a measured
quantity and the underlying latent quantity. Xu and colleagues study sales
limited by adversarially supplied inventory, with explicit assumptions on demand
and noise. Kaggriculture instead censors the market inventory response at its
price floor and includes a strategic simultaneous opponent. The censoring lesson
transfers; their demand model, pricing algorithm and regret guarantee do not.
We therefore do not treat a zero observed market change as a zero rival sale.
[Xu et al., 2025](https://arxiv.org/html/2502.06168v1).

Small-run evaluation can support misleading rankings if uncertainty is hidden.
We report paired seed-cluster effects, outcomes by opponent, all seed differences
and descriptive intervals. This is an application of the evaluation principle,
not a reproduction of an RL benchmark or an implementation of `rliable`.
[Agarwal et al., 2021](https://arxiv.org/abs/2108.13264).

## Derivation and information contract

Let the rival's observed cash change be `delta_cash`, product revenue be `R_p`,
and non-product expenditure be `C`. Wheat and fertilizer trading contribute
signed net cash; other products can only be sold. Then:

`delta_cash = sum(R_p) - C`.

Publicly added land and same-day increases in the hiring counter give a known
minimum `C_min`. Unseen seed, animal and other purchases are not assumed absent.
Consequently `sum(R_p) >= delta_cash + C_min`. At the night reset, the hiring
counter cannot identify that turn's hires, so its lower-bound contribution is
zero. Under-counting hidden expenditure weakens identification; inventing it
would make a bound unsafe.

For each non-buyable product `p`, let `U_q` be a safe upper bound on revenue from
every other product. The residual revenue requirement is:

`required_p = delta_cash + C_min - sum(U_q for q != p)`.

The initial quote is an upper bound on the price of each sale of `p`, because
neither player can buy that product. Therefore at least
`max(0, ceil(required_p / initial_quote_p))` units must have been sold. Intersect
that lower bound with the existing public-flow sale interval. Propagate the
additional identified sales through the stock balance. This is an outer bound,
not exact attribution of all cash to a product. Individually maximizing each
other product ignores their shared shed capacity, which is conservative.

The implementation requires our own agent to make **no `BUY_PRODUCT` orders**.
It does not assume the opponent follows one of our crop policies. The opponent
may buy wheat, fertilizer, seeds, animals or land. Our selected policies satisfy
the restricted own-action contract; unsupported own product purchases fail
explicitly rather than silently producing optimistic bounds.

### Buyable-product ambiguity

Net inventory change alone does not always identify net trading cash. A rival
can sell fertilizer before our own sales depress the price, then buy it back
more cheaply. The rival's net quantity is zero but its cash gain is positive.
This counterexample is reproduced against the official market implementation
in a regression test.

If we do not trade that product and the rival cannot reach the price floor,
its buys and sells telescope along the discrete price curve, identifying signed
net cash. We conservatively check that even a full 100-unit starting shed cannot
reach the floor. Otherwise we use the revenue from liquidating a full initial
shed before our sales as an upper bound. Our own sale-only activity can lower
prices, not raise them; buy/resell cycles cannot exceed that initial liquidation
bound. The identification mask is exposed alongside the numeric value.

### Storage and action ordering

The stock deduction must happen **before** the night storage cap. Subtracting a
newly inferred sale from a bound already clipped at 100 can exclude the true
stock: a pre-cap balance of 150 minus 40 still clips to 100, not 60. A dedicated
test covers this case. Own sale bookkeeping reproduces the farm-before-market
order, atomic insufficient-seed blocking, repeated sales and the ten-order cap.
Private rival inventories are used only after extraction, by the evaluator.

## Feature inventory

| Family | Added descriptors | Meaning |
|---|---:|---|
| Public cash accounting | 3 | Availability, observed cash change, known minimum spend |
| Cash-constrained supply | 35 | Seven products × stock upper, sale lower/upper, newly identified sales, revenue upper |
| Buyable cash ambiguity | 4 | Wheat/fertilizer signed-revenue upper and identification mask |

The joint bank has 1,308 candidates: 933 previous observation/relationship/market
descriptors, 333 legal-history descriptors, and these 42. The count is an audit
dimension, not evidence of predictive quality. The executed study screens the
entire joint bank for finite values, schema stability, variation, exact duplicates
and high Spearman correlation. No constants are called unimportant merely
because these particular policies never activate them.

## Preregistered decision experiment

The machine-readable design is [supply_research.json](../configs/supply_research.json).
Registration freezes source, interpreter, runner and all 64 episode identities
before any fresh development outcome is inspected. The source and registration
are archived to versioned private S3 before execution. Prior source files remain
unchanged, preserving the identity of studies 1–3 and the history audit.

| Arm | Holding information | Other decisions |
|---|---|---|
| `bank` | Sell all available product | Frozen `MarketPolicy("10")` |
| `visible` | Visible rival crop supply | Same delivery and production rules |
| `history` | Visible crop supply + loose legal-history stock upper | Same rules |
| `cash` | Visible crop supply + cash-tightened stock upper | Same rules |

`bank` is action-identical to frozen market arm `10`; `visible` is action-identical
to frozen arm `11` in full-season regression tests. Later observations may still
diverge across arms because holding changes cash and subsequent decisions. This
is an information intervention within fixed decision rules, not identical future
trajectories or an isolated direct-effect estimate.

The holding horizon remains at most four actions and the stress-scenario weight
stays at 0.5. Neither is fitted in this study. A conservative stock upper is a
stress input, **not a calibrated forecast**, and a tighter bound need not improve
this particular two-scenario rule. That possibility is part of the experiment.

The grid uses development seeds 1301–1304, both seats, and two frozen opponents:
`RelationshipPolicy("101")` and `MarketPolicy("10")`. These are strategically
different references but share crop-policy ancestry; they do not represent the
whole competition. All prior development, validation and holdout seeds are
excluded. No random split of callbacks is permitted.

The primary outcome is local match score: win 1, tie 0.5, loss 0. Coins and coin
margin are supporting diagnostics. Registered contrasts are visible−bank,
history−visible, cash−history and cash−bank. Within each seed, both seats and both
opponents remain together. We average paired differences within seed and use
4,000 bootstrap resamples of the four seed clusters, with fixed bootstrap seed
3301. Opponent-stratified contrasts are also descriptive. Four clusters do not
support a leaderboard guarantee, a reliable population ranking, or a
multiple-comparison significance claim.

Pairing fixes the initial simulator seed, not every future random event. Different
actions can change random-number consumption and later shop realizations. The
registered contrast therefore measures the total policy effect under a common
starting seed, not a counterfactual with all subsequent randomness held constant.

## Execution, recovery and audit

The canonical runner supports `plan`, `register`, `batch`, `summarize` and
`upload`. Each batch starts at most eight new games and checks a 240-second
elapsed limit before starting another game. That is a scheduling check, not a
hard per-game deadline. A completed game is atomically checksummed, revalidated,
and uploaded immediately to private, versioned S3. A failed upload stops progress;
the locally completed episode can be uploaded on restart without playing it
again. Signed URLs and raw observations are never committed.

Reuse requires matching source/engine/protocol lineage, semantic checksum,
719 consecutive callbacks for each player, 181 sample vectors of 1,308 features,
completed official statuses, consistent match outcomes and exact product
conservation. A corrupted checkpoint is an error, not a cache miss. Policy state
is serialized and restored every 24 callbacks plus the last callback, exercising
recovery inside every episode. Episode recovery is atomic: an interrupted,
unfinished game may need replay; completed games must not.

Independent post-run auditing replays legal observations, reconstructs features,
checks actions and verifies tighter bounds against evaluator-only hidden truth.
Published summaries retain hashes and episode keys; private trace and matrix
artifacts stay in S3. The source-locked runner and verified remote versions make
the work restartable without relying on this conversation's memory.
The [recovery runbook](supply_recovery.md) gives exact archive identities, restore
commands, bounded-batch behavior, remote verification and notebook publication.

## Findings and remaining gates

The earlier 48-game identification replay found no bound violations. Cash
constraints added 740 identified melon-sale units (3,810 → 4,550) and tightened
the stock upper on 15,452 callbacks. Accumulated excess upper-bound units fell
from 1,772,040 to 1,612,546, but the 19,536 false-positive empty-stock warnings
did not decrease. This is **partial identification progress**, not demonstrated
policy improvement. Other products were unchanged on that dataset.

Fresh policy outcomes will be added here only after the preregistered run and
independent audit finish. Feature engineering remains incomplete. Outstanding
areas include joint cross-product constraints, cash attribution under broader
own trading, calibrated opponent beliefs, livestock/feed, fertilizer timing,
land expansion, crop mixtures, joint routing, broader opponents and family-level
predictive ablations. Final training, validation/holdout use and submission remain
blocked.
