# Kaggriculture

**Autonomous farming agents with domain-informed state features, economic planning,
paired simulation evaluation, and reproducible AWS experiments.**

This project studies sequential decisions in a competitive farming economy: allocating labor,
growing crops, managing livestock, expanding land, and selling into a shared nonlinear market.
The central question is which observation-safe representations improve decisions and win rates.

**Current stage: resource-relationship feature research.** Two bounded studies now contain
144 development games: 80 crop-feature comparisons and a 64-game capacity/capital/maturity
factorial experiment against the frozen previous scheduler. The state/history bank contains
618 provisional descriptors. Feature research remains open; no Kaggle score is claimed.

## Review the work

1. [00 · Simulator and evaluation contract](notebooks/00_environment.ipynb)
2. [01 · Observation audit and feature hypotheses](notebooks/01_data_audit.ipynb)
3. [02 · Crop features and resource-relationship experiments](notebooks/02_feature_research.ipynb)
4. [Latest findings: maturity, storage and capital](docs/relationship_findings.md)
5. [Feature coverage and completion ledger](docs/feature_coverage.md)
6. [Research protocol](docs/research_protocol.md)

The [first study](docs/feature_findings.md) motivated storage and stronger-opponent research.
The [second design](docs/relationship_research.md) tests those relationships explicitly.
Earlier collection of fully capped crops helped in this development setting; storage
protection alone eliminated waste but reduced match score. The capital rule never activated,
so its utility remains untested. These are component effects, not proof that 618 features help.

The notebooks execute from saved, verified results. The [latest machine-readable study](reports/relationship_research.json),
[618-feature registry](reports/relationship_registry.csv), and [independent trace audit](reports/relationship_integrity.json)
identify exactly what was measured. Three notebooks contain 25 executed code cells and seven
static figure fallbacks. Both studies' code, outcomes, contrasts and conservation are verified.

## Problem and metric

[Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) is a two-player simulation,
with a nominal 30-day, 720-state season. Final bank balance determines each game's winner;
unsold inventory does not count. Official ranking depends on wins/losses/ties, and the
competition describes a final Bradley–Terry tournament. Coin margin is a supporting diagnostic.

The pinned official engine runs **719 action rounds and records 720 states**, including the
initial state. We use its exact default horizon rather than modifying it to fit the prose guide.
Local performance against an official starter or passive agent does not estimate leaderboard rank.

## Reproduce the current milestones

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --frozen
PYTHONPATH=src uv run python scripts/run_foundation.py
PYTHONPATH=src uv run python scripts/run_feature_research.py
PYTHONPATH=src uv run python scripts/audit_feature_behavior.py
PYTHONPATH=src uv run python scripts/run_relationship_research.py
PYTHONPATH=src uv run python scripts/audit_relationship_evidence.py
uv run python scripts/build_research_notebook.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
PYTHONPATH=src uv run python scripts/execute_notebooks.py
```

These commands run full development seasons, reuse matching verified episode checkpoints,
recompute the observation audit, and execute the canonical notebooks. Episode configuration,
engine files, runner code, feature code, and semantic episode hashes are recorded. Corrupted
checkpoints raise an error; different lineage gets a separate experiment key. Full study 2
uses 64 games; its private trace audit recomputes all 11,584 sampled feature vectors. Raw
trajectories are intentionally absent from GitHub; rerun the studies or restore matching
authorized checkpoints. `scripts/verify_research_report.py` checks published evidence without
rerunning 144 games, including the exact AWS-executed notebook hash. A fresh local notebook
execution changes execution metadata and must not replace the recorded publication artifact
without updating its execution evidence.

## AWS workspace

| Setting | Configuration |
|---|---|
| Region | `us-west-2` |
| Space | `kaggriculture-dev` |
| Compute | `ml.m5.xlarge` · 4 vCPU · 16 GiB |
| Persistent volume | 30 GiB |
| Idle shutdown | 60 minutes |
| Storage | Private, encrypted, versioned S3 bucket in `configs/aws.json` |

The observed on-demand compute price was $0.23/hour on September 9, 2026, before storage and
request charges. Setup work has a 20-minute process timeout. Future experiment budgets must be
scoped before launch; a timeout or idle shutdown is not an account-wide spending cap.
The second run completed in 1,055.75 seconds, including 75 tests and notebook execution.
Compute was stopped after completion; persistent storage remains and can still incur charges.

## Feature research is the completion gate

The initial feature vector describes crop state, livestock state, labor and land, inventory and
storage, nonlinear sale curves, visible town demand, remaining time, and the public opponent.
It contains **candidates**, not empirically selected features. Constant or duplicate columns in
simple reference rollouts indicate missing state coverage; they are not automatically discarded.

The first action-feature experiment evaluates 13 templates for crop lifecycle value, watering
urgency, labor allocation and terminal banking in one fixed scheduler. All remain provisional.
See [paired results](reports/feature_ablations.csv) and the [research summary](reports/feature_research.json).
Study 2 adds 374 state/history descriptors and a complete three-factor experiment. All 618
descriptors were screened for availability, finite values, variation and dependence; none
were promoted or rejected for a final model. There are 246 constant descriptors in these
crop-only trajectories, 23 nonconstant exact-duplicate groups and 202 highly correlated pairs.
These are coverage/redundancy flags, not evidence that the corresponding domain is useless.
Joint market/delivery timing, livestock, fertilizer, capital-stress regimes, spatial assignment
and diverse adaptive opponents remain open in the [coverage ledger](docs/feature_coverage.md).
Every major family needs information-availability checks, controlled additions and removals,
seed-paired uncertainty, and performance against diverse opponents.

Read [the source audit](docs/source_audit.md) for mechanics that affect the design. The full
standards are in [AGENTS.md](AGENTS.md). Final optimization remains blocked by the research gate.

## Sources

- [Competition overview and evaluation](https://www.kaggle.com/competitions/kaggriculture/overview)
- [Competition rules](https://www.kaggle.com/competitions/kaggriculture/rules)
- [Official simulator source](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture)
- [Pinned package release](https://pypi.org/project/kaggle-environments/1.32.7/)

Only public simulator dependencies are installed. Competition data-kit files are not redistributed.
Public strategic-code sharing must also be associated with the competition as described in rule 3.6.b.
The [public companion discussion](https://www.kaggle.com/competitions/kaggriculture/discussion/740550)
was posted with the repository owner's authorization.
