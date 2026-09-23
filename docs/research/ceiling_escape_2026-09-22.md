# Ceiling-escape review — 2026-09-22

## Current competitive state

The latest verified full leaderboard export at `2026-09-23T00:55:21Z` contained 9,875 ranked rows.

- Strongest current submission: **2047.9**, rank **1621**.
- Second current submission: **2044.9**.
- Observed rank one: **3152.6**.
- Remaining gap: **1104.7**.
- Stretch target **3700** is **547.4 above** the observed leader and is treated as aspirational, not as the current benchmark.

## Killed directions

| Direction | Evaluation | Result | Decision |
|---|---|---:|---|
| Terminal crew/route/market planner | 32 direct games | 5-27 | stop |
| Adjacent-sale action learning | recent train/validation | holdout gates failed | stop |
| Frozen service-route release | 64 direct games | score 0.65625; prospective gates failed | stop |
| Exact Boatlee V16 | 64 direct games | 0-32 vs each live source | stop |

## Data status

AWS retains compact daily replay shards through **2026-09-20**. The last verified official episodes index reaches **2026-09-21**. The next run refreshes only missing/changed recent deltas and current public episodes; historical shards and caches are reused.

## Ceiling diagnosis

The project has both a validation-distribution mismatch and a whole-policy capability gap. Strong-looking local changes have repeatedly failed to produce a stronger live rating.

## Next advancement

Move from micro-interventions to recent, compatible full-season policy families. Freeze candidate families before confirmation, compare against both current submission sources, then require a broader current-meta veto league before any submission review.

## Public/private boundary

GitHub contains implementation, compact evidence, notebooks, decisions, and provenance—not raw replay corpora, credentials, environments, large checkpoints, or uncleared third-party controller source.
