# Resource relationships: measured findings

## Outcome and scope

The registered 64-game development study completed on September 10, 2026. Collecting a
fully capped mature crop earlier improved the candidate against the frozen previous crop
scheduler. Storage protection alone stopped waste but hurt the primary local match metric.
The cash-reserve intervention never activated: this batch does **not** evaluate its usefulness.

This is feature-policy research, not a trained predictor, final policy selection, a Kaggle
submission or evidence of leaderboard performance. Four development seeds and both seats
were reused from study 1. Validation and holdout seeds were untouched. The
[registered design](relationship_research.md) and [full outcome rows](../reports/relationship_games.csv)
are the primary experiment record.

## Controlled comparison

Arm bits are **capacity / capital / maturity**. Each listed arm contains eight games.
The four corresponding capital-on arms had identical outcome summaries and zero capital
interventions; they do not provide additional seed diversity. Match score is win = 1,
tie = 0.5, loss = 0, not simply the fraction of outright wins.

| Arm | Active components | W / T / L | Mean match score | Mean final coins | Mean units sold | Mean units discarded |
|---|---|---:|---:|---:|---:|---:|
| 000 | Frozen reference | 3 / 2 / 3 | 0.500 | 22,276.00 | 233.250 | 26 |
| 100 | Capacity | 1 / 0 / 7 | 0.125 | 22,358.75 | 171.375 | 0 |
| 001 | Maturity | 8 / 0 / 0 | 1.000 | 38,992.25 | 381.000 | 0 |
| 101 | Capacity + maturity | 8 / 0 / 0 | 1.000 | 41,918.75 | 349.125 | 0 |

The full eight-arm results remain visible in notebook `02`; no unfavorable arm is dropped.
All maturity-enabled arms won their development games, but these repeated combinations of
four seeds against one opponent do not justify a general win-rate estimate.

## Relationships, not isolated feature counts

**Maturity has a clear development signal.** Averaged over the other factors, its effect is
+18,138.125 banked coins and +0.6875 match score. The descriptive seed-cluster bootstrap
intervals are [17,134.875, 18,732.000] coins and [0.5625, 0.7500] match score. They resample
only four complete seed clusters; they are not confirmatory significance tests.

**Capacity has a conditional opportunity cost.** Without earlier cap collection, it reduces
mean units harvested from 259.250 to 171.375, even while eliminating 26 discarded units.
The conservative ready-wave routing rule spends actions delivering instead of tending or
collecting crops. Across all arms, its match-score effect is -0.1875, with descriptive interval
[-0.2500, -0.0625]. Its banked-coin effect is +1,504.625, with interval [-107.000, 2,878.625].
Eliminating waste is not sufficient evidence of improved competitive decisions.

**The interaction matters.** Capacity raises mean coins by only 82.750 without maturity,
versus 2,926.500 with maturity. The capacity-by-maturity difference-in-differences is
+2,843.750 coins, with descriptive interval [317.250, 4,974.000]. Both maturity-enabled
settings saturate match score against this opponent, so the extra coins are not demonstrated
additional wins. These results motivate joint routing/harvest/market decisions, not blindly
switching every resource-protection rule on.

**Capital needs a genuine stress test.** Its action-change count is zero in every game.
The observed zero contrasts establish non-activation, not irrelevance, equivalence of all
reserve policies or evidence against cashflow descriptors. Low-capital, uncertain-receipt,
staffing and fertilizer-purchase regimes are needed before making a utility judgment.

## Post-hoc mechanism audit

The [behavior summary](../reports/relationship_behavior.csv) was derived after the fixed run;
it is descriptive and was not used to tune the experiment. In these traces the first melon
sale occurs at step 312 for the frozen reference, 289 for capacity alone, 264 for maturity
alone, and 242 for their combination. Against the candidate, the frozen opponent's first
melon sale remains at step 312: the combined policy gets to market 70 actions earlier.
Mean melon units sold are respectively 177, 113.5, 270 and 240.

This is consistent with earlier supply reaching a shared, price-impacting market as well as
earlier land reuse. It does not isolate those channels causally. Same initial seed does not
guarantee the same future shop path after policy-induced random-number consumption diverges.
There were no tomato sales or livestock production in this batch; these domains need
explicit coverage, not extrapolation from melon-dominated outcomes.

## Feature-bank evidence and remaining gaps

The bank expands from 244 to **618 state/history candidates**, adding 374 mechanistic
descriptors. It was profiled on 11,584 legal observations, with history updated on every
callback. There are 372 varying and 246 constant descriptors, 23 exact-duplicate groups
among nonconstant columns, and 202 pairs with absolute Spearman correlation at least 0.995.
All 618 remain provisional: **zero final-model promotions and zero final-model rejections**.

All 78 animal-state/feed-care descriptors are constant in these crop-only trajectories.
Their engine-parity tests establish mechanics, not useful on-policy coverage. The same
distinction applies to water/fertilizer counterfactuals, temporal signals and market-pressure
descriptors that have not yet been activated in controlled policies. See the complete
[18-family coverage ledger](feature_coverage.md).

The next bounded research unit should test joint delivery/harvest/market timing, while adding
mechanistic livestock/fertilizer and capital-stress scenarios, followed by separately
registered development opponents/seeds. No additional cloud experiment was launched as part
of this evidence-publication step. Final optimization remains blocked.

## Verification and operational recovery

- AWS passed 75 tests and executed all three notebooks: 25 code cells, seven PNG fallbacks,
  no execution errors. Original study-1 notebook code and source lineage are preserved.
- An independent replay audit checked 46,016 candidate callback observations and recomputed
  all 11,584 vectors of 618 features from legal observations and causal history, with absolute
  tolerance 1e-12 and zero relative tolerance.
- The audit also replayed farm-action inventory transitions and checked all 64 product
  conservation identities: harvested = sold + final held + discarded. No ineffective farm
  actions were observed in the published games.
- All 175 run-manifest artifacts were downloaded and matched their recorded SHA-256 and
  byte counts. Raw trajectories and the feature matrix remain private; public summaries
  include source/engine/protocol identity and the [execution evidence](../reports/relationship_cloud_verification.json).
- The initial launch failed before game 1 because the batch initializer unpacked the wrong
  number of values. The initializer was corrected and a full synthetic 64-job orchestration
  and checkpoint-reuse regression test was added. No feature, policy, parameter, seed or
  design changed based on outcomes. The failure record was preserved; no game checkpoint
  was lost and the prior 80 games were not rerun.
- The corrected AWS runner completed in 1,055.75 seconds within its 1,200-second limit.
  Compute was stopped; the private versioned artifacts and persistent volume are retained.

The public verifier independently recomputes statistics and verifies both studies' 144
outcome rows, lineage, conservation and the exact executed notebook. This milestone closes
the bounded experiment and evidence review, **not** the feature-research completion gate.
