# Kaggriculture — decision-focused feature research

**Alvaro Mendizabal · Simulation agents · Controlled ablations · Reproducible evidence**

A research project on turning farm observations into profitable actions in Kaggle's
Kaggriculture environment. The work connects crop and livestock mechanics, worker
allocation, inventory flow, and shared-market behavior to explicit policy hypotheses.
The implementation, tests, protocols, and research notebooks are public in this repository.

## Start with the evidence

| Entry point | What it contains |
|---|---|
| [Research overview notebook](notebooks/00_research_overview.ipynb) | Six inline Plotly views from recorded results; no simulator execution |
| [Interactive overview](docs/research/index.html) | Exported HTML; download and open locally, or use the repository's configured GitHub Pages URL |
| [Research index](research/README.md) | Source snapshots, feature dictionaries, tests, and notebook navigation |
| [Evidence boundaries](docs/research/evidence.md) | What is measured, missing, and not yet validated |
| [Execution guide](docs/research/reproduction.md) | How the AWS workspace and versioned research sources fit together |

## Latest reviewed milestone

The first completed outcome pairs are now available. Collection-completion valuation lost **5,136 own coins** and is not promoted. Maintenance-deadline valuation gained **218 own coins**, improved margin by **233**, and changed **one local loss to a win**. Both comparisons used one shared development control; this is not independent validation.

See the [current outcome ledger](docs/research/latest_outcomes.md) for exact receipts, negative findings, and limits. The six-chart overview retains the earlier archived-screen evidence. **No official Kaggle submission score is recorded.**

## Research approach

The project tests representations rather than counting columns: information-availability
contracts; simulator-mechanics checks; identical-condition controls; feature-family
interventions; complete-trajectory outcomes; runtime checks; and reproducible artifacts.
Negative and inactive hypotheses remain in the record. An activation screen is not a
performance result, and a single favorable development pair is not independent validation.

Recent investigations cover crop lifecycle and renewal, maintenance interactions,
arrival stock, production headroom, collection-to-sale time, and survival-critical
service slack. Earlier code and findings remain available in the original repository
structure and the indexed manual-study snapshots.

## Implementation map

- `src/`, `configs/`, `scripts/`, `tests/`: the established research baseline.
- `research/manual/`: additive snapshots of work actually found in the AWS home-directory packages.
- `notebooks/`: original notebooks plus the entry-point reporting notebook.
- `docs/research/`: evidence summary, aggregate data, and exported interactive report.

The publication manifest records included files, missing package folders, and notebook
execution-count observations. It is not a complete disk backup and does not certify
all historical notebooks as freshly rerun.

## Reproducibility and limitations

Research sources are public. Raw competition assets, generated episode archives,
credentials, environments, and large checkpoints are excluded from Git; the guides
identify the artifacts needed for reproduction. Their exclusion is data handling,
not concealment of the agent implementation.

The existing complete callback still has a restricted workforce contract; broad
submission-readiness, stronger opponents, fresh grouped evaluation, and a verified
competition score remain open. Feature engineering is not declared complete.

Existing repository licensing and third-party notices are retained. See the root
license and the notices adjacent to attributed components.
