"""Update the second study in canonical notebook 02; preserve study 1 verbatim.

Stable cell IDs make regeneration idempotent. Real fresh-kernel execution follows
this build, so no prewritten outputs or fabricated execution counters are used.
"""

import subprocess
import sys
from pathlib import Path

import nbformat


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith("relationships-")]
    additions = [
        (
            "markdown",
            "intro",
            """## Study 2 · Resource relationships and factorial interventions

The first experiment lost 26 harvested units per full-policy game. This study asks
whether crop value becomes useful only when maturity, shared storage, delivery and
working capital are coordinated. The frozen previous full scheduler is now the opponent.

This is **development feature research, not final model selection**. Four reused seed
clusters, both seats and every 2×2×2 combination are evaluated. `C` = capacity-aware delivery,
`K` = labor-cash reserve and `M` = local collection of capped mature crops. All-off `000`
returns the previous full scheduler exactly. Earlier smoke checks used the registered
design and did not drive parameter tuning. The same initial seed need not produce the
same future shops after different policies consume the shared RNG differently.

See [the fixed design and domain rationale](../docs/relationship_research.md) and
[the completion ledger](../docs/feature_coverage.md).""",
        ),
        (
            "code",
            "load",
            """import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from IPython.display import display
from kaggriculture_research.visuals import show_figure

root = Path.cwd() if (Path.cwd() / 'reports').exists() else Path.cwd().parent
relationships = json.loads((root / 'reports/relationship_research.json').read_text())
games2 = pd.read_csv(root / 'reports/relationship_games.csv', dtype={'arm': str})
effects2 = pd.read_csv(root / 'reports/relationship_effects.csv')
registry2 = pd.read_csv(root / 'reports/relationship_registry.csv')
assert relationships['games'] == len(games2) == 64
assert not relationships['validation_or_holdout_used']
assert relationships['feature_completion_gate'] == 'closed'
display(pd.Series({
    'Full games': len(games2), 'Independent development seed clusters': games2.seed.nunique(),
    'State/history candidates screened': len(registry2),
    'Sampled legal observations': relationships['screening']['sampled_development_observations'],
    'Selected final-model features': 0,
    'Exact conservation checks': relationships['conservation_verified_games']
}, name='Verified scope').to_frame())""",
        ),
        (
            "markdown",
            "design",
            """### Performance against the stronger frozen opponent

Match score (win + half a tie) is the primary local comparison. Coins diagnose how a
decision changes economic output; they are not a leaderboard rating. Each row is eight
games, not eight independent samples. Both seats remain in the same seed cluster.
Arm digits are ordered **capacity / capital / maturity**. No final policy is promoted.""",
        ),
        (
            "code",
            "groups",
            """groups2 = games2.groupby('arm').agg(
    games=('match_score', 'size'), match_score=('match_score', 'mean'),
    mean_coins=('coins', 'mean'), mean_coin_margin=('coin_margin', 'mean'),
    mean_discarded_units=('discarded_units', 'mean'),
    mean_minimum_cash=('minimum_observed_cash', 'mean')
)
display(groups2.round(3))
fig = go.Figure(go.Bar(x=groups2.index, y=groups2.mean_coins, name='Banked coins'))
fig.update_layout(title='Banked coins across the full factorial design',
                  xaxis_title='Capacity / capital / maturity (0 = off; 1 = on)',
                  yaxis_title='Mean final coins · eight games per arm', xaxis_type='category')
show_figure(fig)""",
        ),
        (
            "markdown",
            "effects-explanation",
            """### Isolated components and their interactions

Main effects average ON-minus-OFF across the other factor settings. Pairwise effects
are difference-in-differences; the triple contrast tests whether a pairwise interaction
changes when the third component is switched. These are not regression coefficients.

Intervals below resample **four whole seed clusters** (both seats and every arm together),
2,000 times with a fixed statistical seed. They are descriptive, not confirmatory
significance tests; no multiplicity correction or broad generalization is claimed.
Negative effects are retained in the record. Correlated descriptors are not shuffled
independently to manufacture feature importance.""",
        ),
        (
            "code",
            "effects",
            """display(effects2[effects2.metric.isin(['match_score', 'coins', 'discarded_units'])][
    ['contrast', 'metric', 'effect', 'bootstrap_low', 'bootstrap_high', 'seed_clusters']
].round(3))""",
        ),
        (
            "markdown",
            "conservation-explanation",
            """### Follow the produce, not only the score

Every game verifies `harvested = sold + final held + discarded`. Farm actions happen
before market sales; nightly inventory dumping happens after market sales. A sale later
in the same turn cannot rescue units already destroyed by an overflowing DROP.
Capacity-aware delivery may add travel and delay other tasks, so reduced waste alone
does not establish better performance.""",
        ),
        (
            "code",
            "conservation",
            """accounted = games2.sold_units + games2.unsold_product_units + games2.discarded_units
assert (games2.harvested_units == accounted).all()
display(games2.groupby('arm')[['harvested_units', 'sold_units', 'discarded_units',
    'unsold_product_units', 'ineffective_farm_actions', 'interventions_capacity',
    'interventions_capital', 'interventions_maturity']].mean().round(3))
fig = go.Figure(go.Bar(x=groups2.index, y=groups2.mean_discarded_units, name='Discarded produce'))
fig.update_layout(title='Does delivery prevent harvested produce from being destroyed?',
                  xaxis_title='Capacity / capital / maturity',
                  yaxis_title='Mean units discarded per game', xaxis_type='category')
show_figure(fig)""",
        ),
        (
            "markdown",
            "coverage-explanation",
            """### Feature coverage is not the same as feature usefulness

The bank combines 244 original current-state descriptors with 374 new relationship and
history descriptors. Every fourth callback plus the final callback is profiled; the
history object still sees every consecutive turn. Missing lags have explicit masks.
There are 181 sampled states per game. No turn-level train/test split is made.

Availability, finite values, stable schemas, empirical variation, exact duplicates and
high Spearman dependence are screened. Constant animal-care features mean **missing
policy coverage**, not evidence that livestock is useless. No candidate is rejected
or retained for a final model based merely on these descriptive checks.""",
        ),
        (
            "code",
            "coverage",
            """variable2 = registry2.assign(variable=lambda d: d.distinct_development_values > 1)
coverage2 = variable2.groupby('family').agg(
    generated=('feature', 'size'), variable_in_this_design=('variable', 'sum')
)
coverage2['constant_coverage_gaps'] = coverage2.generated - coverage2.variable_in_this_design
display(coverage2)
display(pd.Series({
    'Exact nonconstant duplicate groups': len(relationships['screening']['exact_duplicate_groups']),
    'Pairs with absolute Spearman >= 0.995': relationships['screening']['high_spearman_pairs'],
    'Policy median milliseconds': relationships['policy_latency_ms']['median'],
    'Policy p95 milliseconds': relationships['policy_latency_ms']['p95'],
    'Full-bank median milliseconds': relationships['sampled_feature_bank_latency_ms']['median'],
    'Sampled full-bank p95 milliseconds': relationships['sampled_feature_bank_latency_ms']['p95']
}, name='Diagnostics').to_frame().round(3))""",
        ),
        (
            "markdown",
            "remaining",
            """### What must happen before feature engineering can close?

The major open families are competitive price-impact scenarios and crop-mix adaptation;
joint harvest/delivery routing; fertilizer acquisition and timing; livestock feed/care,
wheat and fertilizer loops; land-expansion return on capital; and safe temporal/opponent
models. The first study's distance and staffing interventions also need separation.

The new descriptors are available for these studies, but descriptors without policy
activation and controlled ablation are **not completed research**. We still need broader
development seeds and opponents, structured stress states and evidence of diminishing
returns. Validation and holdout remain untouched. Final optimization and submission
remain blocked; this notebook is deliberately still an open research notebook.

Domain methods: the [official interpreter](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture)
defines the actual farming economy. [Finite-horizon inventory research](https://business.columbia.edu/faculty/research/optimal-dynamic-pricing-inventories-stochastic-demand-over-finite-horizons)
motivates inventory × time-to-sale interactions, not a transplant of its pricing model.
[Hooker, Mentch and Zhou](https://arxiv.org/abs/1905.03151) motivate caution with
importance methods that destroy dependence. Here we use controlled policy interventions.""",
        ),
    ]
    for kind, identifier, source in additions:
        cell = (
            nbformat.v4.new_markdown_cell(source)
            if kind == "markdown"
            else nbformat.v4.new_code_cell(source)
        )
        cell.id = "relationships-" + identifier
        notebook.cells.append(cell)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    # Lint/format generated cell sources before execution, not after publication.
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", str(path)], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], check=True)
    print(f"Updated canonical notebook: {len(notebook.cells)} cells; fresh execution required")


if __name__ == "__main__":
    main()
