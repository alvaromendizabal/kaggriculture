# Reproducibility and publication scope

This repository provides a reviewable research record and executable evaluation components.
The public checkout includes the demonstration and evidence checks. The full private agent
and raw evidence for every historical experiment remain outside this release.

## Run the Farming Decision Lab

```bash
python -m http.server 8000
```

Open `http://localhost:8000/public-demo/`. A 24-day authored season has four plots and explicit legal-action masks. Play manually or compare three generic policies using identical seeded weather and price sequences. The policies act on current and past observations only. The browser computes the resulting actions, inventory and economic outcomes locally.

```bash
node tools/test_public_demo.mjs
```

No dependency installation, backend, private agent or cloud account is needed. This educational surrogate illustrates decision and evaluation contracts; it does not reproduce official mechanics or generate a competition rating. The Python paired-outcome example below remains a separate public component check.


## What can be reproduced

| Layer | Available from the public checkout | Boundary |
|---|---|---|
| Environment | Python 3.12, pinned project dependencies, committed `uv.lock` | Initial dependency installation needs package-network access |
| Aggregate checks | Arithmetic, report structure, recorded decisions, notebook-output checks | Checks consistency of published evidence; does not independently regenerate raw games |
| Evaluation behavior | Paired comparisons, chronology and promotion-gate tests, synthetic example | Fictional example outcomes are not competitive measurements |
| Notebook review | Saved executed summaries and charts, with a compact portfolio entry point | Aggregate re-execution does not retrain an agent |
| Foundation environment | Existing full CI runs small official-engine foundation checks | These are not the full competitive experiments |
| Historical competitive results | Summaries, protocols, source/bundle identities | Full private reruns require withheld artifacts and authorized competition data |

## Bounded review without games or AWS

Install Python 3.12 and `uv`, then run the following from the repository root:

```bash
uv sync --frozen
uv run pytest -q tests/test_final_sprint.py
uv run python scripts/verify_final_sprint.py
python3 scripts/verify_portfolio_review.py
python3 examples/run_demo.py
```

The first command installs the locked environment. The following commands validate the
published final-sprint evidence and exercise the synthetic evaluation example. They do not
launch official-engine games, train policies, access AWS, or submit anything to Kaggle.

Open [notebook 57](../notebooks/57_portfolio_review.ipynb) for the compact executed review and
[notebook 56](../notebooks/56_final_sprint_ladder_alignment.ipynb) for detailed sprint evidence.
The [example README](../examples/README.md) documents its expected behavior and output.
To regenerate notebook 57 with a real Jupyter kernel, run
`uv run python scripts/execute_portfolio_review.py`. This reads the committed aggregate
reports and synthetic example; it runs no private policy training. The execution script
writes and reopens the notebook, and the portfolio verifier checks the saved outputs.

The broader [quality workflow](../.github/workflows/quality.yml) runs lint, formatting,
all retained tests, final-result verifiers, small official-engine foundation runs, and notebook
execution. It is intentionally broader than the no-game commands above.

## Full competitive reproduction

The project-specific AWS space and bucket have been retired. Public examples and evidence checks run independently of that infrastructure. The September sprint
manifest records Python 3.12, Kaggle Environments 1.32.7, and its research environment.
Historical hardware metadata is not a requirement for reviewing this checkout and does not
confirm the current state of any AWS space.

Full competitive reproduction additionally needs the exact keeper/candidate artifacts,
registered chronological episodes, raw replay streams, engine and source identities, and
applicable authorized competition access. Some external sources can be retrieved upstream;
private checkpoints, current orchestration, and submission archives are intentionally absent.
The public reproduction contract covers source checks, aggregate evidence and authored examples.
Re-evaluating the historical rating requires the separate private agent and competition environment. See the [sprint reproduction details](research/final_sprint_reproduction.md).

## Attribution, data, and evidence limits

Third-party controllers retain upstream attribution. Raw replay corpora, credentials,
account configuration, private S3 mirrors, private checkpoints, submission archives, and
exact current competitive implementation details are excluded from the review materials.
Source hashes identify recorded artifacts; a hash string alone does not authenticate an
artifact that a reviewer cannot obtain.

The latest evidence is dated September 30, 2026. Rating, win/tie score, coin margin, and
forecast MAE are separate measures. The native harvest/service recovery result remains
pending in that record, and the full historical AWS bill is not published.

## Recompute a browser export

The [public replay contract](DEMO_REPLAY.md) adds a dependency-free Node command that
regenerates the synthetic environment and verifies every exported computation against
the actual browser engine. It writes a source/runtime receipt and content manifest,
rejects altered results, and re-executes verification under `--check`. CI exercises
this path on Node 22 and Node 24.19.0; no private research is launched.
