# Current outcome ledger

**Latest published evidence snapshot: 2026-09-30T02:31:37Z**

| Milestone | Evaluation | Result | Decision |
|---|---|---|---|
| Active scoring pair | authenticated latest-two accepted submissions | keeper **1691.0** (`56656845`), labor **1516.2** (`56598411`) | preserve keeper until a new candidate clears real-ladder holdout + safety |
| Historical timing reference | authenticated completed submission | **2048.7** | historical benchmark, outside current latest-two pair |
| Highest returned leaderboard row | authenticated paginated leaderboard export | **3084.1** | reference frontier only; export not exhaustive |
| Late-layer source ablation | 234 official-engine games | prefixes matched panel score but lost direct H2H | **REJECTED_SCREEN** |
| On-policy economic population | 448 games / 2 updates | selected policy produced no useful interventions | **TRAINING_REJECTED** |
| Coherent Kaito/recent-leader route frontier | 428 games | keeper **87.5%**; best transferred route **18.75%**; 0% direct H2H for all route candidates | **SCREEN_REJECTED** |
| Current public adaptive frontier | 300 games | Thomas candidates **25%, 16.7%, 16.7%**, all 0% direct H2H vs keeper | **SCREEN_REJECTED** |
| Replay-aligned ladder validator | 48 recent keeper episodes | exact replay fidelity; keeper **18 W / 10 T / 20 L = 47.9%** | validator corrected |
| Fixed-policy ladder comparison | older 24 real keeper episodes | keeper **45.8%**; all fixed alternatives worse overall | **NO_FIXED_POLICY_IMPROVEMENT** |
| Boundary selector | 1,084 calibration/branch games | hindsight oracle about **+7 score units**, but learned tree made no stable rescue decisions | **INNER_VALIDATION_REJECTED** |
| Rolling boundary-rule CV | 1,084 branch results reused; zero new games | best forward rule **+0.5 units**, zero rescued losses | **ROLLING_CV_REJECTED** |
| Native harvest/service attempt | 94 attempted development games | post-terminal diagnostics transport raised `BrokenPipeError` after completed gameplay | **EXECUTION FAILURE**; no scientific decision |

## Current decision

The old fixed-opponent panel is no longer the primary promotion surface. It materially
overstated the keeper's live strength.

All new keeper-centered research must first pass exact replay reconstruction and then use
chronological development/holdout logic on recent ladder episodes. Reactive-opponent safety
remains a separate gate because recorded opponent tapes cannot respond to a changed policy.

Fixed expert replacement, whole-route transfer, public adaptive controller transfer, and
low-capacity boundary borrowing are closed under the tested protocols.

The current registered hypothesis is **native harvest/service recovery on the exact keeper**.
The first attempt failed operationally after gameplay, so it remains scientifically untested.
The repaired artifact changes transport ordering only and does not inherit a favorable result
from the failed attempt.

## Final-sprint execution ledger

Corrected cumulative project/chat tally at this checkpoint:

- total top-level attempts: **75**
- successful intended executions: **43**
- execution failures: **28**
- authorization stops: **1**
- other controlled stops: **3**
- tracked successful active compute: **$20.7994**
- tracked failed active compute: **$1.0859**
- tracked stopped active compute: **$0.5387**
- tracked active compute total: **$22.4239**

These figures are experiment-level estimates, not account-wide AWS billing totals.

## Public provenance / boundary

AWS/SageMaker remains canonical. The repository publishes aggregate outcomes, executed
notebooks, validation utilities, protocols, and reproduction manifests.

Raw replay corpora, credentials, private checkpoints, Kaggle submission archives, and
third-party controller source remain outside the repository.

See:

- `reports/final_sprint_2026-09-30.json`
- `reports/final_sprint_reproduction_manifest.json`
- `notebooks/56_final_sprint_ladder_alignment.ipynb`
- `docs/research/final_sprint_2026-09-30.md`
- `docs/research/final_sprint_protocols.md`
