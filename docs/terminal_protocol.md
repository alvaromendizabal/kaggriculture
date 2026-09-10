# Terminal service and joint liquidation protocol

Study 6 isolates final-day decisions. All arms use Study 5's fertilizer policy
through decision 695. The pinned simulator has no refresh on the final day, and
executes its last action at observation 718. A feed action after observation 696
cannot protect survival or create production before scoring. Collected goods
must reach the shed and sell before scoring; money is the terminal reward.

## Hypotheses and frozen comparisons

1. **feed − baseline:** zero final-day feeding and zero final-day wheat reserve
   should conserve wheat and worker actions, increasing final coins. The explicit
   fork changes only these two conditions. All other decisions use the prior scaffold.
2. **joint − feed:** joint collection/delivery routes should recover more terminal
   stock, avoid competing workers targeting the same resource, and increase coins.
   The package replaces final-day farm actions and sells all deposited products;
   it includes no final-day hiring. It is not an isolated estimate of assignment alone.
3. **joint − baseline:** total final-day package effect.

Primary outcome: win + half a tie. Supporting outcomes: own coins, coin margin,
terminal feed, ineffective actions, carried/shed residual units and resource balances.
Four fresh development seeds 1501–1504, both seats, three arms and two frozen
opponents give exactly 48 full games. Opponents are Study 5's strongest frozen
fertilizer reference and the existing all-MELON crop specialist (CropPolicy full,
three hands). Neither is a new independent leaderboard agent. The stronger
livestock reference replaces the saturated routine benchmark; specialist strength
will be reported, not assumed. Validation and holdout remain untouched.

Paired differences are averaged within seed across seats/opponents. A descriptive
4,000-resample seed-cluster bootstrap uses seed 4501. Four clusters cannot support
strong population inference; local scores are not Bradley–Terry leaderboard ratings.
All arms' preterminal observation/action/diagnostic hashes must match within each
seed/seat/opponent block. Seed 71 is preflight only and excluded from outcomes.

## Route model and feature availability

The 79 new descriptors expose actual remaining refreshes, last-day service waste,
product inventory opportunities, and bounded worker/task assignment menus. The
1,579 active bank retains all 1,500 Study 5 supported columns. The prior 42 cash
features remain excluded because own buying violates their existing contract.

Routes visit at most two distinct harvest/manure resources then one DROP. Optional
WATER precedes a ready single-harvest crop only when the current legal state gives
an immediate yield increment. Costs count every move, service, collection and DROP.
Each worker keeps the eight highest utility routes, preserving direct deposit,
plus PASS. Exact enumeration over these menus prevents overlapping resources and
joint stock exceeding currently free shed capacity. Utility is current conditional
sale revenue minus eight coins per action. Sale curves account for own market
impact; future demand, opponent sales, subsequent trips and terminal water/fertilizer
combinations beyond this menu are not forecast. Only the first action is executed,
then replanning occurs. This is a bounded heuristic, not global route optimality.

DROP is allowed only if all carried goods are products and the complete joint
route load fits the shed. This is deliberately conservative about later room freed
by sales. No future shop, seed, hidden inventory, or reward enters policy features.
Expensive route descriptors are explicitly inactive before day 29; other horizon
and stock descriptors remain available throughout the season. Counts are candidates,
not individually validated predictive features or a completion claim.

## Research translation

Pardo, Tavakoli, Levdik and Kormushev (ICML 2018),
[Time Limits in Reinforcement Learning](https://proceedings.mlr.press/v80/pardo18a.html),
distinguish intrinsic finite horizons from artificial training truncation. Here
termination is intrinsic: nonexistent refreshes must not receive continuation value.
No reinforcement learning is being fitted in this study.

Choudhury et al. (RSS 2020),
[Dynamic Multi-Robot Task Allocation under Uncertainty and Temporal Constraints](https://arxiv.org/abs/2005.13109),
separate individual feasible plans from cross-agent conflict resolution. Our
deterministic collection menus and shared-resource exclusion use that structural
idea; they do not implement SCoBA or inherit its optimality guarantees.

Bischoff et al. (2020),
[Multi-Robot Task Allocation and Scheduling Considering Cooperative Tasks and Precedence Constraints](https://arxiv.org/abs/2005.03902),
motivate checking executability and precedence. WATER → HARVEST → DROP is an
explicit dependency here. The final authority is the pinned
[official interpreter](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py),
version 1.32.7, SHA256 bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e.

## Execution and decision rules

Publish source and registration before registered outcomes. Each invocation starts
at most two new games or 60 seconds of new work, completes the current game, and
saves each game before upload. Reuse valid checkpoints. No new AWS compute.
Replay every saved decision and sampled vector, restore policy/history states,
verify both private transitions only in the evaluator, and check product balances.
Document constants, duplicates, source hashes, runtime, mechanism failures and
paired effects. Do not silently revise policy/seed/opponent after results. A failure
requires a new study identity; earlier evidence stays frozen. All descriptors stay
provisional. No holdout use, final training or competition submission is authorized
by this protocol.
