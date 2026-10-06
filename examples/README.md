# Paired evaluation on fictional episodes

This small CPU example calls the repository's actual
[`final_sprint.py`](../src/kaggriculture_review/final_sprint.py) evaluation helpers.
Its eight episode outcomes and toy thresholds were authored for explanation; they contain
no competition replays, private model predictions, controller source, or current policy recipe.

Run from an authorized checkout with Python 3.12:

```bash
python3 examples/run_demo.py
```

The script uses only the Python standard library. It prints a JSON summary and writes no
result files. No engine games, model training, credentials, AWS access, or submissions are
involved. Python may create its normal import cache unless bytecode writing is disabled.

## What the output demonstrates

| Check | Expected result | Meaning |
|---|---|---|
| Six development episodes | Keeper score 50%; candidate score 66.7% | The candidate improves average win/tie score on the fictional development sample |
| Paired tradeoff | Three rescued losses, two sacrificed wins, +1 net score unit | An aggregate gain can conceal damage to previously won episodes |
| Explicit toy gate | `REJECTED_SACRIFICED_WINS` | The candidate exceeds the toy maximum of one sacrificed win despite meeting gain/rescue thresholds |
| Chronological split | `toy-01` through `toy-06` precede reserved `toy-07` and `toy-08` | Future episode IDs are kept out of candidate comparison; no candidate holdout outcomes are supplied |
| Invalid episode pairing | Duplicate keeper/candidate IDs and a missing candidate episode raise `ValueError` | Silent overwriting or comparing different episodes is rejected |

This is a worked example of evaluation behavior, not a trained selector or proof of
competitive performance. It does not demonstrate opponent reactions, calculate an official
rating, or reproduce the historical research scores. The toy gate is intentionally visible
and is not a disclosure of the current private competition configuration.

The [portfolio notebook](../notebooks/57_portfolio_review.ipynb) presents the same reasoning
alongside dated aggregate project evidence. Read the
[reproducibility guide](../docs/REPRODUCIBILITY.md) for the broader boundary.
