# Final evaluation findings · September 29–30, 2026

**The decisive improvement was a more credible evaluator, not an unsupported new policy.**

The fixed opponent panel had become saturated. A replay-aligned check of 48 recent
keeper episodes instead measured **18 wins, 10 ties and 20 losses**, or **47.9%**
win/tie score. The older 24-episode development slice recorded **9 / 4 / 11**, or
**45.8%**. These are local episode statistics, not official Elo or a current rating.

[Original aggregate record](../../reports/final_sprint_2026-09-30.json) ·
[Executed analysis](../../notebooks/56_final_sprint_ladder_alignment.ipynb) ·
[Evaluation protocol](final_sprint_protocols.md)

## Why the reference was retained

The aligned evaluator required exact terminal-reward parity for the keeper before
counterfactual results could be interpreted. Fixed replacements were globally
worse even where they rescued isolated losses. A hindsight boundary oracle had
approximately seven score units of opportunity across the 24 development episodes,
but the learned selector failed its inner validation.

Forward-only evaluation reused **1,084 accepted calibration/branch results** rather
than replaying those games. The strongest threshold/two-rule families reached only
**+0.5 validation score units with no rescued losses**. They failed the registered
promotion gate, and the newest 24 holdout episodes remained unopened by that
selection attempt. Negative results are preserved; they are not promoted into
capabilities of the final agent.

## Reliability boundary

Accepted work was bound to source and engine identities. Verified checkpoint reuse,
writer exclusion, chronological grouping and bounded execution prevented discarded
work from being mistaken for a fresh experiment. A separate unfinished experiment
stopped at a post-terminal diagnostics failure. That operational failure did not
establish either a positive or negative policy result, and its proposed recovery
mechanism is not shipped as an implemented final capability.

## What remains reproducible

The maintained tree contains observation audits, evaluation and recovery contracts,
the educational simulator, compact original evidence and executed reviews. It does
not publish the private competitive policy, routing/service-control implementation,
raw replay corpus, third-party controller source or private checkpoints.

Run the [public review](../REPRODUCIBILITY.md) for independently checked aggregate
arithmetic and simulator exports. Its educational mechanics are distinct from the
official game. Historical cloud and ladder records identify completed work, not
currently provisioned AWS resources or fresh performance measurements.
