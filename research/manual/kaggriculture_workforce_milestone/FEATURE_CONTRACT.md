# Workforce representation: research contract

## Hypothesis and boundaries

A three-hired-hand observation cap excludes demonstrated legal engine states.
Extending one fixed array to twelve merely replaces one arbitrary representational
limit with another. This forward-only module instead returns a fixed aggregate
vector plus variable-length, identity-preserving worker/task tables. No maximum
reachable workforce is claimed. Synthetic cases above the engine fixture range are
software stress tests, not claims about economic feasibility.

The family hypothesis is that worker access, alternative access, available labor
before expiry, and delivery deadlines expose useful decision constraints. This
milestone establishes definability and coverage only. It does not attribute a
competitive improvement to them.

## Data inputs and availability

`extract_workforce(observation, rules)` receives one current legal callback
observation and public crop/animal constants derived from the pinned engine.
It does not receive an episode, reward, seed, future record, hidden evaluator,
opponent shed, opponent carried inventory or future shop unlock.

Both farms' worker locations, crops, livestock and cash are public. Only the
viewer's private inventory is used. Unknown opponent worker inventory is stored as
null with `inventory_observed=0`, not estimated or set to zero. Input mutation is
forbidden. Extra top-level metadata and nested opponent-private fields are ignored.

The registered environment is Python 3.12 with kaggle-environments 1.32.7 and the
engine SHA256 recorded in notebook 05. Board size and horizon are pinned. A missing
or null `step` is derived from day/hour; a contradictory clock fails. Step 719 is a
terminal state, not a decision callback. Inventory list length must equal actual
own worker count; no truncation or invented padding is permitted.

## Representation

**124 state-level candidates** describe time, both farms, relative state and own
inventory. Candidate counts are a schema check, not a quality score.

Worker rows preserve the original action order: farmer index zero, followed by all
hired hands. The aggregate vector is invariant to a reordering of hands; hand rows
are equivariant when their inventory rows are reordered consistently. Worker
identity must not be inferred from a sorted feature table when issuing actions.

Task rows identify visible harvest, water, feed, care and weed-removal opportunities.
Multiple task types on one tile are distinct jobs. A plant is counted as harvestable
only after the registered first-yield age and with positive visible units.

## Feature interpretation

| Family | Definition and rationale | Important limitation |
|---|---|---|
| Workforce and expiry | Worker count times remaining current-day decision slots; positions, shed access and co-location | An action budget is not task-completion capacity; co-location is legal, not a collision penalty |
| Task demand | Per-kind counts, urgent water/feed counts and visible harvest units | Urgency reflects current maintenance state, not estimated lifetime value |
| Worker-to-task access | Manhattan travel plus one task action; first and second nearest alternatives | Feeding prerequisites, simultaneous use, future production and task conflicts are excluded |
| Substitute-worker access | Number of independently eligible workers and first-to-second worker travel gap | A distance gap is not marginal policy value or worker-removal reward loss |
| Delivery deadline | Independent travel-to-task + harvest + travel-to-shed + DROP action lower bound | Excludes overnight auto-drop, shared storage, price changes and competing tasks; not a realized sales forecast |
| Own logistics | Shed room, carried totals, load distribution, wheat availability and hypothetical joint-deposit overflow | These are current stocks and conditional bounds, not optimized feeding or market orders |
| Relative public state | Own-minus-opponent differences in selected public counts/access measures | No private opponent features or inferred inventory are inserted |

A worker counted as able to reach many tasks cannot necessarily finish all of them.
A task accessible to multiple workers must not be double-counted in a joint schedule.
The code never calls these independent opportunity bounds exact assignment utilities.

## Tests and bounded evidence

The shipped unit suite covers fixed schema, unbounded-by-contract worker rows,
both seats, identity-preserving permutations, malformed observations, chronological
consistency, input immutability, hidden-field invariance, deadlines, maturity and
checkpoint safety. Stress cases include 0, 1, 3, 4, 12, 32 and 100 hired hands.

The AWS mechanics stage uses seed 0 only to reproduce the existing two-transition
fixture for each hiring player: four hires, then eight additional hires. It checks
both observer views before and after the transitions and exact hire accounting.
The frozen validator is expected to remain unchanged and reject over-three cases.
This is a source/contract comparison, not a policy comparison.

The replay stage reads only the seven accepted interrupted-pilot artifacts and
rechecks their hashes, envelope checksums, lineage and episode validity. It audits
the same 161 final-day observations, checkpointing each episode independently.
Group identifiers are output metadata only; they are never passed to the extractor.
All these episodes are existing development evidence. No validation/holdout-driven
selection, fitting, reward correlation ranking or feature retention is performed.

## Stop/continue decision

Stop on any changed source, unexpected engine hash, invalid observation, missing
checkpoint, mismatched schema, corrupted resume output, timeout, or failed test.
Keep the diagnostic receipt and completed checkpoints. Do not weaken the contract
to make an unexpected state pass; inspect the underlying reason.

A coverage pass permits the next engineering milestone: a forward-only action
pathway and bounded full-callback acceptance. It does not clear the previous
500 ms full-policy gate. Extractor-only timing must remain labeled separately.

Once a complete candidate pathway passes, preregister one family intervention
against equal staffing and market rules. Require activation and legal-action
divergence before paired games, then assess group-level match outcome, coin margin,
unsold goods, ineffective actions and runtime across distinct opponents/both seats.
Select weights only within training groups. Preserve a fresh evaluation boundary.
No columns are retained for performance based only on this audit.

## Provenance and primary references

Repository baseline: alvaromendizabal/kaggriculture commit
7194116dfc92a8663139611233b5a221dad431a4, especially:
- src/kaggriculture_research/market_features.py: existing three-hand rejection.
- src/kaggriculture_staffing/features.py: canonical clock and fixed slots.
- scripts/audit_workforce_scope.py: mechanics fixture and hire accounting.
- scripts/research_bottlenecks.py: seven-episode/161-observation replay protocol.
- src/kaggriculture_research/artifacts.py: checkpoint format and integrity contract.
- docs/feature_next_milestone.md: equal-rule, grouped action-ablation gate.

Official current mechanics documentation was consulted separately from the pinned
runtime; code execution must satisfy the pinned-source checks, not assume mutable
upstream documentation is identical:
https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md

Zaheer et al., Deep Sets (2017), https://arxiv.org/abs/1703.06114 supplies general
motivation for order-invariant set aggregation. No Deep Sets neural network is
implemented here and the paper establishes no Kaggriculture performance benefit.
