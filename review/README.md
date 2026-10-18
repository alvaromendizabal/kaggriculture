# Legal actions. Paired experiments. Defensible decisions.

**Alvaro Mendizabal · Sequential decisions / simulation / agent evaluation**

An agent-research project connecting legal observations, resource allocation, policy integration, and evidence-based promotion. The public lab exposes the mechanics behind policy behavior without distributing private competition strategies.

[Project overview](../README.md) · [Printable inspection brief](index.html) · [Review configuration](project.json)

## Review the engineering, not just the headline

| Focus | Decision to inspect | Follow the proof |
|---|---|---|
| Applied AI | **Constrain the agent to legal information and actions.** Connect observable state to feasible actions instead of allowing hidden simulator state to enter the policy. | [Code](../src/kaggriculture_research/audit.py) · [Tests](../tests/test_foundation.py) · [Evidence](../examples/run_demo.py) |
| Data science | **Evaluate policies on paired populations.** Separate development from a later holdout and preserve the registered promotion decision. | [Code](../src/kaggriculture_review/final_sprint.py) · [Tests](../tests/test_final_sprint.py) · [Evidence](../reports/final_sprint_2026-09-30.json) |
| ML engineering | **Reuse completed experiments rather than replay games.** Track accepted results and artifact identities so expensive completed episodes remain reusable. | [Code](../src/kaggriculture_research/artifacts.py) · [Tests](../tests/test_foundation.py) · [Evidence](../docs/REPRODUCIBILITY.md) |
| Data science | **Separate scientific failure from transport failure.** Record failed promotions and post-game diagnostics as different events in the review evidence. | [Code](../src/kaggriculture_review/portfolio.py) · [Tests](../tests/test_portfolio_review.py) · [Evidence](../CASE_STUDY.md) |

The linked tests are review entry points, not a claim that this compact command executes the full research suite. The project’s canonical reproducibility guide describes the broader environment and tests.

## One command, an inspectable result

From a checkout with Python 3.11 or newer:

```bash
python3 -S review/run.py --output /tmp/ml-review
```

Open `/tmp/ml-review/index.html`. The directory contains an accessible HTML brief, `receipt.json`, `manifest.json`, and logs for each executed command. No Python package installation, model download, cloud credentials, or external dataset is required. On Windows, substitute a writable directory outside the checkout for `/tmp/ml-review`.

To execute the browser engine checks as well, install Node.js and use a separate output directory:

```bash
python3 -S review/run.py --output /tmp/ml-review-node --with-node
python3 -S review/run.py --output /tmp/ml-review-node --with-node --check
```

The default path does not execute Node checks and never labels them as passed. CI runs both the Python and browser checks on Python 3.11 and 3.13. It retains the exact review artifacts with the workflow run.

| Check | Runtime | Inspected entry point |
|---|---|---|
| `review-evidence` | python | [`scripts/verify_portfolio_review.py`](../scripts/verify_portfolio_review.py) |
| `action-contract` | python | [`examples/run_demo.py`](../examples/run_demo.py) |
| `farming-lab` | node | [`tools/test_public_demo.mjs`](../tools/test_public_demo.mjs) |

## What is actually reproduced

The Python checks validate published sprint evidence and execute the authored action-contract example. Optional Node tests exercise the farming lab. The lab is a simplified synthetic economy, not the official simulator or a claimed deployed policy.

A repeat invocation verifies the saved bundle rather than rerunning completed checks. `--check` performs verification only. A changed linked source file, missing evidence, changed artifact, failed command, invalid path, or mismatched check mode causes a nonzero exit. Use a fresh output directory after an intentional source change; stale evidence is never silently relabeled as current.

Each command has a default 90-second deadline, configurable with `--timeout`. The runner records UTC time, interpreter version, elapsed command times, command identities, and SHA-256 hashes for its configuration, template, invoked entry points, linked implementations, tests, and evidence. Failed runs keep diagnostic logs in a separately named failed-run directory and never produce a success receipt.

The fingerprint covers this curated review surface, **not every transitive dependency or every repository file**. Checksums establish consistency, not independent authentication of historical scores. HTML links follow the current default branch; the receipt is the record of the local bytes inspected. The static page is explicitly an inspection brief, not an execution receipt.

## Public/private boundary

Raw episode logs, private feature matrices, exact strategy parameters, competition checkpoints, opponent-specific state, and unpublished policy recipes remain excluded.

This review adds no training result and changes no historical score, selection decision, notebook output, source attribution, or license. A synthetic demonstration, an aggregate evidence check, public reference training, and exact private-model replay are different reproducibility levels.

## Verify the review kit itself

```bash
python3 -B -S -m unittest discover -s review -p test_run.py -v
python3 -B -S -O -m unittest discover -s review -p test_run.py
python3 -S review/run.py --check-page
```

After an intentional configuration or template change, regenerate the static brief with `python3 -S review/run.py --render`, inspect it, then run the checks above. The kit needs no JavaScript or network access to render its HTML. It uses semantic headings, keyboard-visible links, a skip link, responsive layouts, and print styling.

## Source-bound replay

The optional Node path also exercises the [export replay contract](../docs/DEMO_REPLAY.md).
Review receipts now fingerprint the complete public demo and tool source inventory,
including added and removed files. They bind command arguments, captured logs and
the rendered brief. A clean checkout records its exact commit with immutable source
links; uncommitted work is identified explicitly. These are consistency checks, not
an independent authentication of historical research scores.
