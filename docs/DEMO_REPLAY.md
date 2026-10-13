# From an exported season to a verifiable decision trace

Field Notes exports enough public information to replay a season action by action.
The verifier starts from the same authored seed, reconstructs each legal observation,
recomputes public policy choices, applies recorded actions, and compares the complete
resource ledger and outcome. A matching checksum alone is not enough to pass.

## Run a reference experiment

Use Node 24.19.0 for the recorded CI environment; Node 22 is also tested. No package
installation, official simulator, cloud credentials or private policy is required.
From a checkout, choose a new output directory outside the repository:

```bash
node tools/replay_public_demo.mjs --output /tmp/farming-replay
node tools/replay_public_demo.mjs --output /tmp/farming-replay --check
```

The reference trace contains one manual action and 23 public-policy actions across a
complete 24-day season. A separate paired comparison runs three fixed policies over
eight identical seeded environments: 24 policy-seasons. The second command re-executes
verification without modifying the saved bundle.

## Verify your own decisions

In the [live lab](https://alvaro-farming-agent-lab.tartmacaw2.chatgpt.site), play a season
manually or with autoplay, optionally run the paired comparison, then select **Export
evidence**. Partial and empty sessions are valid; their receipts say `IN_PROGRESS` and
record the actual number of replayed days.

```bash
node tools/replay_public_demo.mjs --input field-notes-evidence.json --output /tmp/my-farming-replay
node tools/replay_public_demo.mjs --output /tmp/my-farming-replay --check
```

A `PASS` requires all of these conditions:

1. The seeded environment regenerates the observed rain and prices.
2. Each action is legal at that point. A policy-labelled choice and reason match the
   named public policy on the current-and-past observation; manual choices are checked
   for legality and recorded as manual.
3. Observation checksums, days, plot states, water, cash, inventory, accounting ledgers,
   assets and terminal status exactly match the replay.
4. Every included paired season and summary recomputes under the same seed range.
5. No missing or additional fields bypass verification.

All comparisons are exact; the receipt does not use numerical tolerance. The environment
checksum remains a compact browser diagnostic. Artifact identity uses SHA-256, and the
verifier also recomputes all content so neither checksum substitutes for actual replay.

## What the bundle records

| File | Purpose |
|---|---|
| `export.json` | Interactive choices, full legal transition trace and optional paired comparison |
| `receipt.json` | Checks performed, actual replay counts, Node/platform, UTC time, elapsed replay time and source SHA-256 identities |
| `manifest.json` | SHA-256 hashes for the exact export and receipt bytes |

The receipt binds the engine, UI exporter, replay validator and transport utility.
Changing a bound source invalidates an existing bundle; use a new output directory after
an intentional update. Missing/extra files, symlinks, malformed or oversized JSON, changed
manifests, fabricated balances and altered decisions fail closed. Output is published
only after a successful replay; existing unrelated files are preserved.

## Inspect the implementation

- [Domain replay](../tools/replay_public_demo.mjs): reconstructs decisions with the actual simulator and policies.
- [Artifact transport](../tools/replay_bundle.mjs): validates paths, source identities and bundle publication.
- [Adversarial tests](../tools/test_replay_public_demo.mjs): altered observations, actions, policy provenance, accounting, comparisons and manifests.
- [UI tests](../tools/test_public_demo.mjs): replay the real browser export handler's partial-season and paired evidence.
- [Public-demo CI](../.github/workflows/public-demo.yml): two Node versions test generation, imported evidence and repeat verification.

```bash
node --test tools/test_replay_public_demo.mjs
node tools/test_public_demo.mjs
```

This proves local consistency with the public authored surrogate, not who took the
actions or when a historical run occurred. It does not reproduce the official engine,
authenticate a historical rating, or expose private agent weights, opponent corpora,
competitive policies or current strategy parameters.
