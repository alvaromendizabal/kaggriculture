# Staffing-controlled terminal routing — preregistered pilot

## Research question

Study 6 improved the pooled local match score by 0.25 and removed residual carried/shed products, but its coordinated `joint` arm stopped rehiring after nightly worker expiry while comparison arms could rehire. That result therefore combines routing and staffing. This pilot isolates the routing mechanism.

**Hypothesis:** with the same fertilizer/feed-gated base policy, the same day-29 hiring rule, and the same market-order rule, bounded conflict-aware multiworker collection/delivery will bank at least as much terminal value as the sequential scheduler and will activate two or more workers on observed trajectories.

This is a mechanistic development pilot, not a population-performance or Kaggle-leaderboard estimate.

## Domain evidence motivating the representation

The implementation is guided by the pinned official engine plus current public competition evidence and operations-research analogues:

- Kaggriculture community analysis repeatedly identifies action efficiency, worker zoning, movement cost, end-game banking, and avoiding late investments as key mechanisms. Public notebook feedback specifically recommends `expected_profit - movement_cost - urgency_penalty`, efficient scheduling of four workers, and explicit terminal harvest/deposit/liquidation logic.
- Current high-ranking public discussion reports that competitive agents are still largely heuristic/hybrid. A current #1 participant reported limited end-to-end RL success and more promise in opponent modeling; another detailed system reports that exact legality/routing/task-dependency execution plus high-level option selection is materially more reliable than primitive-action learning.
- Public discussion of land expansion notes that extra quadrants can have poor ROI because they increase walking distance and require increasingly expensive labor. That motivates marginal-worker value and route-work features rather than treating worker count as uniformly beneficial.
- Integrated Task Assignment and Path Planning for Capacitated Multi-Agent Pickup and Delivery (Chen et al., 2021, arXiv:2110.14891) motivates assignment using realized delivery cost rather than a distance-only lower bound.
- Multi-Goal Multi-Agent Pickup and Delivery (Xu et al., 2022, arXiv:2208.01223) motivates assigning sequences of tasks to workers rather than independent one-task greediness.

Public competition discussions used as hypotheses, not ground truth:

- https://www.kaggle.com/code/nagatakengo/kaggriculture/comments
- https://www.kaggle.com/competitions/kaggriculture/discussion/732623
- https://www.kaggle.com/competitions/kaggriculture/discussion/736369
- https://www.kaggle.com/competitions/kaggriculture/discussion/737937
- https://www.kaggle.com/competitions/kaggriculture/discussion/738079

## Arms and causal control

Both arms instantiate exactly `FeedPolicy("fertilizer")` and use its market orders. On day 29:

- `sequential`: use the base policy's farmer and hand actions.
- `coordinated`: replace only the farm-unit actions with the bounded Study-6 route assignment; retain the base market orders verbatim.

Consequences such as different shed contents may produce different SELL quantities later, but the decision rule is shared. HIRE orders, worker expiry mechanics, and the policy implementation generating market orders are identical by construction.

Before day 29, both arms must be action-identical. The experiment must reject a pair if preterminal semantic hashes differ.

## New feature families

`src/kaggriculture_staffing/features.py` adds 53 fixed-schema, observation-safe candidates. They are provisional until screened and ablated.

1. **staffing_coordination** — active worker count, hiring window, remaining horizon, shed room, route resources, feasible/retained routes, exact assignment leaves/value/work/units, an optimistic independent-route upper bound, resource conflicts, routed-worker count, and assigned-work/load extrema.
2. **staffing_worker_opportunity** — per worker (four fixed slots): presence, menu size, best/second-best route utility, best route value, work length and units.
3. **staffing_marginal_worker_value** — exact joint utility available to the first 1–4 active workers under the same bounded route menu.

Availability contract: only current/past legal observations. No seed, evaluator reward, hidden rival inventory, future shop sequence, future market orders, or simulator-private transition state enters the feature extractor.

The route menu remains bounded: at most two collections plus deposit, with Study-6 resource and shed-capacity constraints. Exact assignment is only over that retained menu and is active on day 29. This keeps the feature family interpretable and within the competition's tight per-step runtime budget.

## Frozen development design

`configs/staffing_research.json` registers:

- development seeds: 1601, 1602;
- seats: 0 and 1;
- opponent: `livestock_fertilizer` for the first mechanism pilot;
- arms: `sequential`, `coordinated`;
- 8 games total;
- one new game per operational batch;
- 45-second batch cap; 15-minute total simulation cap;
- no validation or holdout access;
- no automatic scale-up.

Seeds 1601–1602 are disjoint from foundation development/validation/holdout and Studies 3–6 seed registries. The test suite checks this against the committed configs instead of relying on the narrative.

The mirror-like fertilizer opponent is intentionally retained for this *mechanism* pilot because earlier terminal work converted ties against it into wins, making terminal routing discriminative. It does not satisfy the later opponent-diversity requirement; a separate opponent milestone must follow before broader performance claims.

## Acceptance tests before game 1

The pilot is not allowed to start until all of the following pass:

- code style and complete repository tests;
- fixed 53-feature schema, finite values and mutation safety;
- reward/seed/future-metadata invariance;
- exact arm equality before day 29;
- shared day-29 market orders and HIRE rule;
- policy serialization roundtrip;
- registered seed separation and hard 8-game cap;
- a real-policy smoke trajectory that activates at least two workers before treating multiworker benefit as measurable;
- policy latency below 500 ms on the representative terminal smoke.

## Pilot outputs and evidence

For every game, persist before beginning another game:

- exact source/config lineage;
- full episode checkpoint;
- per-callback policy diagnostics;
- active-worker and routed-worker counts;
- staffing feature vectors sampled on the final day;
- terminal residual product units;
- match result, coins and coin margin;
- policy latency;
- semantic hash and transition audit;
- upload receipt with byte hash/version/encryption when running in AWS.

Primary metric is local win/tie/loss match score. Coins, margin, residual products and routing diagnostics explain mechanism; they do not replace the official outcome.

## Stop / continue gate

Stop immediately and retain the negative result if any of these occur:

- staffing/hiring logic differs across arms for the same reachable state;
- preterminal behavior differs;
- no callback has at least two active workers where coordinated routing can act;
- the coordinated route mechanism never activates;
- illegal/no-op conflicts appear;
- checkpoint/upload/lineage verification fails;
- latency exceeds 500 ms;
- a source/schema change occurs after preregistration.

After all 8 games, inspect paired seed/seat effects and activation diagnostics. Do **not** scale automatically. A wider study requires a new preregistration and a distinct opponent-population decision.

## What this pilot does not establish

It does not prove general win probability, leaderboard strength, optimal worker count, optimal land expansion, a learned value function, or that all 53 candidates should survive. Those questions remain feature-research work.
