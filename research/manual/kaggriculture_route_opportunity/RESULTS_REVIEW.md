# Notebook 10 — verified result and decision

Source: the user's `kaggriculture_sale_timing_results.zip`. All 27 entries in its bundle manifest match their SHA256 checksums. The saved notebook has 13 executed code cells and zero error outputs. The worker reported 70 passing tests, 7 completed comparisons, 154 source-prefix action checks, 7 source-final-reward checks, and 8.074613 seconds of elapsed worker time.

## Primary endpoint comparisons

| Source | Control coins | Final-sale-gated coins | Difference | Local match change |
|---|---:|---:|---:|---:|
| Seed 1601, seat 0, coordinated | 44,840 | 44,840 | 0 | 0 |
| Seed 1601, seat 1, coordinated | 44,840 | 44,840 | 0 | 0 |
| Seed 1602, seat 0, coordinated | 51,764 | 51,806 | +42 | 0 |

The four sequential negative controls stayed unchanged. In the improved primary case, remaining product inventory fell from one unit to zero. No other primary endpoint improved. Maximum candidate callback time was 86.159432 ms. Maximum logged timing-feature extraction was 0.341516 ms. Local match indicators and in-game coins are not Kaggle leaderboard ratings; no submission score is present.

The report decision was `PROMISING_DEVELOPMENT_ONLY_FRESH_VALIDATION_REQUIRED`. The source lacks the seed-1602, seat-1 coordinated episode. There are two already-examined seed blocks and one related opponent, not seven independent validations. The 120 timing descriptors were logged; only the fixed final-callback indicator changed actions. No claim that all 120 features improve outcomes is supported.

## Decision for the next milestone

Preserve the final-sale gate as a provisional development baseline, without declaring it independently validated or spending another round optimizing those 42 coins. Investigate another plausible representation bottleneck: routes discarded by each worker's independent top-eight filter before the exact joint allocator is called.

This is a new hypothesis based on source inspection, not a finding in the returned notebook. Notebook 11 must first measure whether it activates. It tests one family with the solver and sale rule held fixed, then at most one primary endpoint pair and one no-change control. More features are not presumed to be better.
