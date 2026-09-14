# Feature engineering remains open

## The problem is action quality, not feature count

Kaggriculture is a finite-horizon competitive farming economy. The simulator awards the game according to final banked money, not the number of crops grown, stored units or columns engineered. A useful representation must change attainable decisions under legal information and improve the relevant game outcomes. The reported 3140.0 benchmark is a leaderboard-rating target, not 3140 banked coins or an RMSE target. No submission score has been verified for this project.

The current evidence does not establish that all performance loss is attributable to features rather than policy/search/validation. It does establish a serious representation gap and an actual runtime bottleneck. Prioritize the representation, but measure all those effects honestly.

## Starting evidence, not new results

The project has a substantial provisional bank already: Study 6 reported 1,579 supported candidates, while a project union of 1,621 included 42 earlier cash bounds invalidated by own wheat purchases. Those counts are not feature-selection evidence. Study 7 added 53 staffing candidates and was halted after seven accepted games; the eighth exceeded the 500 ms full-callback gate before the rejected outcome/maximum latency was preserved. Three completed paired comparisons changed local match score by zero. The incomplete pair cannot be dropped to make a complete-study claim.

A later 39-descriptor audit reused 161 saved observations: 28 varying, 11 constant, with 161/161 base-assignment parity. The study measured feature coverage, not an official-metric improvement. The more decisive latest finding is a schema boundary: the engine demonstrated 12 hired hands while the frozen extractor supported only three, and both observer views could be rejected. Twelve is a demonstrated case, **not a discovered maximum**. Merely increasing the hard-coded cap to twelve is not a robust solution.

## Five bounded investigation rounds

### Round 1 · Workforce coverage and a scale-safe representation

**Hypothesis:** a variable-size, observation-safe labor representation will eliminate legal-state coverage failures and expose profitable tasks that fixed worker slots cannot reliably express.

Keep frozen Study 7 sources immutable. Build a forward-only extractor with permutation-invariant global summaries and worker-indexed action features. Aggregate actual available work, remaining contract/expiry horizons where exposed, travel/access distributions, task compatibility and resource availability. Do not invent worker skills or tenure fields that are absent from the pinned engine.

The worker/action mapping must be permutation-equivariant even when global summaries are invariant. Swapping two worker records should not change global values, and corresponding actions should follow the swapped workers. Never truncate the public opponent's workforce just to make the own-player extractor fit.

**First gate:** zero-game schema/fixture checks on both seats, 0/1/3/4/12 hired hands and larger synthetic lists; immutable input; public-clock handling; finite/deterministic output; no forbidden keys; no exponential exhaustive joint enumeration. Record full callback wall time, not just a fast subcomponent. Persist rejected inputs and measured maxima before applying the gate.

**Conclusion allowed:** legal observation support and runtime acceptance. **Conclusion not allowed:** proven competitiveness.

### Round 2 · Opportunity cost of the next action

**Hypothesis:** task-relative values and the opportunity cost of the first action will matter more than additional absolute storage descriptors in the states already observed.

Investigate best-versus-runner-up feasible value, marginal loss when a worker/resource becomes unavailable, task overlap across workers, shared-access conflicts, travel/service/deposit burden and the cash value of the next-best alternative. Keep planning approximations explicit. A retained-menu optimum is not a global optimum; hypothetical capacity sensitivities are not necessarily purchasable actions.

Hold hiring, wages, feeding, fertilizer and market rules equal between control and treatment. Change only the registered task-choice feature family. Require observable action divergence in its activation window before paying for a pilot. If no actions change, diagnose nonactivation rather than running more games.

Simple bipartite assignment can provide a useful lower-complexity reference only when its independence assumptions hold. It does not automatically solve route, shared inventory, capacity, horizon or multi-step conflicts.

### Round 3 · Production that can actually become banked cash

**Hypothesis:** deadline-aware marginal value should reflect the whole path from service to maturity, collection, movement, deposit and sale.

Investigate critical-path slack, realizable remaining yields, labor-adjusted maturation value, final profitable feeding/watering windows, harvest-backlog risk and unsold work-in-progress. Use the actual pinned horizon (719 action rounds/720 states in this project), not a prose approximation of 720 decision rounds. Engine boundary fixtures should cover the last feasible action and one step too late.

Re-test terminal routing under equal staffing: the earlier winning liquidation package did not isolate a multiworker assignment benefit. Pair added/removed deadline features while holding all other behavior constant.

### Round 4 · Joint liquidity, sale curves and investment alternatives

**Hypothesis:** cash tied up in maintenance or delayed-return production changes the marginal value of workers, land, herd/crop mix and market actions.

Investigate exact nonlinear incremental sale value, wage/maintenance cash reserve, labor-adjusted investment payoff before the terminal horizon, opportunity cost of buying feed, and stress-regime activation. Existing cash bounds that excluded own wheat purchases must remain marked unsupported under those purchases; do not silently reuse them.

Test mechanics and accounting first. Activate genuine capital-stress and mixed-production states; earlier never-activated rules provide no evidence of utility. Evaluate one family at a time rather than confounding several investments with a new scheduling policy.

### Round 5 · Public opponent history and interaction regimes

**Hypothesis:** legal public history and uncertainty about competing supply can improve decisions under opponents that change market and task opportunities.

Investigate public production timing, interval-valued rival supply exposure, shared demand pressure, revealed crop/herd/hiring behavior, market-price pressure and same-turn sale risk. Never read evaluator-only rival inventory or future realized actions into the agent feature function. Maintain histories within a game and reset them between games.

Use at least two meaningfully distinct, source-identified opponent policies and both seats; verify that opponents actually induce different task/market distributions. The current narrow, related reference population is insufficient for a ladder-strength claim. External weather, satellite and real-world agronomy data are not automatically useful to a rules-driven simulator; admit external signals only if rules allow them and a simulator mechanism connects them to observations and outcomes.

## Common experiment contract

Before each new policy study, inventory all prior development and CI seeds. Seed 1601 is already development data; do not call it untouched. Reserve a truly uninspected final evaluation set and do not repeatedly select features against it.

Register the exact engine/source/config/opponent hashes, feature availability contract, activation window, primary paired outcome and stopping criteria. Any fitted thresholds or feature screening use development/training episode groups only. Individual turns from one game are not independent validation samples.

Start with pure-function tests and at most a few mechanics transitions, then a saved-observation audit, then a single bounded callback check. Only a passing candidate proceeds to one game per checkpoint and a small explicitly capped pilot. The initial illustrative pilot is two fresh development seeds × two seats × two distinct opponents × control/treatment = 16 games, executed one at a time. It is a directional pilot, not sufficient evidence for final selection. Do not choose seeds or launch this pilot until coverage, runtime and action-activation gates pass.

Every accepted game must have durable source-locked evidence. Save failed or rejected payloads and exact timings too. An acceptance failure is an outcome, not a reason to rerun until it disappears. Before a second batch, inspect paired outcome, coin margin, unsold goods, ineffective actions, runtime and mechanism activation by seed/opponent block. Report the complete attempted denominator, including failures.

Stop for nonactivation, invalid information use, deterministic accounting errors, unacceptable callback latency or clearly dominated results. Keep a family only when controlled contribution and grouped stability justify it. Counterfactual state coverage is not a substitute for policy ablation. Feature counts, descriptive variance and green CI do not establish predictive value.

## What happens immediately after workspace readiness

The next actual implementation milestone is **Round 1's forward-only observation contract and workforce-support tests**, followed by full-callback acceptance of the exact faster candidate. It is not another unbounded simulator run and it is not an ensemble study. This package contains recovery and evidence visualization, not that new extractor or a new feature-value experiment. No feature family is declared complete.

## Research basis and limits

- Official simulator mechanics: https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture . The live upstream README may change; executable experiments must use the project's pinned 1.32.7 engine bytes.
- Current project plan: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/docs/feature_next_milestone.md
- Current coverage ledger: https://github.com/alvaromendizabal/kaggriculture/blob/7194116dfc92a8663139611233b5a221dad431a4/docs/feature_coverage.md
- Aziz et al., *Multi-Robot Task Allocation—Complexity and Approximation*, AAMAS 2021: https://arxiv.org/abs/2103.12370 . Motivates studying coupled allocation and budget constraints; its formal task is not this game and proves no Kaggriculture feature gain.
- Zaheer et al., *Deep Sets*, NeurIPS 2017: https://arxiv.org/abs/1703.06114 . Motivates permutation-aware variable-size representations. Using that representation principle does not require switching this project to a neural model.
- SciPy's linear assignment contract: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html . Useful only where the represented constraints fit bipartite assignment.

No winning solution was verified in this milestone. No claim is made that a specific proposed family is the competition's most predictive feature family. These are prioritized, mechanism-based hypotheses to test against the project's actual gaps.
