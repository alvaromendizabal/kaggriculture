# Recover or continue the livestock feature study

The source-locked protocol is [livestock_protocol.md](livestock_protocol.md).
Use Python 3.12, `uv sync --frozen`, and `PYTHONPATH=src`. Main experiment source
is isolated in `src/kaggriculture_livestock`; all earlier research code is frozen.

## Exact identity before compute

`python scripts/run_livestock_research.py register` rechecks engine, protocol,
source, runner and all 64 job identities against the saved registration. It fails
on a mismatch rather than relabeling an earlier outcome. To inspect planned paths,
run the same script with `plan`. The original source archive is private at
`s3://sagemaker-kaggriculture-560403859723-us-west-2/releases/livestock-resource-loops/source.zip`.
Outputs use prefix `runs/livestock-resource-loops-20260910/` in that bucket.

Do not start SageMaker to run this small CPU study. No new AWS compute was needed.
Storage and requests remain metered. Never commit credentials or signed URLs.

## Restore completed games

Obtain authorized signed GET URLs for the exact missing job paths from the AWS
connection. Save a temporary file outside the checkout:

```json
{"downloads": {"artifacts/livestock_episodes/<registered-hash>.json.gz": "<signed GET URL>"}}
```

```bash
PYTHONPATH=src python scripts/restore_livestock_checkpoints.py --downloads /private/downloads.json
```

Restoration verifies envelope checksum, lineage, semantic identity, callback order,
schema, outcomes and completed-game status before installing the file. Existing
valid episodes are reused. Incorrect lineage, corruption and path traversal fail.
The scripts never print signed URLs and stop on HTTP authorization failures.

## Continue bounded batches

Obtain signed PUT URLs for only the missing planned jobs. Save this outside Git:

```json
{
  "bucket": "sagemaker-kaggriculture-560403859723-us-west-2",
  "prefix": "runs/livestock-resource-loops-20260910/",
  "uploads": {"artifacts/livestock_episodes/<registered-hash>.json.gz": "<signed PUT URL>"}
}
```

```bash
PYTHONPATH=src python scripts/run_livestock_research.py batch --uploads /private/uploads.json
```

Each invocation starts at most eight new games or 240 seconds of new work, then
finishes the current game. It saves each episode before uploading, records the
object version/ETag/checksum, and reuses valid work if a transfer needs retrying.
Budget checks stop starting games; they do not interrupt a completed-but-unsaved
episode. A batch can exceed 240 seconds while finishing an episode or transferring.
Checkpoint validity never depends only on file existence.

If the execution service disconnects during a longer session, use
`scripts/run_livestock_slice.py --uploads /private/uploads.json`. This operational
adapter starts at most one new game per invocation, within the registered maximum
of eight. It rechecks the original source registration, verifies completed file
digests, restores any completed-but-unuploaded game, and restricts signed URLs to
the exact configured S3 bucket and object path. It changes no experiment input.
After the final slice, the original `batch` command revalidates all 64 checkpoints
and produces the complete progress manifest without executing another game.

## Audit and summarize

```bash
PYTHONPATH=src python scripts/audit_livestock_evidence.py --partial --max-new-games 8
PYTHONPATH=src python scripts/summarize_livestock.py
PYTHONPATH=src python scripts/audit_livestock_evidence.py --max-new-games 8
```

Repeat bounded audits until all 64 are checked. Matching audit checkpoints are
reused; no game is executed by the auditor. `artifacts/livestock_audits.zip` stores
the final per-game audit cache. Its entries must match `livestock_integrity.json`
before restoration. Run `scripts/manage_livestock_audit_archive.py restore --archive`
with the downloaded archive path; it validates the exact manifest, checksums,
envelopes and source lineage before installing missing cache files. The public audit
record also verifies candidate actions,
stock/sale containment, both players' actual private transitions and nine product
balances per player. Evaluator-only inventories never enter a decision feature.

Use `summarize_livestock.py` for final reporting. The registered simulator emits
sparse optional action counters: absent `FERTILIZE` keys mean zero events, not an
unknown measurement. The reporting adapter fills those command counters with zero
before means; paired estimators and all primary outcomes remain unchanged. Its
source hash is recorded separately. The original source-locked runner and raw
episodes remain unchanged. This is an explicit reporting correction, not an
alteration to the experiment or a policy tuned after seeing results.

Upload the matrix, audit archive and public summary files to their exact paths.
Then use authorized signed downloads with `verify_livestock_storage.py --downloads`
to verify every byte, SHA256, size, version, ETag and AES256 header. The required
set is enumerated by `required_paths`; existence or upload success alone is not
the final persistence claim. `verify_livestock_report.py` rechecks the published
evidence without credentials or rerunning the 64 private episodes.

Storage verification also checkpoints each completed download. By default each
invocation checks at most eight new objects and reports partial progress until all
82 are verified. Repeat with fresh signed URLs as needed. Cached checks bind the
exact upload receipt, object version, local bytes and both verifier source hashes;
changed content or code cannot silently reuse an old check. Each result retains
its actual download-verification time. Only a complete set writes the final public
cloud receipt. This makes execution-service interruptions recoverable during
publication as well as during simulation.

## Publish a genuinely executed notebook

`build_livestock_notebook.py` appends five cells to canonical notebook 02 and
asserts the earlier 23 code-cell sources are unchanged. Execute all canonical
notebooks with `scripts/execute_notebooks.py` in the pinned environment; CI is an
authorized execution path. `verify_livestock_notebook.py --record` captures the
actual artifact, source, study and plotting hashes, execution counts, timing and
eight static plot outputs. Preserve the earlier supply receipt as an ancestor.

When importing a CI artifact, compare expected code sources first, inspect output
figures, verify the receipt and publish the actual executed file. A successful
workflow does not by itself update the committed notebook. Finish with passing
checks on the exact PR head, then verify the merged remote commit.

Feature research remains open after this milestone; validation/holdout pools and
final Kaggle submission are separate, untouched stages.
