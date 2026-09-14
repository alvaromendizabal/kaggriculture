# Publication integrity and maintained-code checks

PR #16 adds historical, standalone research packages as byte-preserved evidence.
Their recorded hashes and executed outputs must not be rewritten by a bulk lint
fix or a formatter. The initial Quality run scanned those independent snapshots
as if they were a newly refactored part of the baseline, and stopped at Ruff.

## Two explicit scopes

- **Maintained code:** the root Ruff rules still come from `pyproject.toml`.
  Existing `src/`, `tests/`, `scripts/`, and the original notebooks remain in
  scope. No existing lint rules or root test steps are removed.
- **Frozen publication:** `research/manual/` and the single newly published
  `notebooks/00_research_overview.ipynb` retain their committed bytes. The new
  `scripts/verify_publication_snapshot.py` checks tracked-file coverage, sizes,
  SHA256 hashes, Python syntax, notebook JSON structure, and agreement with the
  original publication manifest before the existing CI steps continue.

The root `ruff.toml` inherits the existing configuration and excludes only these
frozen paths from root formatting and linting. The lock records the source commit
and hashes every tracked file in that scope. New unlisted files and changed bytes
fail the integrity check. Do not regenerate the lock merely to hide a mismatch.

## What this gate does not certify

It does not execute the historical experiment suites, replay raw trajectories,
prove that all historical code is style-clean, or establish scientific validity.
Unexecuted notebook cells and saved error outputs are reported, not overwritten.
Use each snapshot's original runbook and environment for independent reproduction.
Future maintained implementations should be developed under the normal strict
lint/test policy; historical snapshots are evidence, not a general exemption.

Existing root CI tests and evidence/notebook checks remain unchanged. Some of
those existing CI steps execute baseline smoke work and canonical reporting
notebooks in the GitHub runner. This publication change does not rerun AWS
experiments or promote a candidate policy.

## Local, no-game checks

```bash
python scripts/verify_publication_snapshot.py
python -m unittest discover -s tests -p test_publication_snapshot.py -v
python -m ruff check .
python -m ruff format --check .
```

Use the verified project interpreter. These commands do not install packages or
run simulations. Integrity checks precede CI's ordinary baseline execution.
