# Project instructions

The user's standing standards are binding. Work in bounded, verifiable milestones.
The target is a rigorous employer-facing project; a numerical quality rating is not evidence.

## Research gate

- Kaggriculture is an agent simulation. Study the official interpreter and actual observations.
- Feature research precedes final policy/model optimization. Notebook `02` cannot be called
  complete before major plausible families have been implemented or rejected with evidence.
- Candidate count is not quality. Log generated, screened, rejected, and retained counts,
  rejection reasons, information availability, computational cost, and paired ablation outcomes.
- Use diverse development opponents and seed groups. Keep validation and holdout seeds disjoint.
  Never randomly split turns from one episode across folds. Both seats of a seed stay together.
- Learned encodings, transformations, feature screening, policy selection, and calibration use
  training episodes only. A later holdout is not an iterative feature-selection dataset.
- Policies may use current/past legal observations and bundled code/models. Never use the
  environment seed, future shops, final rewards, hidden engine state, or opponent private state.
- Official ranking is based on wins/losses/ties and the final Bradley–Terry evaluation. Local
  match score and coin diagnostics are not official leaderboard ratings.

## Engineering and presentation

- Use canonical filenames; update in place. No fix/fixed/repair/repaired copies.
- Edit, test, execute, inspect, then commit. Keep tests for leakage, mechanics, schemas,
  reproducibility, recovery, and lineage. Fail clearly on incorrect or stale artifacts.
- Use modular typed Python, pinned dependencies, UTC logs, stage/total elapsed times, and
  heartbeats. Expensive valid episodes/checkpoints must survive interruption and be reused.
- Public review path: README → executed notebooks. Use clear Plotly figures with meaningful
  explanations, honest limitations, and a static fallback where needed for GitHub.
- Raw episode logs, feature matrices, and checkpoints live in private versioned S3 storage.
  Keep notebooks, Python, small summaries, and tests in GitHub. Do not commit secrets or data kits.
- Use branches, passing quality checks, reviewed diffs, and meaningful PRs. Verify remote state.
- Report measured evidence; never imply that candidate features improved a policy before ablations.
- Finish each agreed milestone without asking the user to debug or run accessible work.
- No live inference network calls: competition rules prohibit ingress/egress during episodes.

## First milestone boundary

Provision the CPU workspace, pin and verify the official simulator, execute deterministic full
seasons, audit legal observation candidates, test recovery, and publish notebooks `00` and `01`.
Do not train a final model, use validation/holdout seeds, or submit a baseline during this milestone.

## Canonical execution

`uv sync --frozen` then `PYTHONPATH=src uv run python scripts/run_foundation.py`.
Quality: `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.
Notebook execution: `PYTHONPATH=src uv run python scripts/execute_notebooks.py`.

At competition publication time, comply with the public-sharing requirement in rule 3.6.b
(companion competition forum post or notebook). Do not send a forum message without the user's
authorization. Keep the exact companion text ready for review.
