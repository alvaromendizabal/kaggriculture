# Sale timing, public demand and the last opportunity to realize cash

## Source-derived result: notebook 09

All 29 entries in the returned bundle manifest match their SHA256 hashes. Its latest report and run-status receipt record a completed experiment, not a new exception. The old 23:37 UTC error files are retained history; the corrected run finished at 23:58 UTC.

Only the first primary pair ran: seed 1601, seat 0, coordinated source, opponent `livestock_fertilizer`. Control finished with 44,840 coins and the aligned-all-final-day policy with 44,837. Opponent cash was 44,082 in both, so margin fell from 758 to 755; both remained wins. Both branches ended with zero residual products. The negative-effect gate correctly stopped after two 23-decision branches. Six source pairs were not run and no negative controls were reached. This is not a complete seven-pair comparison.

The late-sale ledger reconciles the entire three-coin loss. Four tomatoes sell for 332 coins at step 716 in the aligned branch versus 335 at step 717 in control. All farm commands match across the full suffix; all opponent commands match too. Other late product revenues reconcile without a net difference. At step 716 the aligned cash lead is +714, at 717 it is +83, and at 718 it is -3. Earlier cash was not extra final wealth.

The ledger uses the saved product liquidation values only where there are no competing same-product orders. It verifies their sum against actual per-transition cash changes before attributing product differences. It does not pretend to reconstruct unseen shop composition from that ledger alone.

## External mechanics supporting the new hypothesis

Primary implementation: Kaggle's official `kaggriculture.py`, interpreter SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` in the reviewed runtime.

https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/kaggriculture.py

The interpreter applies unit actions, then market orders, then known town demand. Known-shop demand operates at four-step intervals, with specialist multipliers and duplicate shop instances; town-center demand operates at 24-step intervals. Sales have nonlinear, product-specific price impact, with a special one-coin floor. Thus post-action inventory is not by itself a sufficient reason to sell immediately. A future demand event can make waiting more valuable; at the final callback that later sale is no longer possible.

This describes the pinned default mechanics, not proof of the private hosted Kaggle configuration. No claim about a current leading solution or leaderboard rating has been verified by these files.

## Hypothesis and implementation

H10: Preserve control sale timing before the final callback, and use the post-action inventory representation only at the last legal sale opportunity. This removes the earlier timing changes that caused notebook 09's observed loss while testing whether final inventory otherwise goes unsold.

The threshold 718 follows the fixed official 720-state / 719-decision horizon; it is not tuned to a seed, outcome, or observed price. The wrapper calls the same control policy every time, maintaining the same memory. Its only action-changing feature is the final-callback indicator. It does not introduce a different solver, ensemble, buying rule, hiring rule, farm task, market curve, or reserve parameter.

The prior aligned-all-day treatment remains stopped and rejected for promotion. This is a new, explicitly narrowed hypothesis, not a retry of the same failing test or permission to ignore its loss.

## 120 new timing descriptors

Three shared fields represent the final callback, remaining future sale callbacks and offset until the next known shop event. Each of nine products has its post-action quantity, current quote and one-sided immediate liquidation value, plus five fields for each of horizons 1 and 4: availability, known demand units, demand-only quote, demand-only liquidation value and conditional holding premium.

All unavailable scenarios are zero-masked with an explicit availability field. In particular a terminal premium is zero because the future sale is unavailable, not because waiting is valued as a loss equal to today's inventory. These tables cannot distinguish all future opponent strategies. Demand-only values hold the currently visible shops fixed and assume no competing trades. The runner restricts this investigation to day 29, so it does not extrapolate future random shop additions.

Current seeds, labels, opponent orders, opponent private inventory, later observations and terminal rewards never enter the feature interface. Product quantities come only from a copied application of the player's own proposed farm commands. Metadata seed/seat/arm is appended by the evaluator for grouping; it is never an actor input feature.

These descriptors are candidate activation diagnostics, not trained predictors or proven importance rankings. Only the last-callback gate is action-ablated here. A feature can have zero activation in these final-day sources yet remain useful earlier in the game.

## Why two transitions per source episode are enough here

For each source the wrapper recomputes all 23 terminal-day callbacks in temporal order and proves exact action equality with the saved control through step 717. It also verifies that the control action on step 718 matches the recorded one. Because no earlier action or actor memory is changed, both branches reach the same saved final observation under the deterministic pinned rules. The opponent is recomputed from its own legal final observation using the documented clock-only policy state; its action must match the recorded source.

The evaluator then runs the control and gated candidate once each through the official interpreter. Control final rewards must reproduce the recorded episode. This provides the exact endpoint comparison for the last-decision-only change on that preserved trajectory without resimulating its unchanged prefix. It is not a shortcut valid for earlier interventions, learned stateful history changes or a different opponent. The equality proof must fail closed if any prefix command differs.

At most 154 prefix equality checks and 14 research transitions are performed; 38 separate interpreter calls exercise artificial mechanics fixtures. Earlier notebook experiments are not rerun. No new full season, fit, submission or paid cloud job is launched automatically.

## Acceptance and stop rules

Mechanics fixtures compare known-demand forecasts with real interpreter-held-then-sold cash for all nine products and both seats. Two more tests check final-callback deposit and sale with price-aware expected cash. Unit tests include the previous million-inventory wheat error (13 coins, not a forced floor), masks, chronology, input immutability, seed/reward exclusion and checkpoint corruption.

All callbacks are measured with the real wall clock and must be at most 500 ms. The worker stops after 180 seconds; the parent allows two seconds for termination. A heartbeat is printed every ten seconds. Each completed episode comparison is saved atomically and hash-verified by readback. A timeout preserves valid checkpoints but is not automatically retried. A new failure requires diagnosis before another attempt.

Negative primary coins, margin or match outcome stops the new hypothesis. No activation or no terminal benefit also prevents scale-up. The four sequential sources are negative controls, not additional independent efficacy examples. There are only three coordinated sources in two seed blocks and a related opponent, with a missing fourth source. No turn-level p-values, confidence intervals or validation claims are justified.

## Next research decisions

If this narrow correction shows a benefit, freeze it as a provisional development change and validate on fresh groups and genuinely different source-identified opponents. A valid submission is a separate necessary measurement of the leaderboard gap; do not translate coins into rating or claim 3140.0 has been reached.

The next more ambitious feature round should represent the opportunity cost of waiting: public-demand event phase, quantity-dependent market impact, possible rival supply, delivery bottlenecks and the cost of stranded cargo. A one-step demand-only premium alone must not trigger a new market timer without opponent/capacity risk checks and controlled paired outcomes. Do not tune a 3-coin threshold to this example.

After that, major open rounds include joint worker–task marginal value with resource conflicts; crop maturity, death and watering windows; fertilizer opportunity cost; livestock feed/care timing; marginal labor payback across legal workforce sizes; land and crop investment payback; and strictly causal opponent-market history. Each requires defined information availability, explicit tests, training/development-only screening, family ablation and grouped stability evidence.

The old callback's rejection of more than three hired hands on either farm remains a submission-readiness risk. A broader extractor passing tests does not certify the complete agent. This milestone intentionally does not silently alter that domain boundary.

## Persistence and publication

All earlier source and results remain read-only. New checkpoints are local and in the returned ZIP, not automatically copied to S3. The research package is not a GitHub commit or merge. Manual artifact integration/publication requires review of its result and a separate commit; do not `git add .` in the home directory or publish private raw episodes.
