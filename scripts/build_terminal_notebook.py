"""Extend the canonical feature notebook while preserving its first 28 code sources."""

import subprocess
import sys
from pathlib import Path

import nbformat

from kaggriculture_research.artifacts import digest

PRIOR_SOURCE = "52760a1a7e2e54f6c3aa41d7679d28494127313537cc81a4cb5df2b4a4c2979f"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith("terminal-")]
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if len(cells) != 28 or digest([c.source for c in cells]) != PRIOR_SOURCE:
        raise ValueError("Preserved earlier notebook source changed")
    additions = [
        (
            "markdown",
            "intro",
            """## Study 6 · Finite-horizon service and joint liquidation

The last production refresh precedes the final day. Feeding after it cannot protect
an animal or create goods before scoring. Collection also has a dependency: goods
must reach the shed and sell before the final action. This study adds explicit
refresh feasibility, inventory opportunity and joint worker-route features.

The three arms share the same policy through decision 695. **feed** changes the
final-day feed gate and wheat reserve; **joint** additionally replaces final-day
work with bounded collection/delivery assignment and immediate liquidation.
Routes can include WATER → HARVEST → DROP, use distinct resources, and respect
joint shed capacity. Exact selection is only over a pruned two-collection menu;
this is not global season-long optimization.

The [registered protocol](../docs/terminal_protocol.md) links the official engine,
finite-horizon RL research, and task-allocation research. Results below use four
fresh development seeds, both seats, and two fixed opponents: the preceding
fertilizer policy and an existing MELON specialist. Validation and holdout are
unused. The [findings](../docs/terminal_research.md) record decisions and gaps.""",
        ),
        (
            "code",
            "load",
            """from terminal_plots import show_coin_effects, show_scores
from verify_terminal_report import verify as verify_terminal_report

terminal6 = json.loads((root / 'reports/terminal_research.json').read_text())
games6 = pd.read_csv(root / 'reports/terminal_games.csv')
effects6 = pd.read_csv(root / 'reports/terminal_effects.csv')
registry6 = pd.read_csv(root / 'reports/terminal_registry.csv')
diagnostics6 = json.loads((root / 'reports/terminal_diagnostics.json').read_text())
assert len(games6) == 48 and terminal6['identical_preterminal_blocks'] == 16
display(games6.groupby(['opponent', 'arm'])[['match_score','coins','coin_margin',
    'terminal_feed','residual_product_units']].mean().round(3))
show_scores(games6)""",
        ),
        (
            "markdown",
            "inference",
            """### Paired effects and mechanisms

Coin differences support the mechanism analysis; the primary metric remains wins
plus half a tie. The bootstrap keeps both seats and opponents inside each seed.
With four seed clusters, intervals are descriptive. Saturated or identical seed
score differences can give zero-width intervals without proving population certainty.
Any gains against the related fertilizer reference need confirmation against
independent competitive agents. Hired hands expire overnight: the joint arm has
one worker because it does not rehire on the final day. Its effect therefore tests
liquidation plus staffing; it cannot establish a benefit from multiworker assignment.
Multiworker route descriptors are measured on the baseline/feed trajectories.
Receding-horizon route choices also affect sale
timing and the opponent's market, so a coin difference is not a pure feed price.""",
        ),
        (
            "code",
            "effects",
            """display(effects6[(effects6.opponent == 'pooled') & effects6.metric.isin(
    ['match_score','coins','coin_margin','terminal_feed','residual_product_units'])][
    ['contrast','metric','effect','bootstrap_low','bootstrap_high']].round(3))
show_coin_effects(effects6)
display(pd.DataFrame(diagnostics6['groups']).set_index(['opponent','arm']).round(3))""",
        ),
        (
            "markdown",
            "coverage-note",
            """### Feature coverage remains distinct from predictive selection

The 79 new candidates extend the jointly screened bank to 1,579. The project union
is 1,621; 42 earlier cash features still have an invalid contract for own purchases.
Route features are explicitly inactive before the final day. Constants, duplication
and runtime identify coverage or representation limits; they do not select a final
model. Prices in route features are current no-opponent-sale scenarios, not forecasts.""",
        ),
        (
            "code",
            "coverage",
            """fresh6 = registry6[registry6.feature.str.startswith('terminal.')]
display(fresh6.assign(varying=lambda d: d.distinct_development_values > 1).groupby(
    'family').agg(generated=('feature','size'), varying=('varying','sum')))
display(pd.Series({'Jointly screened': len(registry6),
    'Varying': (registry6.distinct_development_values > 1).sum(),
    'Constants': len(terminal6['screening']['constant_features']),
    'Exact duplicate groups': len(terminal6['screening']['exact_duplicate_groups']),
    'High-correlation pairs': terminal6['screening']['high_spearman_pairs'],
    'Final-day policy p95 ms': diagnostics6['terminal_policy_latency_ms']['p95'],
    'Final-day feature assembly p95 ms': diagnostics6['terminal_feature_assembly_ms']['p95']},
    name='Coverage and local runtime').to_frame())
print(diagnostics6['timing_scope'])""",
        ),
        (
            "markdown",
            "audit-note",
            """### Independent audit and recovery

Every saved action and sampled feature vector is replayed. Evaluator-only private
transitions check conservation and the public stock bounds; hidden truth never
enters policy inputs. Sixteen paired blocks must have identical preterminal hashes.
Each game has an atomic checksum envelope and a private versioned S3 checkpoint.
A real download-and-reuse probe demonstrates recovery with zero new simulation.

All 28 earlier code cells are preserved exactly. This extension has its own genuine
execution receipt. Feature research remains open; larger menus, mixed inventories,
fertilizer/water continuation, season-long assignment, land/capital stress and
unrelated opponents require further bounded tests.""",
        ),
        (
            "code",
            "audit",
            """evidence6 = verify_terminal_report(root)
audit6 = json.loads((root / 'reports/terminal_integrity.json').read_text())
assert audit6['complete'] and audit6['mismatches'] == 0
assert (games6.harvested_units + games6.collected_units + games6.bought_units ==
    games6.sold_units + games6.fed_units + games6.applied_units +
    games6.discarded_units + games6.terminal_units).all()
display(pd.Series(audit6['counts'], name='Independently audited').to_frame())
display(pd.Series(evidence6, name='Evidence gate').to_frame())""",
        ),
    ]
    for kind, identifier, source in additions:
        make = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cell = make(source)
        cell.id = "terminal-" + identifier
        notebook.cells.append(cell)
    nbformat.write(notebook, path)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], check=True)
    cells = [c for c in nbformat.read(path, as_version=4).cells if c.cell_type == "code"]
    if len(cells) != 32 or digest([c.source for c in cells[:28]]) != PRIOR_SOURCE:
        raise ValueError("Earlier notebook code changed")
    print("Preserved 28 code sources; appended four terminal-study cells")


if __name__ == "__main__":
    main()
