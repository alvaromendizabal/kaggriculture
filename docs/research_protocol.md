# Feature research protocol

## Milestones

| Milestone | Evidence required | Current state |
|---|---|---|
| 1. Environment and observation audit | Pinned engine, AWS space, full episodes, legal features, tests, executed 00–01 | First bounded deliverable |
| 2. Feature research (`02`) | Broader trajectory coverage, action candidates, controls, leakage tests, paired ablations | Open |
| 3. Policy learning/planning | Only after major feature avenues have measured diminishing value | Blocked by feature gate |
| 4. Robustness and interpretation | Diverse opponents, scenario stress, untouched holdout, latency, polished conclusions | Pending |
| 5. Competition execution | Offline agent packaging, validation episode, authorized submission, verified receipt | Pending |

Do not assign an overall completion percentage from the existence of files or a successful
simulation. The first milestone establishes reproducibility, not research completion.

## Priority feature families

| Family | Why it could help | Availability and leakage boundary | Planned experiment |
|---|---|---|---|
| Crop lifecycle value | Yield timing, irrigation, fertilizer, decay, and season horizon determine recoverable cash | Current public tile state and public mechanics; future prices must be scenarios | Add lifecycle value to a fixed rule policy; remove each component |
| Labor scheduling | Workers move and act; late hires cannot recover their cost | Current locations, hours, visible tasks, hire count | Compare nearest task, urgency, and cash per worker-turn |
| Multi-unit feasibility | Conflicting plant and inventory actions waste turns | Own seeds/inventory and joint proposed actions | Shared resource constraints versus independent unit decisions |
| Market impact and demand | Premium gluts crash prices; duplicate shops change consumption | Current inventory, public curve, visible shops; no future unlock identity | Spot-price valuation versus per-unit batch valuation and opponent-sale scenarios |
| Inventory and terminal conversion | Unsold inventory has zero terminal reward; shed overflow destroys goods | Own shed, own carried items, visible products, remaining decisions | Add storage pressure and liquidation deadlines |
| Livestock economics | Feed, care, production delay, fertilizer and worker access affect return | Current animal state and own feed stock; source-tested care timing | Lifetime-value features versus nominal product price |
| Land utilization | Purchased land costs cash and requires enough labor to use | Current cash, unlocked land, capacity, season time | Marginal capacity value versus fixed expansion day |
| Public opponent state | Rival crop mix affects future supply and competitive risk | Public farms only; hidden seeds/shed must not be reconstructed from replay truth | With/without public supply-risk indicators across opponent types |
| Causal history | Observed price moves, net supply changes, and past actions reveal trends | Only earlier observations in the same episode; reset state at episode start | Lag/rolling windows and trend versus current snapshot |
| Learned representations | Tile sets and variable-sized worker/task interactions may need compact encodings | Trained on development episodes only; no seed embedding | Compare pooled descriptors, tile/worker embeddings, and action-value features |
| Target-derived encodings | Historical action outcomes may summarize context value | Whole seed groups, out-of-fold encoding; never other turns from the validation episode | Only after a learned action-value dataset is justified |

## Selection and evaluation

1. Generate realistic states with multiple farming strategies; audit action/state coverage before
   removing constants. Reference policies cannot expose animal, land, and multi-worker behavior.
2. Predeclare seed groups and opponents. Both seats are evaluated on each development seed.
   Keep the whole seed group together in any learned preprocessing or target-encoding split.
3. Freeze the base policy, seed suite, compute budget, and feature-group comparison. Change one
   feature family at a time and run both addition and removal controls when appropriate.
4. Compare win + half-tie match score, with paired confidence intervals clustered by seed.
   Report coin margin, catastrophic losses, action no-ops, storage losses, and p99 action latency
   as diagnostics. Do not convert local wins into a made-up Kaggle rating.
5. Broaden opponents, report seed-level variability, check interaction effects, and repeat promising
   effects on validation. Track reuse of validation as a finite selection resource.
6. Use the final holdout once, after freezing policy and features. The first milestone consumes
   neither validation nor holdout seeds.

SHAP/permutation importance becomes relevant when a learned value or policy model exists.
For rule/planning agents, causal feature-group interventions and decisions changed by each
family are the primary explanation. Irrelevant temporal or target encodings are not mandatory.

## Notebook 02 completion evidence

Keep candidate and retained counts, rejection reasons, group ablations, timing, uncertainty,
opponent/seed robustness, information-availability tests, and lineage. An open high-value
family blocks completion unless its omission is justified by measured cost/value evidence.
`require_feature_completion` fails closed until the eight research requirements are explicit.

No initial candidate has yet been screened for model selection, rejected, or promoted. A
descriptive constant/duplicate profile of the reference trajectories is not feature selection.
