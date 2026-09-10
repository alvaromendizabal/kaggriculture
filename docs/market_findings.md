# Study 3 findings: useful delivery signal, harmful holding rule

**Decision: do not promote a new competitive agent. Keep feature research open.**
The delivery intervention improved coin production, but its two wins were concentrated
in one of six seeds. The fixed market-holding rule reduced coins in every seed cluster.
More mechanistic descriptors did not automatically produce a broadly stronger policy.

## What actually ran

The [registered design](market_research.md) evaluated four arms × six fresh development
seeds × both seats: 48 complete games against frozen `RelationshipPolicy("101")`.
The candidate baseline was frozen maturity policy `001`. No validation/holdout data or
leaderboard submissions were used. The prior 144 study games were preserved, not rerun.

The AWS workflow completed in **940.77 seconds**, including 106 passing tests, 828.61
seconds for the research stage and fresh execution of all three notebooks. Compute was
then stopped. All 76 expected output artifacts (15,289,344 bytes) were SHA-verified.
Independent replay checked every one of 34,512 candidate callbacks, recomputed all
8,688 × 933 feature values (absolute tolerance 1e-12), and verified exact product accounting.
No ineffective farm actions, discarded products or terminal held products occurred.

## Controlled outcomes

Digits mean delivery / market timing. Each row contains 12 games but only six independent
seed clusters. Match score is win + half a tie, not an official Kaggle rating.

| Arm | Wins / ties / losses | Mean banked coins | Mean opponent-relative margin | Mean harvested/sold units |
|---|---|---:|---:|---:|
| 00: baseline | 0 / 0 / 12 | 31,984.92 | −3,576.08 | 339.33 |
| 01: holding only | 0 / 0 / 12 | 31,194.42 | −5,056.92 | 339.33 |
| 10: delivery only | 2 / 0 / 10 | 34,628.42 | −1,032.67 | 293.08 |
| 11: both | 0 / 0 / 12 | 33,269.75 | −4,073.00 | 294.25 |

| Registered contrast | Mean coin effect | Descriptive 95% seed-bootstrap interval | Match-score effect |
|---|---:|---:|---:|
| Delivery, averaged over holding settings | +2,359.42 | [1,138.33, 3,647.46] | +0.0833; interval [0, 0.25] |
| Holding, averaged over delivery settings | −1,074.58 | [−1,253.10, −740.92] | −0.0833; interval [−0.25, 0] |
| Delivery × holding interaction | −568.17 | [−904.50, 64.50] | −0.1667; interval [−0.5, 0] |

These exploratory intervals resample six whole seed clusters 4,000 times. They do not
establish confirmatory significance, correct for all historical design choices or
measure robustness to diverse opponents. Both delivery-only wins occurred at seed 1204.
The prior stronger opponent remained ahead in 46 of the 48 candidate games.

## Follow the mechanism

Delivery-only changed about 38 farm commands per game. First melon sale moved from
step **264 to 242**, eliminating the baseline's 22-action delay behind the opponent.
Minimum observed cash rose from 14 to 976. However, mean melon sales fell from 222 to
186 units and total harvest fell from 339.33 to 293.08 units. Earlier banking and better
price timing can outweigh some volume loss, but the work-value proxy does not optimize
the entire production/delivery schedule. Since every arm had zero waste, this result
cannot be explained as recovery of discarded units. These are descriptive trace
relationships; they are not a separate causal mediation experiment.

The holding rule activated about 11.17 product decisions/game without delivery and
17.42 with delivery. It did not simply fail to activate. A separate evaluator-only
[hold diagnostic](../reports/market_hold_analysis.json) examined its 343 product-hold
events. The opponent sold the **same product during that turn in 174 events**. The
next observed quote fell in 139 events, rose in 87 and was unchanged in 117.

| Holding arm | Product-hold events | Same-turn rival sale events | Next quote fell | Mean next quote change |
|---|---:|---:|---:|---:|
| 01 | 134 | 81 | 63 | −7.87 |
| 11 | 209 | 93 | 76 | −7.13 |

This is consistent with a key missing relationship: **a visible ripe-crop wave does not
represent already harvested rival goods in private carry or storage**. Known town demand
alone is not a sufficient reason to wait. The analysis verifies rival sales from their
own recorded inventory only as an evaluator; those private observations never enter a
policy or feature. Event observations are correlated and do not identify the portion
of the total loss caused by this channel.

The next justified representation is an uncertainty-aware rival-supply estimate derived
only from public harvest changes, market-history residuals and our own known actions.
It must have a decision-time availability contract and be evaluated with new controlled
tests. Do not leak the evaluator's rival stock into a supposedly predictive feature.
The current fixed 50:50 scenario blend is not a calibrated probability model and is not
adopted as an improvement. Future tests should also separate crop-mix substitution from
delivery scheduling instead of relying solely on a crop work-value proxy.

## Feature accounting and remaining scope

The bank now contains **933 provisional descriptors**: the prior 618 plus 315 conditional
market/delivery descriptors. All 933 were screened; 361 were constant and 572 varied in
this design. There were 56 exact nonconstant duplicate groups and 670 feature pairs with
absolute Spearman correlation at least 0.995. These are coverage/redundancy diagnostics,
not predictive ranking or final feature selection. Final retained/rejected counts remain
zero. We reject adoption of this holding **policy rule**, not every related descriptor.

Policy median/p95 latency was 4.78/5.68 ms; the observed maximum was 290.00 ms. Sampled
full-bank median/p95 extraction was 2.56/3.05 ms. These AWS CPU measurements include this
process/cache setup, not a competition-container latency guarantee.

Livestock/feed-care loops, fertilizer acquisition/timing, land expansion, adaptive crop
mix, joint worker assignment and diverse opponent populations still lack adequate
activated evidence. Tomato sales remained absent. The [18-family ledger](feature_coverage.md)
and [cited domain review](domain_research.md) make these gaps explicit. Notebook 02 stays
open, final optimization stays blocked, and no claim of state-of-the-art competitive
performance or a top leaderboard score is made.

## Inspect and reproduce

- [Executed canonical notebook 02](../notebooks/02_feature_research.ipynb)
- [All 48 outcomes](../reports/market_games.csv) and [paired contrasts](../reports/market_effects.csv)
- [933-feature registry](../reports/market_registry.csv) and [research report](../reports/market_research.json)
- [Independent replay audit](../reports/market_integrity.json) and [AWS verification](../reports/market_cloud_verification.json)

The notebook's interactive match-score axis spans 0–1; its static fallback autosizes
the labeled axis to the observed values. Read the numeric scores, not bar height alone.
The full prior Git history through PR3 was also backed up and round-trip SHA-verified;
see [history backup](../reports/history_backup.json). An initial local audit invocation
preceded the final report download and stopped without changing data; the completed
audit followed verification of all 76 files. No experiment restart was needed.
