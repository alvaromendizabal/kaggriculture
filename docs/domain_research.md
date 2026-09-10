# Kaggriculture: domain mechanisms, feature priorities and modern methods

Research cut-off: 10 September 2026. Scope: the pinned `kaggle-environments==1.32.7`
Kaggriculture simulator, current public competition information and primary research.
This is a decision-oriented review supporting implemented experiments, not a claim that
a particular descriptor or recent paper guarantees a stronger agent.

## Executive assessment

The useful domain is a **finite-horizon, two-player production/inventory/routing game
with a shared endogenous market**. It is not a real-world crop-yield prediction dataset.
The strongest feature candidates express opportunity costs across production, labor,
storage, liquidity, time and rival supply. A correct local crop value can still be a bad
decision if its harvest cannot be delivered, its supply collapses the price, or its
watering displaces a more valuable task. Features should therefore describe feasible
actions and their consequences, not simply increase the number of columns.

The existing two studies provide 144 development games. They support maturity-aware
harvest and labor as promising mechanisms, but also show harmful capacity interventions,
an inactive capital reserve and livestock coverage gaps. Study 3 isolates delivery
opportunity cost and short-horizon sale timing on six fresh seeds. Its new descriptors
remain provisional until evaluated; no literature result is counted as game evidence.

As observed on 10 September, the active leaderboard's leading score was **3033.1
(SpaTaro)**. That rating is not farm coins. The rules rank head-to-head wins/losses/ties;
coin margin itself does not improve the ranking. The competition was still active, so
there was no final winning score to beat. The final submission deadline was 30 September
2026 at 23:59 UTC, followed by additional evaluation. These are a dated snapshot, not a
guarantee of future dates or scores. [Live leaderboard](https://www.kaggle.com/competitions/kaggriculture/leaderboard),
[official rules](https://www.kaggle.com/competitions/kaggriculture/rules).

## 1. Mechanistic evidence: inspect the game before importing agronomy

The installed engine source is the authoritative contract for these experiments. Its
hash is recorded in each report's engine manifest. The public repository provides the
independently inspectable upstream implementation and game description. Statements in
this section were checked against the pinned local interpreter, not inferred from
real crop names. [Official implementation](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture).

The retrieved upstream interpreter was byte-identical to the installed interpreter on
10 September (SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`).
This checks public source drift, not Kaggle's private deployment settings or future
versions; see [the comparison record](../reports/upstream_engine_verification.json).

### Production and treatment timing

Plants have crop-specific maturity, yield caps, watering effects and decay. A capped
melon can be harvestable at age ten although a later maximum-yield-day field is twelve.
Consequently, ranking all harvests by that later field wastes both time and market
advantage. Repeated-yield crops need separate schedules: tomato and strawberry yields
are limited scheduled opportunities, not an endless annuity. Planting-day watering and
consecutive dry days matter independently of a generic plant-age feature.

The correct features include harvestable units **now**, next-refresh survival with and
without water, treatment-dependent incremental yield, remaining productive windows,
time until the next legal action and the opportunity cost of retaining the tile. The
previous treatment parity tests cover all five crops across ages, caps and water/
fertilizer states. That establishes arithmetic, not realized returns after acquisition,
transport and displaced work. Fertilizer's inclusive multi-day window still needs a
trajectory-level treatment policy and a separate component experiment.

For livestock, feeding, escape risk, production intervals and banked care effects are
distinct mechanisms. Today's care is not automatically today's sale. Wheat feeding,
animal acquisition, structure placement, product collection and fertilizer side-products
must be costed together. All 78 animal state/feed-care descriptors were constant in the
second crop-only study. This is absent policy coverage—not evidence against animals.

### Labor, space and inventory

Workers operate on an open Manhattan grid. Their positions, task deadlines, competing
assignments and return-to-shed journeys couple crop choices to spatial decisions.
Daily hire costs grow by a Fibonacci schedule; hired hands expire at night. A worker
can be inexpensive in coins but harmful if it triggers another inventory bottleneck.
Land likewise adds useful capacity only if labor, watering, working capital and time
to recover its cost are available.

Shared storage is capped at 100 units. Farm commands occur before market orders. An
overflowing DROP can destroy produce before a same-turn sale frees space; the later
sale cannot recover that loss. Bounded PLACE commands can preserve the rest in carry.
Nightly automatic deposits follow market trading, so their contents can be sold only
on a later callback. At termination, held goods are not banked coins. These ordering
constraints motivate serial shadow execution, shared-capacity slack and remaining-
delivery-action features rather than independent per-worker recommendations.

### Markets and partial observation

Prices respond to product-specific inventory curves. A quantity's value is the sum of
per-unit quotes, not quantity times the first quote. At the $1 floor, sales do not keep
adding supply. Both players' units can receive the same pre-commit quote when orders
align; the next unit then sees the changed shared inventory. Town consumption depends
on known shop instances, including duplicates, and event alignment. Unknown future
shops must not be reconstructed from the evaluator's seed.

Public plants and workers reveal conditional future supply, but not private carried
goods, shed inventories or the opponent's planned jobs. A visible ready-crop wave is
therefore a **stress envelope**. Treating it as a calibrated probability forecast would
overstate our information. Features distinguish immediate liquidation, known-demand-
only paths, rival-supply stress and horizon availability. Separate uncertainty flags
matter as much as the point values.

## 2. Exhaustiveness means an explicit coverage map

The completion ledger tracks 18 families with an availability contract, mechanistic
tests, on-policy activation, component outcomes and remaining gaps. No family closes
merely because its columns exist. The following map identifies decision relationships
and the evidence that would justify keeping or rejecting a family.

| Family | High-value relationship | Required decision evidence |
|---|---|---|
| Crop lifecycle | Net sale value × productive windows × tile occupancy | Crop-mix and repeated-harvest interventions |
| Maturity/decay | Collect now vs extra yield vs decay/price delay | Global timing and staggered-harvest tests |
| Water/survival | Rescue value × deadline × worker detour | Routing/water interaction, not only urgency scores |
| Fertilizer | Marginal yield × active window − acquisition/work cost | Feasible treatment trajectories and ablation |
| Storage/delivery | Shared room × sale phase × displaced work | Joint routes, mixed inventory and activated gates |
| Capital | Receipts × hire/seed needs × time to payback | Stress-state activation and reserve sensitivity |
| Labor | Marginal work value × remaining day − hire cost | Separate staffing, distance and assignment factors |
| Market impact | Marginal sale units × own/rival supply curves | Quantity/timing controls against varied opponents |
| Town demand | Duplicate shop mix × event alignment | Known-demand decisions, unknown-unlock uncertainty |
| Livestock | Feed/care bank × production × collection cycle | Goose/cow/sheep on-policy coverage and resource loops |
| Land | Additional usable tasks × horizon − capital/labor cost | NE/SW/SE expansion experiments |
| Causal history | Observed response × lag availability | Prefix-safe predictive or decision improvement |
| Opponent response | Visible specialization × market reaction | Diverse opponents and anti-overfitting tests |
| Terminal banking | Inventory × remaining feasible sale actions | Joint final-turn liquidation under capacity limits |
| Relative choices | Best action − second-best feasible alternative | Stable ranks/margins in controlled interventions |
| Learned encodings | State-action structure × future decision value | Grouped out-of-fold fitting without future input leakage |
| Spatial graphs | Workers ↔ tasks ↔ resources ↔ deadlines | Assignment/search benefit beyond Manhattan heuristics |
| Robustness | Mechanism × seed × seat × opponent style | Stress suites, fresh seeds and diminishing returns |

Detailed statuses live in [feature_coverage.md](feature_coverage.md). Weather, satellite
imagery, soil chemistry and real growing seasons are excluded because no corresponding
variables or transitions exist in this simulator. Hidden seed reconstruction, evaluator
reward and rival private inventories are excluded by decision-time availability. Blind
all-pairs polynomial expansion is not a substitute for a causal or constraint-based
hypothesis. This is a domain exclusion, not a refusal to explore a plausible mechanism.

## 3. What the research literature contributes—and does not

### Structured inventory routing and post-decision value

Greif and colleagues combine learned node prizes with a capacitated prize-collecting
routing optimizer for a dynamic inventory-routing problem. The transferable idea is
to separate structured feasibility from the estimated downstream value of serving a
location. Their replenishment, holding and shortage costs differ from this game's
production and shared-market revenue, so their reported performance is not a forecast
for our agent. [Greif et al., 2024](https://arxiv.org/abs/2402.04463).

Hasturk and colleagues formulate constrained reinforcement learning around a known
immediate cost and a learned post-decision value, with optimization enforcing action
constraints. Their application is hydrogen inventory routing under stochastic supply
and demand. Our inference is that exact farm and market transitions should remain
explicit, while only genuinely unknown continuation value should eventually be learned.
It is not evidence that their architecture is already optimal for Kaggriculture.
[Hasturk et al., 2025](https://arxiv.org/abs/2503.05276).

Study 3 implements a modest version of this separation: exact current sale curves and
legal serial farm actions, plus explicitly conditional continuation scenarios. It does
not train a value network or solve the global route problem. A later candidate could
assign workers to jobs using a bipartite graph, then evaluate short feasible plans under
multiple opponent responses. Job value must include survival, available capacity,
cashflow, price impact and the return journey—not only distance to a ripe crop.

### Neural routing and planning

Kool, van Hoof and Welling use attention-based models with reinforcement learning and
a rollout baseline on routing problems including TSP and capacitated variants. This
supports studying permutation-aware worker/task representations. Their benchmarks do
not contain this game's growth, watering, market competition or nightly expiry; those
constraints require an adapted action interface and independent tests.
[Kool et al., ICLR 2019](https://arxiv.org/abs/1803.08475).

MuZero demonstrates planning with learned reward, policy and value models across
Atari, Go, chess and shogi. That motivates evaluating search/value combinations, not
automatically learning a black-box copy of a simulator whose rules we already know.
Our priority is exact known transitions and bounded action branching; learned latent
dynamics would require evidence that their approximation and runtime trade-off helps.
[Schrittwieser et al.](https://arxiv.org/abs/1911.08265).

Invalid-action masking has theoretical and empirical support in policy-gradient
learning, particularly with large invalid action sets. It should accompany any learned
policy here. A per-worker mask alone is insufficient: individually legal actions may
jointly overspend cash or overflow storage. Serial shared-resource execution and exact
market-order limits remain necessary. [Huang and Ontañón](https://arxiv.org/abs/2006.14171).

### Opponent populations, including current research

Policy-space response oracles address the tendency of multi-agent learners to overfit
their training opponents by responding to mixtures and maintaining policy populations.
That directly motivates a development league containing crop specialists, livestock,
market-timing and expansion policies rather than one frozen scheduler. It does not
turn a small local win rate into a guarantee against the live field.
[Lanctot et al., 2017](https://arxiv.org/abs/1711.00832).

The 2026 Global PSRO work emphasizes population quality and population exploitability
in two-player zero-sum games, with a two-phase explore/select construction. It is a
current research direction, not an implemented result in this repository. Full-game
exploitability is not measured by defeating our finite baseline set. A practical first
step is a reproducible cross-play matrix with diverse frozen opponents, then examining
whether new responses broaden coverage rather than repeatedly exploit one weakness.
[Zhang et al., 2026](https://arxiv.org/abs/2605.28273).

### Statistical credibility and feature dependence

Agarwal and colleagues show how limited-run reinforcement-learning comparisons can
be misleading and recommend uncertainty-aware aggregate evaluations. This motivates
reporting clustered intervals, seed sensitivity, performance distributions and explicit
sample counts. It does not justify treating thousands of correlated game callbacks as
thousands of independent trials. [Agarwal et al.](https://arxiv.org/abs/2108.13264).

Hooker, Mentch and Zhou analyze problems with feature-importance methods that break
dependence by unrestricted permutation. Our inventory, time, capacity and workload
features are intrinsically linked. Accordingly, current evidence comes from controlled
policy-component interventions and exact replay, not shuffling impossible combinations
of physical state. Future model importance should use grouped or conditionally plausible
perturbations and be checked against actual policy behavior.
[Hooker, Mentch and Zhou](https://arxiv.org/abs/1905.03151).

## 4. Research-grade validation and the next bounded work

Every experiment fixes its mechanism, comparator, arms, seeds, evaluation budget and
source lineage before outcome collection. Known-rule parity tests and synthetic stress
fixtures come first. A complete-batch synthetic integration test verifies all checkpoints,
statistics and report generation cheaply. Two full deterministic smoke games check the
real runner without consuming the new registered seeds. Failures in fixtures or default
configuration handling are documented rather than disguised as successful experiments.

The observational unit is the **seed cluster** with both seats and all interventions.
Pairing initial seeds improves comparability but does not force identical later shops:
different actions can consume the shared random generator differently. Primary effects
must therefore be interpreted as policy effects under the registered environment,
not as isolated market treatment effects under identical future randomness. Development
intervals remain exploratory; the validation and holdout pools are untouched.

Descriptors pass availability, schema, finiteness, variation and redundancy screens.
These checks detect engineering defects and coverage gaps; they do not rank predictive
power. A learned feature model would additionally require episode/seed-grouped fitting,
out-of-fold predictions for supervised encodings, train-only transformations, temporally
available labels and a genuinely untouched evaluation boundary. Final selection should
combine decision benefit, stability, runtime, redundancy and mechanistic plausibility.

The immediate next evidence is study 3's four-arm market/logistics comparison. Regardless
of its outcome, livestock/resource loops, fertilizer, land return, adaptive crop mix,
joint assignment and richer opponent populations still require their own bounded studies.
Negative or inactive components are retained in the record. No final training or Kaggle
submission is authorized by an arbitrary feature count. Completion requires coverage of
each plausible family, diminishing returns under robust tests and a documented rationale
for exclusions; even then, a top leaderboard position cannot be promised in advance.
