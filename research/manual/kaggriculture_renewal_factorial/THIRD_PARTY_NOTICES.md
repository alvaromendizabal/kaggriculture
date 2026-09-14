# Source and license notes

`tests/official_refresh_excerpt.py` reproduces the public Kaggle `_daily_refresh_plants` component and crop constants as attributed in that file. The upstream project uses Apache License 2.0; see `APACHE-2.0.txt`. It is an excerpt, not the full engine. The live run uses the installed package, verifies its hash and compares the excerpt's AST to the installed component.

The lifecycle feature definitions and small mechanics checks were carried forward from the user's previous notebook-15 package. New experimental logic is in `factorial_policy.py`, `factorial_analysis.py`, `factorial_experiment.py`, `joint_features.py` and `run_factorial.py`.
