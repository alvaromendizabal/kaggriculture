# Study 4: reproducible execution and recovery

This runbook concerns the registered 64-game cash-constrained supply study, not
future feature selection or a final competition submission. The feature gate
remains closed. Do not modify the registered sources to resume an old run.

## Durable identities

- Git branch: `research/cash-constrained-supply`.
- Preregistration commit: `b0b6b8a35c833abf877ed451e09b633482cfc66f`.
- Registration identity: `6a3d6a87199ae736ebc1b1e659d5eca140742c911904fd07780cde820692d6cd`.
- AWS region: `us-west-2`.
- Private bucket: `sagemaker-kaggriculture-560403859723-us-west-2`.
- Episode/report prefix: `runs/cash-constrained-supply-20260910/`.
- Frozen source key: `releases/cash-constrained-supply/source.zip`.
- Frozen source SHA-256: `080270bfdc81285db890147b69b4cc71460a9b961231197e5b188b0d9a82f30f`.
- Frozen source version: `9tjzEqL15Xx_dF2cuGAbZb4GEmfQ76Pc`.

The source archive and registration were saved before the first fresh game.
Public summaries and source belong in GitHub; raw observations, hidden evaluator
truth and the large feature matrix do not. No signed URL belongs in Git history.
The original archive is immutable evidence: do not replace it with final reports.

## Inspect before restarting

Use the pinned Python 3.12 environment (`uv sync --frozen`), then:

```bash
PYTHONPATH=src uv run python scripts/run_supply_research.py register
PYTHONPATH=src uv run python scripts/inspect_supply_progress.py
```

The first command verifies an existing registration without rewriting it. The
second validates existing episodes and reports their upload receipts; it starts
no games. An incomplete inspection is not proof that an old process is dead.
Confirm no other runner is active before starting a batch; there is no distributed
lease or concurrent-writer support.

## Restore completed episodes

For an empty workspace, use the authorized AWS connection to obtain short-lived
GET URLs for the exact registered keys. Keep a local manifest outside the repo:

```json
{"downloads": {"artifacts/supply_episodes/REGISTERED_HASH.json.gz": "AUTHORIZED_GET_URL"}}
```

```bash
PYTHONPATH=src uv run python scripts/restore_supply_checkpoints.py --downloads /absolute/path/downloads.json
```

Only registered job paths are accepted. Every downloaded envelope, source lineage,
semantic checksum, callback sequence and outcome is validated before atomic
installation. An existing valid episode is reused without a download. Corruption
or mismatched lineage stops restoration; it does not silently trigger fresh games.

## Resume missing games, at most eight per batch

Create a separate, short-lived PUT manifest for missing or not-yet-uploaded files:

```json
{"bucket": "sagemaker-kaggriculture-560403859723-us-west-2", "prefix": "runs/cash-constrained-supply-20260910/", "uploads": {"artifacts/supply_episodes/REGISTERED_HASH.json.gz": "AUTHORIZED_PUT_URL"}}
```

```bash
PYTHONPATH=src timeout 270 uv run python scripts/run_supply_research.py batch --uploads /absolute/path/uploads.json
PYTHONPATH=src uv run python scripts/audit_supply_evidence.py --partial --max-new-games 8
```

The runner starts at most eight new games and checks elapsed time before starting
another. Each finished game is persisted and uploaded before moving on. A failed
upload leaves its completed local checkpoint intact. An expired URL can be
replaced using the same approved AWS connection, but an access denial is a stop
condition, not permission to find alternative credentials. A killed unfinished
game can require replay; the contract protects **completed** games.

The independent audit has its own checksummed, code-bound cache. It can run beside
the sole episode runner and uses evaluator-private truth only after reconstructing
the policy's legal features. Final auditing reuses valid completed audits.

## Complete and verify the evidence

Only after all 64 registered games exist:

```bash
PYTHONPATH=src uv run python scripts/run_supply_research.py summarize
PYTHONPATH=src uv run python scripts/audit_supply_evidence.py
```

Upload the exact generated matrix and result paths with the runner's `upload`
mode and explicit `--paths`. The storage verifier expects 75 artifacts: 64
episodes, one joint matrix, nine registration/result/audit files, and the original
source archive. Its GET manifest uses a different schema:

```json
{"downloads": [{"path": "reports/supply_games.csv", "key": "runs/cash-constrained-supply-20260910/reports/supply_games.csv", "url": "AUTHORIZED_GET_URL"}]}
```

```bash
PYTHONPATH=src uv run python scripts/verify_supply_storage.py --downloads /absolute/path/verification.json
PYTHONPATH=src uv run python scripts/verify_supply_report.py
```

The example has one entry for readability; actual verification requires the exact
complete set. Remote bytes, size, SHA-256, version, ETag and AES256 encryption must
match the local upload receipts. A public receipt does not grant bucket access.

## Notebook publication

`scripts/build_supply_notebook.py` appends six study-4 cells to canonical notebook
02 and checks that the earlier 17 code cells are unchanged. Run this builder only
when editing the section: it clears that section's previous execution outputs.
The final publication workflow executes all notebooks in fresh kernels and
uploads notebook 02 plus `reports/supply_notebook_execution.json` as an artifact.
The earlier source-only checkpoint retained the old workflow and notebook.
Download the genuine execution artifact, verify it with
`scripts/verify_supply_notebook.py`, inspect its figures, and commit it before
merging a passing PR. Do not fabricate outputs or call unexecuted cells executed.

This study uses local CPU simulation and normal GitHub CI notebook execution;
it does not require restarting SageMaker compute. Private S3 and persistent EBS
storage can still incur charges when compute is off.
