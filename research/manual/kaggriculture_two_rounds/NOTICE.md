# Source attribution and testing boundary

`tests/official_refresh_excerpt.py` contains an attributed excerpt of the official
Kaggle environment's crop refresh logic, licensed under Apache License 2.0.
The license is included at `tests/APACHE-2.0.txt`.
Primary source: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py

`baseline/` contains byte-identical copies of three previously delivered project
modules: the callback, cash features, and sale-timing features. They preserve the
existing control and final-callback sale correction; they are not a new baseline fit.

Local trajectory tests use explicitly artificial actors and environments. The official
refresh excerpt is not a substitute for testing the complete installed engine.
The live notebooks require source, engine, archived-action and full-episode checks.
