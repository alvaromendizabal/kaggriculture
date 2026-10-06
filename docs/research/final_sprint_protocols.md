# Final-sprint registered protocol ledger

This document preserves the decision rules used during the September 29–30, 2026
Kaggriculture sprint. It is a public research ledger, not a release of third-party agent
source or private competition artifacts.

All competitive games use Kaggle Environments 1.32.7. Candidates are paired on the same
seeds and both seats. A candidate is never promoted because of mean bank alone: win/tie
score is primary, chronological holdouts remain untouched until their registered gate, and
negative experiments are retained.

## 1. Late-layer source ablation

**Hypothesis.** Seven late fixed-sell closure layers appended after the submitted
controller's last productionized compact closure might be responsible for live weakness.

**Candidates.** Exact historical prefixes at Step1002, Step961, and Step953.

**Screen.** Current + three prefixes + labor against five fixed opponents, four fresh seed
groups, both seats, plus direct candidate-versus-current games.

**Screen gate.** At least +5 percentage points over current, nonnegative gain over labor,
at least 62.5% direct score against current, and registered seat/family non-regression
limits.

**Decision.** `REJECTED_SCREEN`. The prefixes matched the keeper on the panel but lost
directly, so the rollback direction was closed.

## 2. On-policy economic population

**Hypothesis.** A small state-dependent economic overlay trained by complete-game outcomes
could improve sale/buy/hire decisions while preserving the parent's farm and movement logic.

**Training.** Three bounded populations, nine policy vectors per generation, complete-game
fitness, later generations exposed to earlier population winners.

**Release gate.** The learned policy had to change actions, improve training outcomes, then
survive a separate screen and an untouched confirmation.

**Decision.** `TRAINING_REJECTED`. The selected policy converged to making no useful
interventions.

## 3. Coherent public/recent route frontier

**Hypothesis.** Large gains in strong public work were caused by coherent full-season
continuations rather than isolated constants.

**Candidates.** Exact Kaito v27, route-only and no-repair ablations, plus two complete
recent-leader-derived observed routes. Routes begin at turn zero; no unrelated midgame
suffix is spliced into the keeper.

**Screen.** Five candidates + current + labor, six opponents, four fresh seeds, both seats;
direct H2H against controls.

**Confirmation gate.** One frozen winner only; at least +5 points over both controls,
positive paired seed-bootstrap lower bounds, gains in both seed blocks, no registered
seat/family regression, and at least 62.5% direct score against both controls.

**Decision.** `SCREEN_REJECTED`. The keeper scored 87.5% on the panel; the best
transferred route scored 18.75% and every candidate scored 0% direct H2H against current.

## 4. Newer public adaptive frontier

**Hypothesis.** More recent public agents with state/routing logic might transfer better than
fixed routes.

**Candidates.** Thomas 2945 Farm V2, 95.5% replay router, and 93.8% public-state router,
acquired from immutable public identities and parity-tested before screening.

**Decision.** `SCREEN_REJECTED`. Scores were 25%, 16.7%, and 16.7%, with 0% direct H2H
against the keeper. Public-policy transfer was closed as a shortcut.

## 5. Real-ladder alignment protocol

**Problem.** The old fixed opponent panel had saturated: the live keeper appeared nearly
perfect locally while remaining far weaker on the actual ladder.

**Registered correction.**

1. Acquire recent public ladder episodes for keeper 56656845.
2. Require exact terminal-reward reproduction before interpreting any counterfactual.
3. Sort chronologically.
4. Use an older 24-episode development set and a newer 24-episode untouched holdout.
5. Compare fixed controllers on the same recorded opponent streams.
6. Score win/tie/loss first; report rescued keeper losses and sacrificed keeper wins.

**Fidelity result.** Exact replay reproduction passed. Across 48 recent keeper episodes the
keeper had 18 wins, 10 ties, and 20 losses: 47.9% score rate. The older 24 development
episodes were 9 wins, 4 ties, and 11 losses: 45.8%.

**Decision.** `NO_FIXED_POLICY_IMPROVEMENT`. Fixed alternatives were globally worse,
although several rescued isolated keeper losses.

## 6. Keeper-centered boundary selector

**Hypothesis.** A globally weaker expert may still be useful for one strategic segment in a
specific keeper failure state.

**Boundaries.** Steps 144, 168, 216, 288, 360, 432, 504, 576, and 648.

**Action.** Temporarily borrow one alternate controller for 72 turns, then return to the
keeper. Both subagents receive observations throughout so internal state remains aligned.

**Alternates.** timing_current, labor, shop_router_v7, v38_smarter_feed, and
sparse_shop_hybrid.

**Development search.** 24 real-ladder development episodes × 9 boundaries × 5 alternates,
plus calibration: 1,084 accepted official-engine results.

**Decision.** `INNER_VALIDATION_REJECTED`. A hindsight oracle showed roughly +7 score
units across the 24 development episodes, but the first small learned selector did not
generalize.

## 7. Forward-only boundary-rule CV

The expensive branch table above is reused rather than replayed.

**Rolling folds.**

- episodes 1–12 → validate 13–16;
- episodes 1–16 → validate 17–20;
- episodes 1–20 → validate 21–24.

**Policy classes.** Fixed segment, one-threshold segment, and at-most-two-rule decision
list. Runtime may trigger at most one 72-turn intervention per game.

**Forward gate.** At least +1.5 total validation score units, at least one rescued loss,
at most one sacrificed win, and no four-episode fold worse than −0.5.

**Decision.** `ROLLING_CV_REJECTED`. The strongest threshold and two-rule families
reached only +0.5 forward score units and rescued no losses. The newest-24 holdout remained
untouched.

## 8. Native harvest/service recovery

**Hypothesis.** The keeper leaves productive worker service opportunities unused. A
project-authored joint-transition layer may safely redirect only idle/ineffective worker
actions while leaving the keeper's farm plan, movement plan, purchases, market policy, and
terminal strategy intact.

**Pre-registered variants.**

- harvest_always;
- harvest_behind;
- harvest_close;
- harvest_late_close.

**Development gate.** On the older 24 ladder episodes: at least +2 score units, at least
two rescued keeper losses, at most one sacrificed keeper win.

**Holdout gate.** The same gate on the untouched newest 24 after exact keeper replay
fidelity passes again.

**Reactive safety.** Fresh responsive games against four recent registered source
opponents plus direct H2H with the keeper. Candidate panel performance must remain within
five percentage points of keeper and direct H2H must be at least 37.5%.

**First execution.** Operational failure, not a scientific rejection. The official game
finished, but an inherited diagnostics transport queried an already exited process and
raised `BrokenPipeError`.

**Recovery rule.** Establish 720 engine states, DONE/DONE status, 719 callbacks/player,
finite rewards, and seed identity before requesting optional post-terminal telemetry.
Missing telemetry from an exited external process cannot invalidate a completed game; a
transport failure while the process is still alive remains fatal.

No scientific claim about native harvest/service recovery is published until the repaired
artifact completes this protocol.

## Shared promotion and release discipline

- AWS/SageMaker is canonical.
- Raw replays and accepted game checkpoints are immutable/reused.
- A later failure does not force recomputation of accepted games.
- No gate is relaxed after results arrive.
- One frozen nominee enters confirmation.
- Latest-two Kaggle scoring slots are rechecked immediately before a write.
- At most one qualifying submission is written per milestone.
- Upload intent is journaled before submission; uncertain outcomes are reconciled rather
  than blindly retried.
- Raw replay corpora, credentials, private checkpoints, third-party controller source, and
  submission archives are not public repository contents.

For machine-readable outcomes see
`reports/final_sprint_2026-09-30.json`. For clone-time verification see
`scripts/verify_final_sprint.py`.
