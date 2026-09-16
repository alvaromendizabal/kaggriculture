# Adaptive Synthesis v1

Adaptive Synthesis v1 tests a deliberately sparse strategy overlay for the Kaggriculture
agent-simulation environment. It is designed around a specific empirical observation:
the strongest route families in the public benchmark set are highly structured, while the
most consequential differences are concentrated in market timing and terminal conversion.

## What is authored here

The maintained implementation in `src/kaggriculture_adaptive/policy.py` adds:

- exact nonlinear market-price and price-impact calculations;
- ordering of existing `SELL` slots without moving non-sale orders;
- sparse public-state near-mirror detection;
- one-turn premium-sale preemption only after clone confidence is established;
- next-turn repayment so preemption changes timing rather than silently increasing planned supply;
- an observation-driven terminal harvest/drop/liquidation controller.

The overlay only uses current or past legal observations. It does not consume the environment seed,
future shops, final rewards, hidden engine state, or opponent-private state.

## External benchmark route

Development cross-play composed the overlay with the public `Soil Remembers Rain v16` route as an
**external benchmark backbone**. The route itself is not included in the maintained authored module.
Exact external artifact hashes and research lineage are documented in
`docs/public_source_lineage.md`.

This separation matters: the contribution being tested here is the adaptive overlay, not a claim that
the public route was originally authored by this project.

## Development protocol

Stage A screened three overlay configurations on fresh development seed `3107`, both seats, against
Soil and Breaking the Tie.

| Variant | Games | Wins | Mean margin |
| --- | ---: | ---: | ---: |
| `clone_terminal` | 4 | 4 | +3,070.0 |
| `clone_front_run` | 4 | 4 | +3,040.0 |
| `impact_slots` | 4 | 4 | +2,267.5 |

`clone_terminal` advanced.

Stage B used fresh development seeds `3108–3110`, both seats, versus four external teachers.

| Opponent | Games | Wins | Mean margin | Minimum margin |
| --- | ---: | ---: | ---: | ---: |
| Breaking the Tie v12 | 6 | 6 | +4,728.2 | +3,761 |
| Kaito Midgame Meta Reset v4 | 6 | 6 | +17,148.0 | +13,623 |
| Rank Your Agent v11 | 6 | 6 | +20,005.5 | +11,519 |
| Soil Remembers Rain v16 | 6 | 6 | +994.7 | +732 |

Overall Stage B: **24/24 wins**, mean margin **+10,719.1**, no ties.

These are local development results, not a Kaggle leaderboard rating and not evidence of a guaranteed
live-ladder score. Canonical validation seeds `2101–2108` and holdout seeds `9101–9108` were not used.

## Interpretation

The smallest margins occur against the Soil backbone itself, which is expected: the overlay changes
only sparse high-value decisions. The larger margins versus the other teacher lineages show that the
underlying route plus adaptive market/terminal logic is robust across this bounded teacher league.

The next gate is a packaging-equivalence smoke on a fresh development seed before one controlled
temperature submission. No additional policy tuning should use validation/holdout seeds.
