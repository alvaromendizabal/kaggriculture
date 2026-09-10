# Terminal service and liquidation: registered development findings

The final-day package won all 16 development games and increased mean coins by
747.875 over the frozen Study 5 fertilizer baseline. Removing final-day feeding
alone increased coins by 426.125, with no pooled match-score change. Feature research
remains open: the package uses only one worker, so these comparisons do not establish
benefit from coordinating multiple workers. No leaderboard score is measured.

## Question, domain evidence and interventions

The [pinned official interpreter](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py)
has 719 action rounds. There is no final-day refresh: feed cannot protect survival
or produce goods before scoring. Goods have value only if delivered and sold before
the final bank balance is evaluated. Hired hands expire every night, including the
night before the final day. These rules, rather than real-world agricultural yield
models, determine the feasible feature relationships in this simulation.

All arms use the preceding fertilizer policy through observation 695. **Baseline**
continues that policy. **Feed** changes only final-day feed and wheat-reserve gates.
**Joint** follows Feed until the final day, then selects bounded collection/delivery
routes, immediately sells products and does not rehire. The [protocol](terminal_protocol.md)
registered these packages before outcome collection; no policy or seed was revised.

The intrinsic-horizon reasoning follows
[Pardo et al., ICML 2018](https://proceedings.mlr.press/v80/pardo18a.html).
Individual route feasibility plus conflict resolution is informed by
[Choudhury et al., RSS 2020](https://arxiv.org/abs/2005.13109), with task precedence
motivated by [Bischoff et al., 2020](https://arxiv.org/abs/2005.03902).
These are structural translations, not claims to implement those algorithms or
their optimality guarantees. The engine version and source hashes are frozen in
the registration and checked on replay.

## Design and paired results

Exactly 48 full games use fresh development seeds 1501–1504, both seats, three
arms and two frozen opponents. `livestock_fertilizer` is the preceding strongest
resource policy; `melon_specialist` is the existing all-MELON crop scaffold, not
an independently developed competitive submission. Both seats and opponents stay
inside each seed cluster. Preflight seed 71 is excluded. Validation and holdout
seeds are unused. All 16 blocks have identical observation/action/diagnostic hashes
through the 696 decisions preceding the intervention.

| Opponent | Arm | Games | Match score | Mean own coins | Mean coin margin | Final-day feed | Residual product units |
|---|---|---:|---:|---:|---:|---:|---:|
| Fertilizer | Baseline | 8 | 0.500 | 46,740.00 | 0.00 | 2.00 | 6.25 |
| Fertilizer | Feed | 8 | 0.500 | 46,983.75 | 248.75 | 0.00 | 4.50 |
| Fertilizer | Joint | 8 | 1.000 | 47,342.50 | 599.00 | 0.00 | 0.00 |
| MELON | Baseline | 8 | 1.000 | 56,013.50 | 24,938.50 | 3.00 | 5.50 |
| MELON | Feed | 8 | 1.000 | 56,622.00 | 25,547.00 | 0.00 | 3.00 |
| MELON | Joint | 8 | 1.000 | 56,906.75 | 25,831.75 | 0.00 | 0.00 |

Match score is win + half a tie. Each arm has 16 games; the 48 is the entire
three-arm study, not the denominator for Joint's 16 wins. Residual units include
carried and shed products, not unharvested crops. Baseline mirrors the fertilizer
opponent and ties all eight games; the local score gain converts those ties to wins.
The MELON opponent is already beaten by every arm and supplies no score discrimination.

| Pooled contrast | Match-score change | Mean coin change | Descriptive coin interval | Mean margin change |
|---|---:|---:|---|---:|
| Feed − Baseline | 0.000 | +426.125 | [153.750, 698.500] | +428.625 |
| Joint − Feed | +0.250 | +321.750 | [−30.500, 674.000] | +317.500 |
| Joint − Baseline | +0.250 | +747.875 | [500.750, 995.000] | +746.125 |

Intervals use the registered 4,000-resample seed-cluster bootstrap (seed 4501).
Four clusters are too few for a strong population claim. Identical score changes
across seeds give a degenerate Joint−Baseline interval; this is not certainty about
unseen games. Joint−Feed own-coin differences by seed are +501, +847, −193 and +132:
the package is not a uniform coin improvement over Feed. The
[complete contrasts](../reports/terminal_effects.csv) include each opponent,
each registered metric and every seed difference. No correction for searching many
metrics turns these development intervals into confirmatory evidence.

## Mechanism checks and the staffing limitation

Terminal feed falls from 2.5 units per game to zero. Feed alone wins four and loses
four games against the fertilizer reference: a correct feed-feasibility feature
does not guarantee a better sequence of deliveries and sales. The full package
leaves zero carried/shed products in all 16 games, and its terminal ineffective
action count is zero. Route decisions change collection, water use, sale timing
and rival market impact; a total coin difference is not the sale price of saved feed.

**Joint never activates multiworker assignment as a policy.** It does not rehire
after overnight expiry and has one worker on the final day. Baseline and Feed hire
three hands and reach four workers. The comparison is therefore liquidation plus
staffing. Descriptor variation for multiple workers is observed on Baseline/Feed
trajectories; mechanical tests exercise multiworker conflicts and capacity. Neither
establishes a decision benefit from multiworker assignment.

The [diagnostics](../reports/terminal_diagnostics.json) report actual worker counts,
hires, hiring expenditure, final-day net coin gain, gross sale receipts, final
inventory and unharvested ready units for every game. Hiring expenditure is derived
from realized hand-count transitions and the pinned cost function, not a guessed
per-worker charge. Receipt accounting separates that expenditure from sales.

Mean final-day hiring cost is four coins for Baseline/Feed and zero for Joint.
Of Joint's 747.875-coin gain over Baseline, 743.875 is additional gross sale
receipts and four is saved hiring expense. This accounting decomposition does
not remove the causal staffing confound: fewer workers also changes routes and
sales. Joint leaves an average 1.375 ready field units unharvested versus Feed's
0.625, another reason to avoid equating zero product inventory with full recovery.

## Features, screening and availability

| New family | Candidates | Varying | Constant |
|---|---:|---:|---:|
| Terminal event feasibility | 13 | 10 | 3 |
| Terminal stock opportunity | 36 | 28 | 8 |
| Bounded liquidation routes | 30 | 29 | 1 |
| Total new | 79 | 67 | 12 |

The supported joint bank has 1,579 descriptors: 1,248 varying and 331 constant
over 8,688 sampled observations. The project union is 1,621; 42 prior cash-bound
features remain excluded because their contract does not cover own purchases.
The [registry](../reports/terminal_registry.csv) includes every feature's availability,
family, range, distinct count and nonzero fraction. The
[screening report](../reports/terminal_research.json) and
[correlation list](../reports/terminal_correlations.csv) retain exact duplication
and absolute Spearman correlation at least 0.995: 153 nonconstant duplicate groups
and 1,926 high-correlation pairs. No feature is selected or rejected
for a final model. Constants are coverage flags, not evidence of useless domains.

Routes visit at most two distinct collection resources, optionally water an
immediately productive crop, and end with a capacity-safe DROP. Every move and
service action counts. Eight ranked routes plus PASS form each worker's menu;
direct deposit is preserved. Enumeration is exact over these retained menus,
excluding resource overlap and excessive total shed load. It is not exact over
all season-long schedules. Utility subtracts eight coins per action from current
conditional sale revenue. Future shops, opponent private state, seed and final
reward never enter policy inputs. Route features are explicitly inactive before
day 29; prices are current scenarios, not calibrated forecasts.

## Integrity, recovery and publication

All 48 games passed independent replay with zero mismatches: 34,512 callbacks,
8,688 full 1,579-value vectors, 1,488 state restorations, 69,024 evaluator-only
private transitions and 864 product balances. Every one of 241,584 supported
stock checks and 241,248 sale checks passed. Hidden truth is used only after
simulation for auditing, never to select an action. The
[audit receipt](../reports/terminal_integrity.json) records each checked artifact.
All 61 required S3 objects passed downloaded-byte, SHA256, version, ETag and
AES256-encryption checks in the [persistence receipt](../reports/terminal_cloud_verification.json).

Source and registration were durable in GitHub and private S3 before registered
outcomes. Each game was uploaded after completion. A real S3 restoration downloaded
one registered game into a separate destination and reused it on a second attempt,
creating zero new games. During service interruptions, valid completed games were
reused; one incomplete simulation without a checkpoint had to restart. A later
summary interruption required only rereading saved games. The
[runbook](terminal_recovery.md) documents exact identities and short restartable steps.

No new SageMaker compute was launched. Local CPU execution, audit, screening,
transfers and CI are distinct costs; recorded episode execution time does not
represent total elapsed work. Feature-assembly timing excludes history updates,
serialization and I/O and is not a deployment guarantee.
Registered episode times sum to 651.718 seconds. Final-day policy latency has a
40.455 ms 95th percentile and 245.126 ms maximum; sampled final-day feature
assembly has a 50.277 ms 95th percentile and 239.483 ms maximum on this local CPU.
These are separate timing samples, not quantities to add as matched observations.

Notebook 02 preserves all 28 preceding code-cell sources and appends four cells
for this study. Its execution receipt is separate from archived ancestor receipts.
Public verification checks paired arithmetic, provenance, audit coverage,
mechanism accounting and remote evidence without rerunning registered games.

## Decision and next bounded experiment

Keep the terminal feed gate and liquidation package as development candidates.
Do not promote individual descriptors, declare feature research complete, or infer
Kaggle superiority. Before another assignment claim, preregister a staffing-controlled
comparison that activates multiple workers, verifies route conflicts and capacity
on real trajectories, and separates route changes from hiring. An independent
specialist/stress opponent is needed to avoid further score saturation. Larger
menus, heterogeneous inventory, fertilizer/water combinations, season-long labor,
capital stress, land return and adaptive crop/herd mix remain in the
[coverage ledger](feature_coverage.md). These results do not consume a final holdout.
