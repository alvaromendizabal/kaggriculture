# Notebook 09 — diagnosed mechanics error and controlled resumption

## Evidence from the uploaded notebook

The uploaded `09_terminal_cash_feature_ablation(1).ipynb` contains three executed
code cells. The third logs 61 successful unit tests, `PREFLIGHT_PASSED` with ten
verified objects, and `ValueError: Continuation fixture endpoint incorrect` inside
`run_continuation.py:mechanics`. The call to `analyze` follows that gate and was
not reached by this recorded attempt. There are no new notebook-09 paired outcomes
in this upload. No inference about the current contents of the AWS disk is made;
the updater checks the recorded failure there before making changes.

## Root cause

The supplied fixture set WHEAT market inventory to 1,000,000 and assumed a one-coin
sale price. That assumption is false for WHEAT's logarithmic excess-supply curve:

```
max(1, round(25 - (5 / log(401)) * log(990001))) = 13
```

The next unit also quotes 13. Therefore the isolated final-callback fixture has
an expected cash advantage of **26 coins**, not 2. Its absolute endpoints are
3,000 versus 3,026. The early-sale catch-up fixture ends 3,026 versus 3,026.
These figures describe artificial test fixtures, not the user's competition agent.

The previous test double returned one coin above 100,000 inventory, embedding
the same false premise. That is why its 61 tests passed while the actual engine
rejected the fixture. This was an error in the supplied validation code, not a
user setup mistake and not evidence that the feature intervention underperformed.

Primary source inspected: Kaggle's `kaggriculture.py`, `MARKET_PARAMS['WHEAT']`,
`_shape`, `market_price`, and `_commit_unit`:
https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py
The AWS runner still requires interpreter SHA256
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.

## Correction and scope

The revised fixture calculates a quantity-aware price path before either branch,
then checks absolute cash, terminal status/clock, residual WHEAT and market
inventory. It saves the expected and observed values plus six transition records
before applying the gate. It does not merely replace 2 with a permissive tolerance
or use the observed outcome to define its expectation.

No policy source, feature-intervention rule, actor, source-episode set, experiment
protocol, 500 ms callback gate or 180-second work cap is changed. `continuation.py`,
`terminal_context.py`, `PROTOCOL.json`, the feature dictionary, previous packages,
GitHub checkout, raw data and private source episodes remain untouched.

## Preservation and restart

The updater accepts only the original source and this precise pre-branch failure.
It refuses to migrate completed branch checkpoints to changed code. It first saves
and verifies a ZIP of the original package (including notebook outputs and failure
diagnostics) outside the code directory. The updater replaces canonical files in
place. A code- and failure-hash-bound permission allows one restart, consumed before
work begins. A new failure cannot silently consume additional retries.

Completed branches from a future failed run remain preserved. They require diagnosis
before any further restart; this update does not override that requirement.

## Research decision remains open

Finish this paired final-day experiment before adding another action-changing
family. A successful mechanics check is only a correctness gate. It is not a
terminal improvement, a submitted score, or evidence of beating 3140.0.
The twelve terminal-exposure candidates remain logged but do not change actions,
so attribution to the post-action SELL-quantity feature stays interpretable.

After a positive result, evaluate fresh grouped episodes and distinct opponents;
after a null or harmful result, close or revise this specific hypothesis and move
to the next high-value feature family. Joint task opportunity, crop time-to-cash,
maintenance and survival value, labor/capital payback, and causal market history
remain open. Do not fit selection thresholds on the held-out groups.
