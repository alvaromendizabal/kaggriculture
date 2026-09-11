# Study 7: halted pilot, preserved evidence, and runtime diagnosis

## What was measured

The eight-job staffing-controlled protocol used the same hiring/market rule in both arms and changed only day-29 farm routing. Seven episodes were accepted and durably checkpointed. The last job (seed 1602, seat 1, coordinated) exceeded the actual AWS 500 ms policy-latency gate. The original runner rejected the payload before saving its maximum latency or game outcome. Those values are unknown. This study is halted, not a completed eight-game result.

The audit did not simulate any new game. It validated all seven local checkpoints against exact S3 object versions, encryption and SHA256; checked their original source lineage and accounting; and preserved the original failure log. Full profile output remains in private versioned S3; the public derived summary records its exact hash and object version.

## Paired evidence and representation coverage

All three complete pairs were identical before the terminal intervention. Coordinated minus sequential coin-margin differences were -1, -1 and +887. All three local match-score differences were zero. The seed-1602/seat-0 pair reduced unsold product units from 14 to 1. This is a context-specific mechanism result, not evidence of general opponent-population strength or a ladder rating. The incomplete fourth pair must not be omitted from an aggregate performance claim.

All 53 staffing candidates were evaluated on 161 saved final-day observations: 51 varied and 2 were constant. None was selected for a final model. Constants reflect a restricted observation slice, not useless features. `active_routed_workers` describes the proposed assignment even in the sequential arm; use actual action records and coordinated route diagnostics for execution claims.

## Why the runtime failed its margin of safety

Source inspection and cProfile identified repeated price-curve construction. The original solver independently computed revenue for each quantity from zero through available capacity. A cumulative curve preserves every legal price-floor/inventory transition while avoiding repeated prefix computation. The separate runtime candidate preserves DFS order, tie-breaking, resource conflict and storage constraints; it does not alter the frozen registered policy.

Thirty-seven deterministic tests passed in the AWS environment. Snapshot replay matched all 161 feature vectors and all 69 coordinated farm actions and route diagnostics exactly. Three alternating repetitions on each of three saved slow snapshots produced median timings:

| Development snapshot | Original features + routing | Candidate | Median speedup |
|---|---:|---:|---:|
| 1601 / seat 0 / step 702 | 370.05 ms | 31.42 ms | 11.78x |
| 1601 / seat 1 / step 709 | 358.54 ms | 19.39 ms | 18.49x |
| 1602 / seat 0 / step 699 | 382.92 ms | 41.75 ms | 9.17x |

These are measured component timings, not full policy acceptance. No original game timing has been replaced. The candidate has not been promoted. The earlier explanation that the problem was only GitHub-host scheduling was insufficient: the real AWS failure and profiling establish an implementation bottleneck.

## Registration correction

CI exercised seed 1601 before AWS preregistration, including full-game fixtures. That seed is development evidence, not an untouched confirmatory sample. Preserve the original registration and its timestamp, but do not repeat its blanket uninspected-outcomes claim. The public audit explicitly records this caveat.

## Next decision gates

The highest-value next experiment is a complete-callback acceptance test of the exact optimized solver, followed by a newly source-locked pilot only if it passes. Before that experiment, persist rejected payloads and measurements before applying acceptance gates. Record real wall and CPU timing; never replace actual deployment timing with the CI fixture clock. Keep the original seven accepted episodes immutable.

Feature research remains open. Priorities are family-level resource-conflict/shared-capacity ablations, distance- and wage-adjusted marginal worker value, season-long coordination, legal-history opponent-stock uncertainty, demand/scarcity regimes, and diverse opponent policies. Each proposed family needs a mechanism rationale, availability contract, tests, training/development-only screening, a paired ablation and stability evidence. Feature count and snapshot equivalence do not prove predictive utility.

## Evidence

- [Executed Study 7 notebook](../notebooks/03_staffing_research.ipynb)
- [Derived audit summary and full-report provenance](../reports/staffing_audit_summary.json)
- [Seven accepted episode summaries](../reports/staffing_observed_games.csv)
- [53-feature coverage registry](../reports/staffing_feature_coverage.csv)
- [Execution receipt](../reports/staffing_notebook_execution.json)
- Frozen algorithm: `src/kaggriculture_terminal/routing.py`; new candidate: `src/kaggriculture_runtime/routing.py`.

Historical notebooks 00–02, frozen policy sources, and historical study receipts remain unchanged.
