# Recover or reproduce the terminal feature study

Study 6's [registered protocol](terminal_protocol.md) fixes 48 games, four fresh
development seeds, both seats, three arms and two frozen opponents. No validation
or holdout seeds are used. Use Python 3.12 and `uv sync --frozen`; all commands below
assume `PYTHONPATH=src` and run at repository root.

## Source and checkpoint identity

Source was published in PR #8 at commit
`ac6d4309e21f219e635b0875bd5eb38149a7e3fa`, tree
`8ee92b7306e5a4d8861d5ec6b983eafd4ed8dd35`, before registered outcomes.
The registration identity is
`2887a1532e6ff297518da90dcd875518ab85f7229dd166f4dc14c13d3a56d670`.
The common study identity is
`9ef023519840bef990c3899c55ce2a681c8dc5e9017a4b9000b48623679129c3`.

Private bucket: `sagemaker-kaggriculture-560403859723-us-west-2`.
Prefix: `runs/terminal-routing-20260910/`.
The exact source archive is `artifacts/terminal_source.zip` under that prefix;
it contains the committed public project source, without raw game data. Source
and registration were uploaded before the first registered game. The source
archive is 1,319,051 bytes. Later reporting helpers are tracked in GitHub.

`python scripts/run_terminal_research.py register` rechecks every source,
protocol, runner and job identity. It refuses to overwrite changed registration.
Earlier research and livestock source modules remain unchanged. The new explicit
feed-policy fork changes only the terminal feed gate and wheat reserve. The
wrapper adds the separately registered joint liquidation arm.

## Bounded execution

Get task-scoped signed PUT URLs from the connected AWS account for only the
missing planned paths. `python scripts/run_terminal_research.py plan` lists them.
Keep URL manifests outside Git, never in public reports or notebooks:

```json
{"bucket":"sagemaker-kaggriculture-560403859723-us-west-2",
 "prefix":"runs/terminal-routing-20260910/",
 "uploads":{"artifacts/terminal_episodes/<registered-hash>.json.gz":"<signed PUT URL>"}}
```

```bash
python scripts/run_terminal_research.py batch --uploads /private/uploads.json
```

An invocation starts at most two new games or 60 seconds of new work. It finishes
and atomically saves the current game, then uploads it and records the version,
ETag and SHA256. Time limits govern starting work; transfer time may extend the
invocation. Existing valid games are reused. An upload failure cannot invalidate
the saved simulation. A lineage mismatch or HTTP authorization denial stops work.
This CPU experiment does not require starting SageMaker or any new AWS compute.

After the initial batches, `scripts/run_terminal_slice.py --uploads ...` provides
the same two-game/60-second bound while comparing previously uploaded local bytes
with their receipt instead of repeatedly decompressing every completed game.
It still rechecks registration and validates each newly completed/restored episode.
Full independent replay remains unchanged. The operational adapter records its own
source hash and creates no new study identity or outcome definition.

When the execution service disconnected during a combined compute/upload session,
work continued with `python scripts/prepare_terminal_game.py`: it prepares or reuses
exactly the first pending registered game and refuses to start another until the
preceding upload receipt exists. Upload that explicit completed path with the
original runner's `upload --uploads ... --paths <path>` mode. These separate short
calls preserve the same study identity. The completed game interrupted during
transfer was reused; a prior interrupted simulation without a complete checkpoint
had to restart. No valid completed registered game was recomputed.

## Audit and byte verification

```bash
python scripts/audit_terminal_evidence.py --partial --max-new-games 4
python scripts/verify_terminal_storage.py --downloads /private/downloads.json --max-new-objects 4
```

Download manifests contain `{"downloads":{"<relative-path>":"<signed GET URL>"}}`.
Only exact project bucket/key URLs are accepted. The verifier compares downloaded
bytes, length, object version, ETag and AES256 encryption against the upload
receipt. Each successful object check is cached atomically with its receipt and
verifier source identity. Later invocations reuse valid checks. Its final expected
set includes 48 games, the feature matrix, source, registration, a deterministic
48-entry audit archive and public evidence summaries.

The actual recovery probe uses a separate temporary destination, verifies the
downloaded game envelope, lineage, semantics and callback sequence, then reuses
that file on a second attempt. It creates zero games:

```bash
python scripts/verify_terminal_storage.py --downloads /private/one-game.json --recovery-probe
```

For a missing primary game, the public `restore(root, relative, url, destination)`
helper can restore that exact registered path; it refuses changed existing files.
Do not rerun valid simulations merely because a local copy was lost.

## Summarize and publish

```bash
python scripts/run_terminal_research.py summarize
python scripts/diagnose_terminal.py
python scripts/verify_terminal_report.py
python scripts/build_terminal_notebook.py
```

Summary requires all registered games and 16 identical preterminal blocks. It
zero-fills absent optional command counters only; primary outcomes cannot be
missing. Diagnostics and plots do not revise registered policies or metrics.
The independent audit replays actual decisions, sampled vectors, restoration,
public market bounds and both players' private transitions after each episode.

The canonical notebook preserves all 28 earlier code sources and has four new
code cells. GitHub Actions executes all three canonical notebooks, verifies all
study evidence and publishes the executed notebook with a new terminal receipt.
Download that actual artifact and verify run/head identity, notebook SHA256,
source preservation, 32 execution counts and ten static figures before committing
its bytes. Never fabricate outputs or overwrite the archived livestock receipt.
The final PR must pass quality checks for its exact head before merging.

## Operational incident

Automatic approval review initially rejected the source/registration upload
because ownership and payload scope were not established to its satisfaction.
Authenticated STS plus HeadBucket/GetBucketAcl with `ExpectedBucketOwner` confirmed
account 560403859723 owns the configured bucket. The archive was checked against
the public GitHub tree and contained no raw data. That new verification resolved
the block. No alternate credentials or unauthorized route was used, and no
registered game ran until durable source and registration receipts existed.

Final evidence transfer prompted the same ownership/payload concern for the
generated feature matrix. Fresh authenticated ownership/security checks succeeded.
The matrix envelope and numeric schema were inspected: 8,688 rows of 1,579 finite
features, with only arm/opponent/seat/seed/step experiment metadata, generated from
the 48 audited public-simulator games. It contains no customer or competition-kit
records. This evidence allowed the transfer. A subsequent network approval was
cancelled before a decision; remaining public reports were uploaded individually,
reusing the completed matrix and audit-archive receipts. The same bucket, credentials
and transfer mechanism were used throughout.
