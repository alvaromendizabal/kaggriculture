# Research round 11: cross-worker route opportunity

## Research question

Can a representation of the alternatives available to **other workers on the same farm** preserve useful route choices that independent top-eight filtering discards, improving final-day outcomes with the allocation algorithm unchanged?

The recently completed sale-timing study produced a +42-coin improvement in one of three primary development comparisons and zero local-match changes. It is preserved as a provisional baseline in both arms. It is not a leaderboard gain or proof of generalization. See RESULTS_REVIEW.md for the exact source results.

## Source-derived mechanism versus new hypothesis

At baseline commit `7194116dfc92a8663139611233b5a221dad431a4`, `src/kaggriculture_terminal/routing.py` constructs routes with zero, one, or two collections, possibly watering before a harvest, then a deposit. It retains eight non-PASS routes per worker, protects a direct deposit, appends PASS, and calls an exact resource/capacity-constrained allocator. Routes are ranked independently by estimated sale value minus eight coins per planned action. The allocator is exact over **retained** choices, not over every feasible game plan.

This is a source finding. The conjecture is that several workers can have high-ranked routes to the same resources, while lower-ranked but complementary alternatives are discarded. Having a strong exact allocator does not recover alternatives missing from its input. Notebook 11 does **not** assume this occurs in the saved states: the screen must establish incidence, static contribution and first-command changes before any simulator continuation runs.

Primary conceptual reference: Aziz et al., *Multi-Robot Task Allocation — Complexity and Approximation*, AAMAS 2021, https://arxiv.org/abs/2103.12370. It studies assignment with costs and budgets, supporting the need to represent coupled access rather than isolated task value. Its multi-robot-task model is different from this game. It does not prove that the proposed heuristic, features, or agent are competitive.

Official mechanics: https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py . The runtime requires the reviewed interpreter SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`, not an unpinned download. Code is the mechanics authority where documentation differs. No web resources are fetched by the delivered runner.

## New representation and intervention

For route r of worker i, the standalone utility u(r) is the **unchanged** baseline route value minus the unchanged action penalty. Let M_j be worker j's original retained menu, including PASS.

Define independent-worker pressure:

`pressure(i, r) = sum over j != i [max(u(q) for q in M_j) - max(u(q) for q in M_j if resources(q) do not intersect resources(r))]`.

Every menu contains PASS, so the compatible alternative is defined. Each term is nonnegative. The new route-admission descriptor is `relative_utility = u(r) - pressure(i,r)`. The coefficient is one because both terms have the same conditional coin-equivalent units. It is fixed, not fitted or tuned to these episodes. **Other workers** are friendly workers, not the opposing player.

The pressure is an approximation: the other workers' independent favorite routes may themselves overlap, it uses their originally retained alternatives rather than all possible alternatives, and the price scenario excludes unknown future trades. It must not be called a realized joint loss, a calibrated forecast, or a valid shadow price for the full game.

The candidate menu keeps each worker's incumbent assignment route, keeps its direct deposit when available, fills the remaining non-PASS slots by relative utility, sorts deterministically, then appends PASS. The non-PASS cap stays eight. The exact joint objective, allocation implementation, capacity constraint, task-exclusion rules, route pool, and action-penalty coefficient do not change. With the incumbent still jointly feasible, the static objective cannot worsen; the runner asserts this rather than assumes it.

Only a strict improvement in the original `(joint_utility, -joint_work)` key can change the selected assignment. Equal-key reordering is forced back to the incumbent, preventing gratuitous tie changes. This static safeguard does **not** imply a better real trajectory. Future markets, replanning, inventory interactions and the limited route model can reverse the apparent gain.

## Candidate descriptors

Sixteen numeric fields are emitted per candidate route, with an explicit dictionary: work, units, resource count, solo value, solo utility, original rank, original admission, incumbent status, direct deposit, competing-worker count, preferred-resource conflicts, summed and maximum opportunity cost, mean compatible alternative, relative utility, and original exclusion. Some describe the previous selection boundary; they are diagnostics available at decision time, not outcome labels. The single new action-changing family is cross-worker opportunity cost at menu admission.

The number of route rows depends on the observed tasks and may be much larger than the number of state-level columns. No assertion of hundreds or thousands of useful features is made. The static feature count is 16; route instances are not 16 new independent predictors per state. Registry nonzero fractions and variation counts are activation statistics, not predictive importance or evidence to retain every column.

## Information contract and leakage prevention

The callback receives the same legal own-view fields as the reviewed agent. All own workers, their own inventories, public farm tasks and public prices are available before action. The actor never receives seed, episode identity, rewards, future observations, opponent private inventory, or the evaluator's paired state. It ignores extra replay metadata through the existing canonical projection.

Feature rows carry seed/seat/step/source columns for grouped auditing; those are metadata, not inputs to the feature function or fitted-model columns. No model is fitted. Outcome tables remain separate from route features. No validation or holdout is opened. The use of already-studied development states is explicit; screening is adaptive research, not fresh validation.

Frozen mechanics and source files remain unchanged. The new code deliberately inherits the old callback's admission restriction of at most three hired hands per farm; it rejects broader observations rather than truncates them. Previous variable-workforce extraction success did not solve this full-callback restriction. Broad-workforce deployment remains a separate required workstream.

## Stage A: bounded activation screen

Verify notebook 10's exact report, output hashes, source fingerprint, imported dependency hashes, original repository commit, runtime and pinned engine. Verify all ten restored objects. Use only the three coordinated source episodes, 23 final-day observations each: 69 states in total. The missing original eighth episode stays missing.

On every state, recompute the candidate callback, the complete notebook-10 reference callback, and the frozen `routing.menus`. Require exact agreement between the reconstructed original menu and the frozen menu, including metadata, and exact reference-action agreement before accepting feature intervention diagnostics. Thus changes cannot be attributed to an accidental replacement of the candidate generator or reference policy.

The screen logs real complete-callback wall time, not a synthetic clock. It has a 90-second stage cap and a 500 ms per-callback gate. Each fully processed source episode is a checksummed, read-back-verified checkpoint. If no first command changes, STOP_NO_ACTION_ACTIVATION is a useful negative result: do not run a bigger experiment just because route scores moved.

## Stage B: one paired endpoint pilot, not automatic scale-up

When the screen activates, select the first activated primary key in ascending seed/seat order, **without inspecting outcomes**. Before that primary pair, run the fixed seed-1601/seat-0 sequential source as a disabled-family/no-change control. At most four branches are evaluated: two control and two opportunity branches, each 23 linked decisions. The maximum is 92 new research interpreter transitions and zero new full seasons.

Both arms use the final-sale gate from notebook 10. Earlier same-state market orders and non-sale/hiring orders must match. On the final callback, the same sale function is applied to each arm's resulting inventory; different sales resulting from different farm actions are downstream feature effects, not a separately changed selling rule. A same-state full reference callback verifies the direct attribution rules each turn.

The control reproduces original recorded transitions through step 717 and notebook-10 endpoint metrics at step 718. The opponent is recomputed each turn from its own legal view; it can react to the changed trajectory. Branches advance continuously and are never reset to original states after a cash effect. Endpoints include own coins, opponent coins, coin margin, local match score and unsold products. Every completed branch is written atomically, checksummed and read back before the next branch.

The stage cap is 120 seconds, with the same 500 ms callback gate. The negative control must be exactly unchanged. Negative cash, margin or match change stops this family. Null or unactivated outcomes do not authorize expansion. A positive result is only PROMISING_SINGLE_DEVELOPMENT_PAIR_NOT_VALIDATED. Additional source groups, diverse opponents and fresh development/validation partitions remain necessary before promotion. No confidence interval or turn-level significance claim is justified here.

## What still separates this study from a competitive agent

This round tests menu representation, not an ensemble or a new model. It cannot apportion the full leaderboard gap among features, planning, implementation and validation. There is still no verified submission rating to compare with the user-supplied 3140.0 target.

Major open families remain:

| Family | Missing question | Next evidence required |
|---|---|---|
| Broad workforce and hiring | What is the marginal realizable value of another worker after expiry and escalating hire cost? | Full-callback coverage, all-worker action alignment, activated hiring comparisons |
| Production timing | Which crops/animals can mature, be maintained, harvested and converted to cash in time? | Earlier-season causal states, maturity/refresh boundary tests, cash endpoints |
| Maintenance/inputs | When are watering, feed, fertilizer and care worth their labor and inventory opportunity costs? | Mechanistic counterfactuals and family-level interventions |
| Land and working capital | Does added land provide attainable production after travel, service and cash constraints? | Equal-rule investment comparisons with ledger attribution |
| Causal market context | Which public demand, scarcity and competing supply histories change attainable value? | History reset/availability tests and genuinely different opponents |
| Beyond terminal two-task menus | What is lost through replanning or the limited collection horizon? | Distinct hypothesis and controlled planner/representation ablations |

A poor result here is a reason to stop or revise this family, not to spend many more runs on cosmetic terminal changes. Feature engineering remains open until realistic high-value avenues have evidence, not until a feature-count target is reached.
