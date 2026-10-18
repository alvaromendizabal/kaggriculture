# Case study: when local agent strength failed to transfer

**Author:** Alvaro Mendizabal

**Domain:** competitive sequential decision-making in Kaggriculture

**Evidence cutoff:** September 30, 2026; this case study does not report a new live rating.

## Problem

A farming agent must allocate workers, manage production and inventory, navigate, and
trade under a changing opponent. The project used the official simulation engine to
compare candidate policies through controlled, traceable experiments.

The hard part was not generating more policy variants. It was deciding which evidence
actually predicted competitive strength. The incumbent could approach a perfect score
against a fixed local opponent panel while its recorded recent episodes showed materially weaker performance.

## Ownership

I built legal-observation feature audits, auxiliary forecasts, controller integrations, paired policy evaluation, chronological protocols, checkpoint recovery, release controls and the evidence publication workflow. Published Python and
notebooks expose the reviewable parts of that work.

The [source and method matrix](docs/public_source_lineage.md) retains credits for upstream controllers and distinguishes my integration/evaluation work, tested mechanisms, rejected transfers and open questions.

## The consequential decision: replace the evaluation reference

The September sprint rebuilt the keeper's recent ladder episodes and required exact
terminal-reward parity before examining changed policies. The reconstructed sample had
18 wins, 10 ties, and 20 losses across 48 episodes: a score of
`(18 + 0.5 × 10) / 48 = 47.9%`.

That result contradicted the apparent strength of the saturated local panel. None of the
final-sprint candidates earned promotion. Evaluation moved to
an older 24-episode development set and a newer 24-episode holdout, with a separate
responsive-opponent safety gate. Historical panel-based promotions are evidence of the
protocol used at the time, not confirmation under the corrected protocol.

Replay fidelity establishes that the incumbent's recorded outcome can be reconstructed.
It does not make counterfactual opponent behavior realistic: a recorded opponent tape
cannot react to a changed agent. That is why fresh responsive games remain necessary.

## Experiments and decisions

| Research direction | Scope in the sprint record | Decision |
|---|---|---|
| Historical source rollback | 234 engine games | Rejected: matched panel scores, lost direct comparisons |
| On-policy economic population | 448 games, two population updates | Rejected: no useful selected interventions |
| Whole-route reference transfer | 428 games | Rejected: best transferred route scored 18.75% versus keeper 87.5% on that screen |
| Public adaptive controllers | 300 games | Rejected: 0% direct head-to-head against keeper |
| Boundary intervention selection | 1,084 branch/calibration results | Hindsight opportunity; learned selection did not generalize |
| Forward-only boundary rules | Same 1,084 results reused | Rejected: only +0.5 forward score units and no rescued losses |
| Native harvest/service recovery | 94 attempted development games | Execution failure; scientific result unresolved |

These counts have different scopes and should not be added into a unique-game total.
The complete decision rules and outcomes are in the
[protocol ledger](docs/research/final_sprint_protocols.md) and
[sprint memo](docs/research/final_sprint_2026-09-30.md).

## Interactive policy and evaluation lab

I built the [Farming Decision Lab](https://alvaro-farming-agent-lab.tartmacaw2.chatgpt.site) as a public, inspectable decision system. A reviewer can play a 24-day season, inspect legal-action masks and compare three generic policies across identical weather and price sequences. Policies receive current and past observations only; the shared seeded environment supports paired comparisons.

The simulator is an authored educational surrogate with four plots, not a reproduction of official Kaggriculture mechanics or a release of the private agent. Its results demonstrate decision flow and evaluation behavior, independently of the historical competition record. [Run and test the lab](docs/REPRODUCIBILITY.md).

## Reliability engineering

Accepted game results were bound to source and engine identities and reused after
interruption. Bounded runtime and resource checks limited experiments, while atomic
checkpoints and compact return bundles preserved progress. Submission intent was recorded
before upload so an uncertain response could be reconciled instead of blindly retried.

A later `BrokenPipeError` exposed another boundary: completed gameplay and optional
post-terminal diagnostics must be validated separately. The prepared recovery runner
checks completion, callback counts, rewards, and identity before requesting optional
telemetry. Its packaged regression checks passed, but a prepared fix is not a completed
competitive experiment.

## Outcome and honest limits

The strongest historical returned rating is **2048.7**. The September 30 snapshot instead
had **1691.0** and **1516.2** in its latest-two scoring pair. These are historical rating observations, separate from the local win/tie score. The sprint did not establish a new project best.

The strongest demonstrated outcome is a more credible selection process: preserve
negative experiments, recognize validation drift, and refuse promotion without the
registered evidence. The public-facing review materials demonstrate that process while
keeping competitive artifacts outside the repository.

Start with the [executed review notebook](notebooks/57_portfolio_review.ipynb), then run the
[synthetic paired-evaluation example](examples/README.md). The
[reproduction guide](docs/REPRODUCIBILITY.md) describes exactly what those checks establish.
