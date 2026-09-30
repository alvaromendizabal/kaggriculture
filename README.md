# Kaggriculture — competitive agent research

**Alvaro Mendizabal · Multi-agent simulation · Validation engineering · AWS/SageMaker · Reproducible experimentation**

A notebook-first research project for Kaggle's Kaggriculture environment. The repository
focuses on rigorous agent evaluation: official-engine simulation, live-ladder replay
reconstruction, controlled policy ablations, chronological holdouts, public-frontier
reproduction, restartable experiment infrastructure, and evidence-driven promotion gates.

## Competitive checkpoint

Latest authenticated evidence published from the September 29–30 sprint:

| Measurement | Verified value |
|---|---:|
| Active keeper | **1691.0** — submission `56656845` |
| Other active slot | **1516.2** — submission `56598411` |
| Highest returned leaderboard row | **3084.1** |
| Gap to that returned row | **1393.1** |
| Stretch target | **3400** |
| Gap to stretch target | **1709.0** |

The leaderboard export was paginated, so this repository describes 3084.1 as the
**highest returned row**, not as a guaranteed exhaustive rank-one snapshot.

A historically stronger returned submission reached **2048.7**, but it is outside the
current latest-two scoring pair.

## The main result: fix the validator before optimizing the agent

The most important final-sprint result was not a new policy. It was a validation
correction.

The older fixed opponent panel had become saturated: the live keeper could look close to
perfect locally while remaining much weaker on the ladder. The replacement evaluator
reconstructs recent keeper ladder episodes and requires **exact terminal-reward parity**
before counterfactual policies are interpreted.

Across 48 recent public keeper episodes, the replay-aligned evaluator measured:

- **18 wins**
- **10 ties**
- **20 losses**
- **47.9% win/tie score**

The older 24-episode development slice was **9 wins / 4 ties / 11 losses = 45.8%**.

That validator is now the primary reference for keeper-centered counterfactual research.

## Final-sprint research arc

The September 29–30 sprint deliberately preserved negative experiments:

| Milestone | Work | Decision |
|---|---:|---|
| Late-layer source ablation | 234 games | **Rejected** — historical prefixes did not improve the keeper |
| On-policy economic population | 448 games, 2 updates | **Rejected** — selected policy learned no useful intervention |
| Coherent public/recent routes | 428 games | **Rejected** — whole-route transfer failed sharply |
| Newer public adaptive agents | 300 games | **Rejected** — adaptive public policies did not transfer |
| Real-ladder alignment | 48 recent keeper episodes | **Validator corrected**; no fixed policy safely replaced keeper |
| Boundary counterfactual search | 1,084 calibration/branch games | rescue opportunities existed in hindsight |
| Rolling boundary-rule CV | reused all 1,084 results | **Rejected** — rescue rules did not generalize forward |
| Native harvest/service recovery | 94 attempted development games | **Execution failure**, not a scientific rejection; repaired runner prepared |

The key engineering conclusion is as important as the modeling result: **a high local win
rate is not evidence of competitive progress unless the validation distribution tracks the
games driving live rating**.

## Start with the evidence

| Entry point | What it contains |
|---|---|
| [Final-sprint notebook](notebooks/56_final_sprint_ladder_alignment.ipynb) | executed notebook with the ladder-alignment correction and policy-rescue diagnostics |
| [Final-sprint research memo](docs/research/final_sprint_2026-09-30.md) | technical narrative and conclusions |
| [Registered protocol ledger](docs/research/final_sprint_protocols.md) | hypotheses, splits, gates, kill criteria, and decisions |
| [Reproduction guide](docs/research/final_sprint_reproduction.md) | clone-time and full competition reproduction boundaries |
| [Machine-readable evidence](reports/final_sprint_2026-09-30.json) | aggregate outcomes from verified return bundles |
| [Reproduction manifest](reports/final_sprint_reproduction_manifest.json) | engine, hardware, handoff, and return-bundle identities |
| [Outcome ledger](docs/research/latest_outcomes.md) | project chronology |
| [Leading-solution matrix](docs/research/leading_solution_reproduction_matrix.md) | reproduced, adapted, rejected, and open mechanisms |

## Research standard

Experiments are self-gating:

**artifact integrity → environment/source checks → parity → development → chronological
holdout → reactive safety → deterministic packaging → terminal-originated release**

The project keeps separate:

- auxiliary predictive accuracy;
- local coin margin;
- official-engine win/tie rate;
- replay-counterfactual improvement;
- chronological generalization;
- reactive-opponent safety;
- live Kaggle rating.

A candidate is not promoted because it wins a familiar panel, improves mean bank, or
matches a historical public notebook score.

## Engineering approach

AWS/SageMaker is the canonical workspace. The recent research infrastructure uses:

- `ml.m7i.12xlarge` CPU simulation;
- up to 24 concurrent official-engine games under resource gates;
- isolated agent processes and callback-parity checks;
- source, engine, worker, and checkpoint SHA-256 binding;
- atomic restartable game checkpoints;
- chronological real-ladder development/holdout splits;
- bounded runtime, memory, disk, and transfer budgets;
- executed notebooks with persisted Plotly outputs;
- deterministic return bundles and candidate archives;
- terminal-originated Kaggle release with durable upload intent and duplicate protection.

## Clone-time reproduction

With Python 3.12 and `uv` installed:

1. Clone this repository.
2. Run `uv sync --frozen`.
3. Run `uv run pytest -q tests/test_final_sprint.py`.
4. Run `uv run python scripts/verify_final_sprint.py`.
5. Open `notebooks/56_final_sprint_ladder_alignment.ipynb` for the executed research story.

The normal CI suite performs broader repository validation.

A full competitive rerun additionally requires authorized Kaggle competition access and
immutable retrieval of registered public sources/replays. See
[the reproduction guide](docs/research/final_sprint_reproduction.md).

## Current research question

**Does project-authored harvest/service recovery improve the actual keeper under the
replay-aligned chronological validator without sacrificing its existing wins?**

The first attempt failed after game completion because an inherited diagnostics transport
queried an exited process. That is recorded as an execution failure—not evidence against
the mechanism. A repaired, hash-bound recovery artifact passed its packaged regression
suite and is the next private AWS experiment.

## Public reproducibility and competitive boundary

This public repository is designed so an employer or researcher can clone it, run the
published validation utilities/tests, inspect executed notebooks, and reproduce the
published aggregate conclusions.

It intentionally does **not** commit:

- credentials, tokens, or account configuration;
- raw Kaggle replay corpora or private S3 mirrors;
- private AWS checkpoints and per-game action traces;
- Kaggle submission archives or handoff `.pyz` binaries;
- third-party controller source;
- exact private competitive implementation details that are not required to reproduce the
  published research conclusions.

External work remains attributed to its original authors and immutable upstream identities.
GitHub is the curated engineering/research surface; AWS remains the canonical competition
workspace.
