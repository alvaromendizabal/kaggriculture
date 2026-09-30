# Final-sprint research arc — September 29–30, 2026

This memo records the competitive research completed after public checkpoint `8fa7538`.
It is intentionally evidence-first: successful negative experiments are preserved, execution
failures are separated from scientific rejections, and Kaggle rating is never conflated with
local official-engine win rate.

## Executive summary

The sprint produced one major validation correction and several decisive negative results.
The old fixed opponent panel had become saturated: the active keeper looked close to perfect
locally while remaining around the high-1600s on the live ladder. The project therefore moved
to replay-aligned validation using the keeper's own recent public ladder episodes.

That new validator reproduced terminal rewards exactly and measured the keeper at only 47.9%
win/tie score across 48 recent ladder episodes. This was the key discovery of the sprint.
Subsequent work tested fixed replacement policies, boundary-level expert borrowing, rolling
chronological rules, and a project-authored native harvest/service mechanism.

## Reproducible experiment chronology

| Milestone | New official-engine games | Decision | Main conclusion |
|---|---:|---|---|
| Late-layer ablation | 234 | `REJECTED_SCREEN` | Removing post-Step1002 controller layers did not improve the submitted reference. |
| On-policy economic population | 448 | `TRAINING_REJECTED` | The bounded economic policy converged to no useful interventions. |
| Coherent frontier routes | 428 | `SCREEN_REJECTED` | Kaito/DECEM/DSM whole-route transfer underperformed the keeper sharply. |
| Current public adaptive frontier | 300 | `SCREEN_REJECTED` | Three newer public adaptive policies also failed the current league. |
| Real-ladder alignment | 48 replay episodes evaluated across policies | `NO_FIXED_POLICY_IMPROVEMENT` | Fixed-policy replacement was inferior, but the validator now matched the live failure distribution. |
| Boundary selector | 1,084 calibration/branch games | `INNER_VALIDATION_REJECTED` | Hindsight branch oracle had signal, but the first small tree could not predict rescue states. |
| Rolling boundary CV | 0 new games; 1,084 reused | `ROLLING_CV_REJECTED` | Low-capacity forward-only rules failed to generalize chronologically. |
| Native harvest/service | 94 attempted development games | execution failure | Post-terminal diagnostics transport rejected otherwise completed games; repaired handoff prepared. |

## Validation mismatch correction

The most important sprint result was not a new policy. It was a corrected evaluator.

The replay-aligned validator requires exact terminal reward parity for the keeper before any
counterfactual policy is interpreted. On the 48 recent keeper episodes used in the sprint, the
keeper produced 18 wins, 10 ties, and 20 losses: a 47.9% win/tie score. The older 24-episode
development slice was 9 wins, 4 ties, and 11 losses (45.8%).

This explains why earlier 90–100% local panel scores failed to predict ladder movement: the
panel was measuring a narrow strength profile rather than the opponent distribution actually
responsible for live rating changes.

## What did not transfer

### Historical-controller simplification

Step1002/961/953 prefixes all matched the keeper's 90% score on the registered panel but lost
directly to the keeper. The direction was closed.

### Public whole-route transfer

Kaito route variants and two complete recent leader-derived routes were tested from turn zero.
The keeper scored 87.5% on the shared panel; the best transferred route scored 18.75% and went
0% direct head-to-head against the keeper. Whole-route transplanting was closed.

### Newer public adaptive policies

The Thomas 2945 Farm, replay router, and public-state router all passed parity checks but scored
25%, 16.7%, and 16.7% respectively on the shared panel while the keeper was effectively perfect.
Public-policy transfer was therefore closed as a shortcut.

## What the real-ladder experiments learned

Fixed controllers were globally worse than the keeper, but some rescued isolated keeper losses.
For example, `timing_current` rescued three development losses while sacrificing five keeper wins.
The 1,080 boundary counterfactual games showed a hindsight oracle gain of roughly seven score
units across 24 development episodes, but the signal was not stable enough for a deployable
low-capacity router.

Rolling-origin validation used folds 1–12→13–16, 1–16→17–20, and 1–20→21–24. The strongest
threshold/two-rule families reached only +0.5 forward score units with no rescued losses, so the
newest-24 holdout remained untouched.

## Reliability engineering completed during the sprint

The research runner also hardened several failure-prone boundaries:

- explicit one-argument vs two-argument agent entrypoint handling;
- game-validity checks before optional post-terminal diagnostics;
- source-hash and engine-hash binding for accepted checkpoints;
- browser-suffixed artifact selection by SHA-256 rather than filename recency;
- durable upload-intent journaling and duplicate-submission reconciliation;
- bounded memory/disk/runtime gates;
- exact chronological split and no post-hoc promotion-threshold changes;
- restart reuse of accepted game checkpoints;
- corrected distinction between execution failure and successful negative experiment.

## Current native direction

The next registered scientific question is a project-authored harvest/service recovery layer on
the exact keeper. It leaves farm strategy, movement, planting, purchases, market planning, and
terminal logic with the keeper, and reallocates only ineffective worker actions toward legal
productive service when a full joint-transition safety check succeeds.

The first attempt reached the development stage but hit an inherited post-terminal telemetry
transport bug. The corrected recovery artifact establishes completed-game validity before asking
for optional diagnostics. Therefore no scientific conclusion has yet been drawn about the native
harvest/service mechanism.

## Reproduction boundary

The repository publishes project-authored validation, routing, and service-control logic plus the
aggregate evidence required to reproduce the research conclusions. Raw Kaggle replay corpora,
credentials, submission archives, private AWS checkpoints, and third-party controller source are
not committed. Public external controllers are referenced by immutable upstream identities and
content hashes; a full live rerun requires competition access.

Clone-time verification is available through `scripts/verify_final_sprint.py` and the normal test
suite. The companion notebook `notebooks/56_final_sprint_ladder_alignment.ipynb` is saved with
executed outputs.
