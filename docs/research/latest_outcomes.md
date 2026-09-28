# Current outcome ledger

**Latest evidence snapshot: 2026-09-28T05:21:12Z**

| Milestone | Evaluation | Result | Decision |
|---|---|---|---|
| Active scoring pair | authenticated latest-two accepted submissions | race-up **1760.7** (`56511669`), labor **1712.2** (`56598411`) | preserved until a new candidate clears release gates |
| Historical timing reference | authenticated completed submission | **2048.7** | historical benchmark, not an active slot |
| Public-state cash forecast | chronological final-date test | MAE **1268.98** vs **1714.86** persistence; **26.0% lower** | auxiliary model confirmed |
| Forecast transfer | 64 later active-submission games | MAE **1527.54** vs **2063.93** persistence; **26.0% lower** | transferred; not a submission metric |
| Learned supply execution | screen then independent confirmation | screen **91.67% vs 79.17%** labor; confirmation **74.31% vs 71.18%** | rejected; broad gates not met |
| Whole-order queue planning | official-engine mechanics gate + screen | **60.71% vs 80.36%** labor | rejected and closed |
| Contextual production-program selector | 1,536 games + 20 fits | confirmation **81.67% vs 80.0%** labor | rejected; gain too small / narrow |
| Whole-controller public reference | 1,192-game study | confirmation **94.44% vs 85.42%** labor; +9.03pp, CI includes zero | promising; fresh replication required |
| Learned add-on to public reference | screen | **91.67% vs 100%** unchanged reference | rejected; external reference strength not credited to adapter |
| Replication release attempt | storage preflight | stopped before tests/games/upload | execution failure; storage-safe recovery prepared |

## Latest decision

Do **not** return to tuning the rejected supply, queue, or contextual-program experiments. The strongest unresolved evidence is the attributed whole-controller reference, and its previous confirmation remains rejected under the registered uncertainty gate.

The next experiment is one independent fresh-seed replication of that exact reference. Previous confirmation outcomes are not pooled into the new verdict. A pass permits one gated terminal submission; a failure closes the reference without automatic sample expansion.

## Public provenance / boundary

- Published post-checkpoint official-engine games: **4,352** across completed studies.
- Published post-checkpoint model fits: **28** small experimental fits.
- AWS/SageMaker remains canonical; GitHub contains aggregate evidence, notebooks, and methodology.
- Raw replays, acquired public-controller source, exact competitive thresholds/weights, private checkpoints, per-game action traces, and submission archives remain private.

The machine-readable aggregate summary is in `reports/recent_meta_frontier.json`.
