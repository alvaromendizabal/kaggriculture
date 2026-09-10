# Kaggriculture

**Autonomous farming agents with domain-informed state features, economic planning,
paired simulation evaluation, and reproducible AWS experiments.**

This project studies sequential decisions in a competitive farming economy: allocating labor,
growing crops, managing livestock, expanding land, and selling into a shared nonlinear market.
The central question is which observation-safe representations improve decisions and win rates.

**Current stage: livestock, feed and fertilizer feature research.** Five policy
studies contain 320 development games. Study 5 adds 234 resource descriptors and
64 registered comparisons. Its supported bank has 1,500 provisional features;
the project union is 1,542, including 42 earlier cash bounds whose assumptions
do not support this study's wheat purchases. Feature research remains open.

The [latest study](docs/livestock_research.md) found that feeding and care must be
coordinated: selective feeding alone hurt performance. Selective care won all
16 games against two fixed references; fertilizer added 2,539 coins of average
margin but no additional wins. These limited development results do not estimate
Kaggle rank. See the [remaining coverage gaps](docs/feature_coverage.md) and
[restartable workflow](docs/livestock_recovery.md).

## Review the work

1. [00 · Simulator and evaluation contract](notebooks/00_environment.ipynb)
2. [01 · Observation audit and feature hypotheses](notebooks/01_data_audit.ipynb)
3. [02 · Feature-research studies](notebooks/02_feature_research.ipynb)
4. [Latest research: livestock, feed, care and fertilizer](docs/livestock_research.md)
5. [Feature coverage and completion ledger](docs/feature_coverage.md)
6. [Domain mechanisms and modern-method research](docs/domain_research.md)
7. [Market-policy findings: delivery helps coins, holding hurts](docs/market_findings.md)
8. [Research protocol](docs/research_protocol.md)

The [first study](docs/feature_findings.md) motivated storage and stronger-opponent research.
The [second design](docs/relationship_research.md) tests those relationships explicitly.
Earlier collection of fully capped crops helped in this development setting; storage
protection alone eliminated waste but reduced match score. The capital rule never activated,
so its utility remains untested. The [third study](docs/market_research.md) found a positive
delivery coin effect (+2,359.42 averaged over holding settings), but its two wins were
concentrated in one seed. Fixed market holding reduced coins in every seed cluster.
No new competitive agent is promoted; these are component tests, not proof that all
descriptors improve decisions. Study 4's history/cash arms scored 0.625 pooled
versus 0.375 for immediate banking, but the extra wins came entirely from turning
eight mirror-match ties into narrow wins. Match score against the other opponent
did not improve. All 16 cash/history pairs had identical full action sequences.

The notebooks consume saved results. The [machine-readable study](reports/livestock_research.json),
[1,500-feature registry](reports/livestock_registry.csv), and [independent trace audit](reports/livestock_integrity.json)
identify exactly what was measured. All 64 games passed independent replay with
zero mismatches, including 11,584 full vectors and 92,032 private transitions.
Notebook 02 preserves all 23 prior code-cell sources and adds five livestock cells.
It contains **28 genuinely executed code cells and eight rendered figures**.
[The publication run](https://github.com/alvaromendizabal/kaggriculture/actions/runs/34516813547)
passed **212 tests**, executed all three notebooks and verified all five studies.
Its [execution receipt](reports/livestock_notebook_execution.json) is separate from
the archived supply receipt. The exact CI archive was checksum-verified before
import, and both new figures were inspected. Earlier notebook lineage remains checked through the
[declared provenance adapter](scripts/notebook_provenance.py). All prior experiment
and feature sources remain unchanged. Current checks run through
[GitHub Actions](https://github.com/alvaromendizabal/kaggriculture/actions).

The new [history replay](reports/market_history_research.json) checked 34,512 callback
vectors: 178 of 333 descriptors varied, 155 were constant, and 12 groups were exact
nonconstant duplicates. All 241,584 supported stock bounds contained the evaluator-only
truth. History captured possible stored supply in 1,524 product/callback observations
with no visible ready yield, but melon bounds were frequently loose after floor-price
sales. No policy benefit was claimed from that replay alone. The 64-game fourth
study jointly evaluates those history candidates and the cash extension in notebook 02.

## Problem and metric

[Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) is a two-player simulation,
with a nominal 30-day, 720-state season. Final bank balance determines each game's winner;
unsold inventory does not count. Official ranking depends on wins/losses/ties, and the
competition describes a final Bradley–Terry tournament. Coin margin is a supporting diagnostic.

The pinned official engine runs **719 action rounds and records 720 states**, including the
initial state. We use its exact default horizon rather than modifying it to fit the prose guide.
Local performance against an official starter or passive agent does not estimate leaderboard rank.

## Reproduce the earlier milestones

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --frozen
PYTHONPATH=src uv run python scripts/run_foundation.py
PYTHONPATH=src uv run python scripts/run_feature_research.py
PYTHONPATH=src uv run python scripts/audit_feature_behavior.py
PYTHONPATH=src uv run python scripts/run_relationship_research.py
PYTHONPATH=src uv run python scripts/audit_relationship_evidence.py
uv run python scripts/build_research_notebook.py
PYTHONPATH=src uv run python scripts/run_market_research.py
PYTHONPATH=src uv run python scripts/audit_market_evidence.py
PYTHONPATH=src uv run python scripts/analyze_market_holds.py
PYTHONPATH=src uv run python scripts/analyze_market_history.py
PYTHONPATH=src uv run python scripts/verify_market_history.py
PYTHONPATH=src uv run python scripts/build_market_notebook.py
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
rerunning 192 games, including preserved notebook-source lineage when a later section is added.
Study 3's independent
audit recomputes 8,688 × 933 feature values and checks all 34,512 candidate callbacks.
A fresh local notebook
execution changes execution metadata and must not replace the recorded publication artifact
without updating its execution evidence.

Study 4 uses the [source-locked recovery runbook](docs/supply_recovery.md), including
authorized S3 manifests, at most eight new games per batch, independent cached
audits, remote-byte verification and genuine notebook-execution receipts.
Study 5 has its own [livestock recovery runbook](docs/livestock_recovery.md), with
unchanged registered source, an exercised S3 restore, one-game operational slices,
explicit reporting adapters and a verified archive of all 64 independent audits.

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
The third workflow completed in 940.77 seconds, including 106 passing tests and notebook
execution. All 76 expected output artifacts were downloaded and SHA-verified. Compute was
confirmed stopped; persistent storage remains and can still incur charges. The full Git
history through PR3 is also [backed up and verified](reports/history_backup.json).
Study 4 used local CPU simulation, with no new SageMaker compute. Its 64 episode
execution times sum to 748.000 seconds; this excludes transfers, screening,
auditing and CI. The app was again confirmed stopped on September 10, 2026.
Study 5 also used local CPU with no new SageMaker compute. Its 64 registered game
times sum to 722.27 seconds. The [persistence receipt](reports/livestock_cloud_verification.json)
checks all 82 required S3 objects by downloaded bytes, checksum, version and encryption.

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
Study 3 adds 315 descriptors and tests delivery/timing on six fresh seeds. Its 933-column
bank has 361 constants, 56 duplicate groups and 670 highly correlated pairs; all remain
provisional. The holding analysis found same-turn rival sales in 174/343 deferred-product
events, motivating legal-history supply uncertainty rather than assuming visible ripe
crops represent all rival stock. Joint routes, livestock, fertilizer, capital-stress
regimes, adaptive crop mix and diverse opponents remain open in the [coverage ledger](docs/feature_coverage.md).
Every major family needs information-availability checks, controlled additions and removals,
seed-paired uncertainty, and performance against diverse opponents.

Study 4 jointly screened all 1,308 candidates: 754 varying, 554 constant, 74 exact
duplicate groups and 1,866 highly correlated pairs. None is selected or rejected
for a final model. Cash constraints reduced accumulated excess melon-stock bounds
by 13.19%, but did not reduce empty-stock false alarms or change decisions beyond
history. All 78 livestock state/feed-care descriptors remained constant: a
high-priority coverage gap, not evidence that livestock is unimportant.

Study 5 activates 70 of those 78 animal descriptors. Its 1,500-column supported
bank has 1,205 varying features, 295 constants, 157 duplicate groups and 1,775
high-correlation pairs. Of 234 new resource descriptors, 192 vary. All remain
provisional. The study exposes a real feeding/care interaction, fertilizer margin
gains and remaining final-day feed waste. Joint routing, alternative herd/crop
mixes, capital stress, land and stronger unrelated opponents remain open.

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
