# Round 07 · Action opportunity features

## Evidence boundary

The latest user upload, `kaggriculture_workforce_milestone(1).zip`, is byte-identical to the original input package. Its notebook has zero executed cells and zero outputs; it contains no `outputs/report.json`. This does not establish that the AWS execution failed or was never attempted. It establishes only that this upload does not contain that execution's results. `reference/upload_review.json` records the inspection.

The connected GitHub read returned main `7194116dfc92a8663139611233b5a221dad431a4`. This package has not been pushed, committed or merged. It neither changes the frozen Study 7 agent nor writes cloud resources.

## Registered hypothesis

Terminal decisions should be represented in terms of **whether, when, and at what incremental value a worker can move visible resources into banked money**, rather than raw stock counts alone. A second hypothesis is that different target tasks often imply the same immediate movement command; task changes should not be mistaken for action changes.

These are hypotheses. No claim is made that the new features are the most predictive, that this round improves the official metric, or that a leaderboard score of 3140.0 has been independently verified. The user-supplied benchmark remains an objective, not a measured result.

## Primary-source mechanics used

The reviewed official interpreter establishes the following details:

- `_apply_unit_action`: movement through LOCKED tiles is allowed; workers retain their observation/action indices; DROP admits inventory in iteration order, discards overflow and resolves before the LOCKED guard.
- `interpreter`: worker actions occur before market sales; crop decay occurs afterward. The final actionable step for the pinned 720-state configuration is 718.
- `_decay_plants`: after the crop's maximum lifespan, yield declines on alternating eligible steps. HARVEST at a future arrival must account for decay on earlier movement steps, not decay after the harvest itself.
- `_commit_unit`: a sale at the one-coin floor does not increase market inventory. Quantity-aware liquidation therefore cannot be reduced to quantity times current headline price.

Primary source: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
Reviewed Git blob: `3c202c7ee921da239356789e266b694635103fc4`.
Runtime acceptance requires **kaggle-environments 1.32.7** and interpreter SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`. A current documentation page is not substituted for the pinned runtime. In particular, town timing described in the current README differs from the pinned code reviewed here; this round does not model future town consumption at all.

Related primary conceptual work: Aziz et al., *Multi-Robot Task Allocation — Complexity and Approximation*, AAMAS 2021, https://arxiv.org/abs/2103.12370. Its cost/budget-constrained allocation setting motivates checking coupled resource access, but is not the same optimization problem and does not prove game-specific feature value.

## Implemented families

| Family | Actual representation | Information availability and tests |
|---|---|---|
| Delivery deadlines | Manual action count, final-decision slack, admissible harvest-then-drop and carried-inventory drop paths | Current clock, own worker positions, current tasks; exact deadline boundary tests |
| Yield survival | Visible units, units at arrival, unavoidable decay loss | Current public crop state and pinned decay rule; closed-form versus iterative tests and on-AWS primitive parity |
| Quantity-aware liquidation | Incremental sale value after existing shed stock; nonlinear price-impact loss; value per worker action | Current observed market curve and own inventory only; explicit frozen-market scenario, not a future quote |
| Deposit bottlenecks | Accepted/discarded quantities, capacity value loss, incremental harvesting value relative to carrying-only deposit | Own private shed/inventory, real DROP order; can expose a **negative** marginal harvest value when cheap goods displace valuable carried goods |
| Alternative actions/access | Best different-first-command rate, first-command regret, alternative worker travel advantage, eligible-worker counts, contested independently preferred tasks | Present observation and current candidate menu only; no seed, final reward, hidden rival inventory or future replay passed to extractor |

The implementation returns **14 state candidate summaries**, a variable-length option table, and **8 audit-only probe counts**. Worker and task counts may change without truncation. The descriptor dictionary separates identifiers, candidate features, counterfactual rates and audit outputs. Large row/column counts are not evidence of predictive value.

## Exact scenario, not an implicit forecast

Each candidate is either a shortest deterministic path to HARVEST followed by a shortest path to DROP, a direct DROP path for carried goods, or PASS. All movement occurs on the final day. One deterministic shortest-path tie-breaker is used. The candidate must finish no later than the final actionable callback to receive positive full-scenario value.

The quantitative scenario holds the market fixed until liquidation and leaves current shed inventory unchanged until the candidate's DROP. Other own workers do not act in this independent scenario. There are no intervening purchases, rival orders, town purchases or overnight refreshes. Existing shed stock is liquidated first for the incremental valuation calculation; its baseline sale value is subtracted. Values are therefore **conditional marginal values**, not predicted future money.

DROP follows the iteration order in the supplied inventory mapping. A saved replay may have had its JSON keys sorted when archived, so this scenario does not reconstruct an unrecorded original live insertion order. On-AWS parity checks intentionally operate on the same supplied copied observation.

Independent workers can prefer the same harvest. Their sale values must not be summed into a realizable joint income forecast. Joint assignment, replanning, simultaneous deposits and the existing policy's full callback remain separate gates.

## Four one-family removal probes

All probes use the same deterministic per-worker selection procedure and candidate identities. They remove one ingredient from the full scenario: deadline gating, travel decay, storage capacity, or nonlinear sale impact. PASS wins zero-value ties.

Compare the **first action**, not just the selected resource. A change from one northward task to another northward task is not a different immediate command. First-action regret compares the best attainable rate of each distinct first-command group.

The probes are **offline activation tests**, not game-outcome ablations and not an allocation-solver comparison. No proposed action bundle is deployed to an agent. Variation or a changed action is necessary evidence of activation, not sufficient evidence of beneficial performance.

## Data and isolation

The live audit reads exactly the seven accepted restored development episodes, 23 final-day observations each. It verifies outer file hashes, checkpoint checksums, lineage and episode validation. Seed/seat/opponent/source-arm metadata is attached **after** feature extraction. It never enters the feature function. No validation or holdout episodes are read, no model is fit, and no learned threshold is chosen.

The original eight-game pilot was latency-censored. Seven accepted episodes and repeated turns are not independent out-of-sample evidence. Reports summarize probes within each episode and then seed/opponent blocks; no confidence intervals or p-values are manufactured from pooled turn rows. Constant features in this terminal slice are not globally rejected.

## Stop / continue decisions

1. Stop on source, package, engine, data, alignment, clock, test or primitive-parity failure. Keep both worker and supervisor failure logs. Do not rerun a failed gate unchanged.
2. If a family's removal never changes the first command, do not spend full games on that unactivated intervention. Inspect whether the candidate menu is missing relevant choices or the effect needs a different state regime.
3. If it changes commands, inspect representative states and the concentration of changes across **observed** episode blocks. This does not yet authorize a claim of performance improvement.
4. Integrate one clearly activated family into an equal-hiring/equal-market/equal-solver control and treatment. Measure the complete policy callback including feature construction. Preserve the exact maximum, failing observation and exception before any latency gate rejects the result.
5. Only after callback and submission-integrity gates pass, run a fresh bounded paired-game pilot with distinct source-identified opponents, both seats and durable per-game checkpoints. Keep failed runs visible. Compare local match outcomes, coin margin, unsold goods, ineffective actions and latency. Local metrics must never be converted to leaderboard ratings.
6. Retain features only after controlled contribution and stable grouped evidence. A valid baseline submission can measure the external gap while feature research remains open; submitting a baseline is not a declaration that feature engineering is finished.

## Remaining research queue — explicitly not exhausted

| Next family | Missing representation / intervention | Cheap next test before a game pilot |
|---|---|---|
| Coupled action opportunities | A worker's loss from committing an action and the opportunities preserved for other workers | Exact first-command grouping and allocation parity on copied states, then full callback |
| Crop time-to-cash | Maturity, watering/fertilizer timing, decay, survival and remaining harvest opportunities net of labor | Crop-transition fixtures over early, middle and late game; temporal availability tests |
| Livestock production economics | Feed acquisition/delivery, care-bank timing, output caps, recovery and animal survival | Species-specific pinned transition parity and regime activation |
| Hiring and land investment | Marginal worker access, daily expiration, affordability and remaining season payback | Equal-policy one-action counterfactuals; distinguish valuable access from mere worker count |
| Market timing and public rival pressure | Known-shop demand, causal price history and visible competing supply with uncertainty | Pin configuration; history reset/leakage tests and uncertainty-aware stress envelopes |
| Robustness and external measurement | Opponent variation, both seats, unseen seed groups and valid submission artifact | Grouped protocol and validated baseline submission; not an excuse to stop feature research |

No learned rankings, ensembles, giant feature search or full historical reproduction is launched by this package.
