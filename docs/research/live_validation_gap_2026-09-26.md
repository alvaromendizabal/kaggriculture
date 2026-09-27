# Live validation gap — labor treasury intervention

**Research checkpoint: 2026-09-26 / 2026-09-27 UTC**

## Question

A narrow labor-funding intervention fixed a severe local matchup failure and passed independent confirmation. Did that improvement transfer to the live Kaggle ladder?

## Mechanism

The intervention preserves enough late-day cash for fixed-cost next-morning labor commitments by reducing seed-only spending when funding is otherwise insufficient. It leaves the underlying race-up policy unchanged outside those targeted trajectories.

The design was intentionally sparse. In earlier matched evaluation, inactive trajectories remained action-identical to race-up while Shop Router losses flipped to wins.

## Local evidence

### Independent confirmation

Across 1,440 accepted official-engine games:

| Policy | Games | Win/tie score |
|---|---:|---:|
| Labor treasury | 480 | **86.875%** |
| Race-up | 480 | 77.708% |
| Parent | 480 | 74.167% |

The labor candidate passed the prospective local gates.

### Champion comparison

A second campaign used 12 fresh seed clusters, ten opponents, and both player positions:

| Policy | Games | Win/tie score |
|---|---:|---:|
| Labor treasury | 240 | **85.0%** |
| Race-up | 240 | 75.0% |
| Timing reference | 240 | 50.83% |

Against race-up, the paired seed gain was **+10 percentage points** in each six-seed block. The candidate changed the Shop Router matchup from 0% to 100% while the other matched opponent scores stayed unchanged.

The retrospective best-of-fixed-policies upper bound was 87.08%, only 2.08 points above the labor policy, so a trivial selector did not offer large additional local headroom.

## Live evidence

The exact confirmed archive was submitted once from SageMaker:

- submission ref: `56598411`
- candidate source SHA-256: `04e4ed65b557139437252348f9159e72b72e8414a480dd087f128d379e045c55`
- archive SHA-256: `3e25e3382a32089b0c51e1c8ade6c221ad35ae3cd685aa12ca9d51d35c96a164`
- returned status: complete
- returned rating: **600.0**

The strongest completed submission in the same authenticated history remained the frozen timing reference:

- ref: `56471163`
- returned rating: **2048.7**

The installed Kaggle CLI did not expose a verified submission-download interface, so the server-side archive could not be re-downloaded and independently re-hashed after upload. Pre-upload source and loader checks passed.

## Interpretation

This is a **validation-distribution failure**.

The local experiment still provided useful causal evidence: preserving labor funding solved the targeted local opponent failure. What failed was the inference from a strong static-league result to expected live ladder strength.

The project therefore treats the local league as a mechanism-testing instrument, not a sufficient promotion instrument.

## Next milestone

Before another policy submission:

1. refresh only missing recent top-agent/public episode evidence;
2. expand the local field with current, behaviorally diverse opponents;
3. construct family-held-out evaluation rather than repeatedly testing near-related controllers;
4. measure correlations between candidate diagnostics and actual live outcomes;
5. require a live-predictive validation gate before resuming structural on-policy policy search.

The next structural policy work should introduce materially new strategic capability—such as simulator-generated on-policy strategic control or league training—but only after validation fidelity improves.

## Public/private boundary

This memo publishes compact metrics, decisions, and hashes. Raw replay archives, private AWS caches, submission tarballs, credentials, and uncleared third-party sources remain outside GitHub.
