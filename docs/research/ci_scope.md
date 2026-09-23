# Publication integrity and maintained-code checks

The repository contains both maintained implementation code and frozen executed research
evidence. They need different automated checks.

Historical standalone packages were originally added as byte-preserved evidence. Their
recorded hashes and executed outputs must not be rewritten by a bulk lint fix or formatter.
The same boundary now applies to the executed frontier notebooks published from the AWS
research workspace.

## Two explicit scopes

- **Maintained code:** the root Ruff rules still come from `pyproject.toml`.
  `src/`, `tests/`, `scripts/`, configurations, and maintained notebook sources remain
  under the normal lint, formatting, test, and evidence checks.
- **Frozen executed evidence:** `research/manual/`, the publication overview, and the
  executed frontier notebooks listed below preserve the experiment state that was actually
  returned from AWS. They are not treated as reusable Python modules for source-style lint.

The frontier evidence notebooks excluded from Ruff source-style checks are:

- `notebooks/47_frozen_public_reference_benchmark.ipynb`
- `notebooks/48_frozen_timing_reference_confirmation.ipynb`
- `notebooks/49_live_submission_feedback_and_incremental_data.ipynb`
- `notebooks/50_terminal_crew_route_market_planning.ipynb`
- `notebooks/51_counterfactual_market_action_learning.ipynb`
- `notebooks/53_public_frontier_reproduction_and_league.ipynb`

These notebooks contain embedded run evidence and generated payloads that can legitimately
produce very long JSON strings and compact plotting cells. Reformatting them after execution
would change the preserved research artifact without improving the maintained implementation.

This exclusion is deliberately narrow. It does **not** exempt new reusable Python modules,
tests, scripts, or future maintained notebook source from the strict Ruff policy.

## What still gates the frozen notebooks

A notebook is not accepted merely because Ruff skips it. The milestone runner must verify,
and the returned evidence must record, the relevant notebook gates:

- execution reaches completion with no unresolved cells;
- Plotly cells return control to the kernel;
- important Plotly figures are embedded inline;
- saved figures remain present after save/reopen;
- figure dimensions remain readable;
- the notebook contains the experiment metrics and decision;
- source, data, checkpoint, and run identities remain recorded.

Where a publication lock applies, `scripts/verify_publication_snapshot.py` checks tracked-file
coverage, sizes, SHA256 hashes, Python syntax, notebook JSON structure, and agreement with the
publication manifest before the remaining CI steps continue. Do not regenerate a lock merely
to hide a mismatch.

## What this gate does not certify

It does not rerun AWS experiments, replay private trajectories, prove historical code is
style-clean, or turn a local result into an official Kaggle result. Saved evidence is reported
honestly. Future maintained implementations should be developed under the normal strict
lint/test policy; frozen snapshots are evidence, not a general exemption.

Existing root tests and canonical reporting checks remain unchanged. Raw competition replays,
credentials, environments, private checkpoints, and uncleared third-party controller source
remain outside the public repository.

## Local, no-game checks

```bash
python scripts/verify_publication_snapshot.py
python -m unittest discover -s tests -p test_publication_snapshot.py -v
python -m ruff check .
python -m ruff format --check .
```

Use the verified project interpreter. These commands do not install packages or run new
competition simulations.
