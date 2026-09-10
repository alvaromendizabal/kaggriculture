# Crop action-feature experiment

This is the first bounded portion of notebook 02. The feature-completion gate stays closed.
The experiment specification and weights are fixed before comparative results are inspected.

## Question and estimand

Do four bundles of observable action features improve one fixed deterministic crop scheduler
on development seeds? Compare `full` with `no_crop_value`, `no_water_urgency`, `no_labor`, and
`no_terminal`. All variants share candidate generation, action legality, tile reservations,
movement tie-breaking and immediate shed sales. A disabled family removes its scoring or
decision contribution. Labor includes both distance weighting and the workload-based hiring
decision. These are **policy-component ablations**, conditional on this scheduler and weights;
they do not establish the intrinsic value of a feature under every possible trained policy.

Thirteen action-feature templates span crop value (3), water urgency (3), labor (4), and
terminal banking (3). They are separate from the foundation's 244 fixed state descriptors.
They are instantiated per crop, tile or candidate task. No coefficients are fitted.

## Fixed assumptions and controls

- Crop value uses current conditional sale revenue, seed cost, daily watering, no fertilizer,
  one harvest, and a two-action delivery allowance. It is not a future-price prediction.
  Irrigation on the harvest day is included before computing single-crop yield.
- Water urgency uses next-refresh mortality, the actual age-dependent watering bonus and time
  to refresh. New plants start with one unwatered day and need water on planting day.
- Labor weights task value by `1 / (1 + Manhattan distance)` and compares approximate work
  remaining with available worker actions. Hire at most three temporary hands per day.
- Terminal features constrain crop maturity to the remaining official decisions, check actual
  delivery distance before late harvest, and prioritize carried goods on the final partial day.
- No land expansion, animals, fertilizer, speculative market trades, seed inference or future
  town information. Future work must examine these families before closing the research gate.
- Weights and thresholds are explicit in `crop_policy.py`; this run does not tune them.
- Opponents: the official starter and the same scheduler restricted to carrots with no hired
  hands. The latter supplies repeatable harvesting and market activity. This is limited
  opponent diversity; it does not represent strong leaderboard policies.

## Evaluation contract

Run 5 variants × 2 opponents × 4 development seeds × 2 seats = 80 full seasons. Both seats
and both opponents remain in one seed cluster. Reuse the foundation development seeds;
validation and holdout remain untouched. Primary local outcome is win + 0.5 × tie. Report
paired full-minus-ablation differences, seed-level differences, and a descriptive 95%
percentile bootstrap interval over the four seed clusters. Four seeds cannot support a
strong significance claim; intervals are exploratory, with no multiplicity-adjusted claims.

Report banked coins, coin margin, unsold product units, plant counts, silent ineffective
farm actions, and policy-call latency as diagnostics. Revenue and a local match score do not
equal Kaggle's live or final Bradley–Terry rating. A local callable latency is not a submission
sandbox benchmark. No submission occurs in this milestone.

The same environmental seed couples comparisons but does not guarantee identical future
shops: policy-dependent weed placement can consume the shared random stream differently.
This is an environment response, not a reason to expose seed information to policies.

## Lineage and recovery

Each full episode stores the exact legal policy observations, actions and feature diagnostics,
with engine, policy, evaluator, environment, economic helper and protocol hashes. Final
reward and seed are evaluator metadata only. Timings are excluded from semantic hashes.
Write each completed episode atomically before continuing, with UTC stages and heartbeats.
Run at most 80 games and 900 seconds locally within the 1200-second cloud setup deadline.
Reuse only checksum- and lineage-valid checkpoints. Raw checkpoints remain in private S3.

Tests cover conditional yields against the official interpreter, terminal boundaries,
observation-only invariance, action feasibility, and reproducibility. No final policy is
selected by this experiment; all four families remain provisional pending broader research.
