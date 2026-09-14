# Notebook 09 | Test the cash mechanism over a complete remaining horizon

## Evidence that justifies this experiment

The uploaded notebook-08 result passed on 161 legal observations from seven saved development episodes. It reported 11 changed SELL-order lists, six positive one-step own-cash differences, no negative one-step own-cash differences, and exact reproduction of 161 recorded control transitions. The largest immediate difference was 1,440 coins. Only one positive row was on the final callback: 42 coins at seed 1602, seat 0, coordinated source policy. Candidate callback maxima were 94.43 ms for control and 20.88 ms for aligned. These are local replay measurements, not hosted competition limits or a leaderboard score. Source data, hashes and the full previous report accompany this package.

An earlier cash receipt can be caught up by the old policy later. It can also alter prices, later task choices and the opponent's reaction. We therefore cannot sum the isolated step effects or treat 161 turns as independent trials. The next experiment tests endpoints, not another generic expansion or a different algorithm.

## Hypothesis and scope

**Hypothesis:** applying the existing terminal SELL rule to the post-action inventory of the farm commands actually emitted increases final banked cash or coin margin in the coordinated policy, without changing routing/hiring/reserve rules. We test the exact notebook-08 implementation, not a retuned version.

Two trajectories start from each recorded callback-696 state. One uses the control policy; the other uses aligned quantities. Each trajectory executes every decision through callback 718, then measures the terminal state at 719. Neither trajectory is reset after an intermediate effect. The official pinned interpreter advances both sides jointly. The unchanged `LivestockPolicy('fertilizer')` is called again using its own current observation on every turn of each branch. Its actions are not replayed from a tape in the treatment branch.

The policy state includes only arm, previous step, and player. It is restored through its explicit state interface. The control branch must reproduce both players' recorded actions, every subsequent public/private state, and the recorded final rewards. Any failure stops the run; no mismatched continuation may contribute to results.

## Attribution

On each treatment-branch observation, a separate control callback sees the **same** own observation. It must return the same farmer commands, hand commands and non-SELL orders as the treatment. This checks the direct intervention. Across the two evolving trajectories, later farm commands may legitimately differ because earlier sales changed the state. Such downstream divergence is measured, not prohibited or mislabeled as an additional intervention.

The unchanged policy still admits only observations with at most three hands on either farm. This experiment does not broaden that action contract. Earlier variable-workforce extraction success cannot certify the current agent on larger workforces.

## Source inventory and statistical limits

The seven source suffixes consist of three coordinated primary comparisons and four sequential no-change controls. There are only two development seed blocks, 1601 and 1602, and one related opponent. Opposite seats can be symmetric. The missing original coordinated seed-1602/seat-1 episode remains missing; this package neither fabricates it nor silently reruns it. The original study was interrupted by a latency failure, so the source evidence is latency-censored.

Sequential controls test whether a case whose base farm commands already match its market calculation remains unchanged. They are not four more efficacy trials. Primary results are shown by seed and seat, with descriptive within-seed means only. There are no turn-level confidence intervals, fitted thresholds, significance claims, bootstrap claims or holdout labels. The protocol was specified after seeing notebook 08 and is not retrospective preregistration.

## New candidate family: terminal liquidation exposure

Twelve additional, current-observation descriptors are implemented in `terminal_context.py`. They distinguish cash already in the shed from cargo that can or cannot independently reach a shed and be deposited before the final market phase. They also describe conditional marginal liquidation value and shared-capacity pressure. `feature_dictionary.csv` gives each definition, availability assumption, limitation and deployment status.

These twelve descriptors are **logged only** in this milestone. They do not modify the tested actions, so any measured policy gain is attributable to the existing post-action inventory intervention—not to these newly logged columns. Their activation can identify the next narrowly scoped delivery/stranded-inventory hypothesis. They are not selected predictors, learned values or new feature-importance results.

For a worker at position p and remaining decision count R, independent delivery is feasible when `min Manhattan(p, shed_access) + 1 <= R`. The `+1` is the DROP command; its market phase can sell deposited goods in the same turn. The official interpreter permits movement across locked tiles. This test ignores shared shed capacity, task competition and future harvests. Hypothetical marginal cargo value is calculated from the exact one-sided price curve after current shed stock; it is not joint achievable profit or a forecast of rival sales. Unknown opponent inventory is never read.

## Measurement and gates

Endpoint outcomes: final banked coins, final coin margin, local match result (win 1 / tie 0.5 / loss 0), and residual products in shed and worker inventories. Report all, not only the most favorable. These local match results are not Kaggle's rating.

The full candidate, live opponent and same-state shadow callbacks are individually timed with the real monotonic clock. Each must remain within 500 ms on evaluated states. The expensive worker is capped at 180 seconds with a two-second termination grace. There is a heartbeat every ten seconds. No tuning is permitted in response to partial favorable results.

Every completed 23-decision branch is written atomically, checksummed and immediately read back locally. Reuse requires identical code, experiment protocol, engine, prior report, source episode and branch identity. Bad hashes or changed lineage are errors, not cache misses. A failed attempt does not retry automatically. No new initial-state games, training, package installation, network calls, AWS resource writes or Git writes occur.

A primary pair with negative coin, margin or match-result change stops expansion immediately after preserving the pair. A sequential control that changes is an implementation failure. If all primary comparisons activate but show no terminal benefit, stop this performance direction rather than running a broader version of the same test. If the effect remains positive, it is provisional and requires fresh groups, distinct opponents and broader action/runtime coverage before generalization or leaderboard claims.

Local EBS checkpoints and a downloaded results ZIP are the recovery mechanism here. This is **not** an S3 upload/readback workflow; no off-instance automatic backup is claimed. The original raw data and frozen source are read only.

## Subsequent research rounds (not run automatically)

1. **If this mechanism persists:** preserve the exact intervention as provisional, then design fresh, grouped validation with genuinely different source-identified opponent behaviors. Inventory existing development/CI seeds first. Resolve or explicitly scope larger-workforce callback coverage before any submission-readiness claim.
2. **Labor and delivery representation:** joint access, competition for tasks, opportunity cost of the first command, complete-workforce indexing, capacity-aware delivery, and stranded valuable goods. Compare controlled family interventions rather than independent-worker scores that cannot be jointly realized.
3. **Production-to-cash timing:** remaining harvest cycles, crop decay and survival, watering/fertilizer timing, collection/deposit delay, and whether a production bonus has time to reach the bank. Use chronological availability tests and mechanism fixtures before fitting anything.
4. **Livestock and capital allocation:** feed opportunity cost, delayed care bonuses, manure allocation, incremental worker price, land utilization/payback and liquidity. Compare these alternatives under the same cash constraints.
5. **Causal market and opponent context:** known demand events, own price impact, publicly observable rival supply, and uncertainty in future shops or hidden inventories. Historical features must reset by episode and update causally, never from future replay or private rival data.

The goal remains stronger competition performance, including pursuit of the user-supplied 3140.0 benchmark. Its current leaderboard status is not verified here and no valid submission rating is contained in the uploaded report. No feature count, local cash total, win fraction or successful notebook can be converted into that rating.

## Primary-source grounding

- Project source: `src/kaggriculture_staffing/experiment.py` at commit `7194116dfc92a8663139611233b5a221dad431a4` identifies the source opponent, source episode schema and accounting requirements.
- Project source: `src/kaggriculture_livestock/policy.py` at the same commit explicitly implements `state_dict` and `from_state_dict` for arm, last_step and player, and requires consecutive legal observations.
- Official interpreter: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py . The experiment rejects any installed interpreter whose SHA256 differs from `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`; the moving URL is not used for runtime loading.
- Ross, Gordon and Bagnell (2011), *A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning*: https://proceedings.mlr.press/v15/ross11a.html . Conceptual support only: sequential decisions change the distribution of later states. This package does not implement their algorithm or claim their paper establishes a game-specific improvement.

No source establishes that the proposed feature family is already the most predictive or sufficient to beat a leaderboard record. The controlled measurements are intended to answer part of that question.
