# After the two screen results have been reviewed

This file documents the prepared interface. It is **not** an instruction to run
pairs now. The current next action is to return both screen results.

`run_service.py pair --round 19 --block 1 --reviewed-screen <SHA256>` is the
single-block interface. The hash must be the exact accepted screen report hash,
not a guessed value. A nonactivated screen cannot launch a pair. Blocks 2–4 also
require their predecessors and stop after a negative predecessor. The CLI never
runs multiple pairs automatically. The same interface applies to round 20.

Following a reviewed pair, run `run_service.py summary --round 19` (or 20), reopen
the relevant notebook, and use the already provided optional-result display cell.
The notebook does not launch more games. Save and bundle again. Never change the
protocol, thresholds or seed to relabel a failed run; record a new reviewed
hypothesis and compatible artifact identity instead.
