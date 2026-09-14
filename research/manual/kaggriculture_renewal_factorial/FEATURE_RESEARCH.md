# Notebook 16 — early clearing × maintenance eligibility

## Decision question

Does clearing empty, fully exhausted recurring crops help when ordinary WATER eligibility is preserved? Notebook 15 evaluated three cells of a two-factor design. This package completes only the missing cell; it does not repeat successful simulations or add another broad policy.

Factor R: remove WATER jobs for empty exhausted ongoing crops. Factor C: enable the existing crop-layout DIG job early for those plants. Eligibility remains subject to the original replant horizon and zero-indexed days 8 through 27. The other policy rules, priority constants, distance costs, layout, hiring, market logic and exact final-day allocator remain fixed. Notebook 10's final-callback sale correction is common to all four cells.

| Cell | R | C | Evidence |
|---|---:|---:|---|
| Control | 0 | 0 | Reuse notebook 15 |
| Retire | 1 | 0 | Reuse notebook 15 |
| Clear only | 0 | 1 | This experiment only |
| Combined renewal | 1 | 1 | Reuse notebook 15 |

The new AST transformation changes only the crop-layout WEED clearing condition. The ordinary WATER expression remains syntactically unchanged. A null transformed policy has an always-false added condition and must reproduce the original policy's emitted actions. The original file's Git-blob hash must match; no repository file is patched.

## Mechanistic basis and outside references

The official Kaggle engine is the domain authority. Ongoing tomato/strawberry plants have finite scheduled production events. DIG removes a plant, whereas HARVEST keeps an ongoing plant. New plants need watering on the planting day to survive that night's refresh. Restoring empty plots therefore interacts with future maintenance workload; it is not an unconditional profit improvement. All mechanics are checked against the pinned installed engine, not replaced with agronomic assumptions.

Primary sources:
- Kaggle simulator: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
- Official description: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md
- NIST two-level factorial designs: https://www.itl.nist.gov/div898/handbook/pri/section3/pri3331.htm

The NIST source supports the experimental organization, not a Kaggriculture feature-performance claim. Real-world soil, weather or satellite signals have no defined mechanism in this experiment. They are not added as generic columns.

## Newly logged representation

Sixteen state descriptors in `joint_features.py` quantify overlap between eligible clearing jobs and ordinary watering jobs, seed readiness, immediate maintenance demand, worker-normalized load and an optimistic DIG–PLANT–WATER work estimate. Several are reused primitives or contextual counts. They are **not sixteen proven novel predictors**, and no learned weights or thresholds use them here.

They read only current own farm, current public clock, current own seed stock and fixed mechanics/layout. Neither final rewards, future observations, opponent private inventory, recorded opponent actions nor evaluation seed are feature inputs. The evaluator necessarily uses source identifiers, both observations and recorded prefixes separately. Output feature tables are separate from endpoint and trajectory tables.

No arbitrary worker truncation occurs in these descriptors. This does not repair the inherited <=3-hired-hands complete callback restriction. Individual seed-ready plots need not be simultaneously feasible. Manhattan travel plus three unit actions is an optimistic single-worker sequence, not a global allocation guarantee. A missing opportunity yields zero with `clear_eligible_spent_plots` as the availability mask.

## Full-path activation check

Use exactly the original selected source: seed 1601, seat 0, coordinated candidate versus livestock_fertilizer. It is already development-contaminated. Evaluate **all 527 control-path observations**, steps 192..718, not a sparse stride or outcome-selected subset. For every observation, verify original versus null versus saved control action equality. Verify the clear-only action equals control outside the intervention window. Record actual callback time and enforce 500 ms per measured callback.

If all 527 candidate actions equal the already-verified control actions, the entire paired path is identical by induction from the same starting state, policies and random stream. In that case the new cell reuses the control endpoint with an explicit action-identity proof and **zero** interpreter transitions. A missing observation, failed comparison or sparse screen cannot justify that shortcut.

Otherwise run just one new branch: replay the 192 recorded prefix transitions into the original seeded environment and then advance 527 responsive decisions. No manual shop/randomness injection is used. Reference and null comparisons are recomputed on each new state. Same-state action equality after day 27 is required even if the two trajectories have different states. Seeds and private evaluator state are not passed into the actor.

## Factorial calculations and interpretation

For endpoint Y, let f00, f10, f01 and f11 be the four cell outcomes.

- Clearing under ordinary maintenance = f01 − f00.
- Clearing under retirement = f11 − f10.
- Retirement without clearing = f10 − f00.
- Retirement with clearing = f11 − f01.
- Difference-in-differences = f11 − f10 − f01 + f00.

The output labels this last quantity **difference-in-differences**, not the half-scaled conventional factorial interaction effect. Averaged main effects are also reported. These are within-block controlled contrasts, not independent causal contributions of market prices or statistically significant population effects. Four arms share one source block; do not treat them as four independent seeds, pool turns as replicates, compute spurious confidence intervals or infer generalization.

Local win/draw/loss is the game-level result; margin and own cash are reported separately. Keep the previous conservative no-decline guard visible. A margin improvement with lower own cash must be labeled mixed, not silently rejected as a loss or adopted through a post-hoc metric switch. No arm is promoted automatically.

## Stop and continuation rules

Screen cap: 120 seconds; pilot cap: 120 seconds; cleanup grace: two seconds. Stop immediately on a malformed source, hash mismatch, action parity failure, inherited observation-domain failure or callback over 500 ms. Failure measurements are saved first. An unchanged failed/active/interrupted stage is not automatically retried. Successful daily screen checkpoints and the one complete new branch are hash-verified and reusable. There is no cloud upload, install, Git write or submission action in this package.

After the fourth cell is resolved, do not keep tuning crop eligibility on seed 1601. A promising arm must face newly registered seed groups, both seats and genuinely different opponents. Separately close the full-callback workforce restriction and produce a validated submission before comparing to the user-supplied 3140.0 leaderboard benchmark. Broader hiring value, crop mix/production timing, land payback, task allocation and causal public-market features remain open; this package does not declare their investigation complete.
