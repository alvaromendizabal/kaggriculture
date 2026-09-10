"""Append the market study to canonical notebook 02 without changing earlier code."""

import subprocess
import sys
from pathlib import Path

import nbformat

from kaggriculture_research.artifacts import digest


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith("markets-")]
    preserved = digest([c.source for c in notebook.cells if c.cell_type == "code"])
    additions = [
        (
            "markdown",
            "intro",
            """## Study 3 · Post-decision markets and delivery opportunity cost

This preregistered 2×2 study uses **six fresh development seeds**, both seats and four
arms (48 games). The frozen baseline is the maturity policy `001`; the opponent is
the previous capacity-plus-maturity policy `101`. Digits mean **delivery / market timing**.
Arm `00` is exactly the frozen baseline. No validation or holdout seeds are used.

The mechanisms are not a learned price forecast: known town consumption is combined
with a visible rival-harvest stress envelope, fixed 50:50 scenario weighting and an
exhaustive integer split of current stock between selling now and a later sale.
Holding lasts at most four callbacks and stops before the nightly deposit/final sale.
Delivery is priced against foregone crop work, with local harvest/watering safeguards.

Read the [preregistered design](../docs/market_research.md) and
[cited domain and modern-method review](../docs/domain_research.md). These are feature
interventions, not final optimization, calibrated probabilities or a leaderboard score.""",
        ),
        (
            "code",
            "load",
            """markets = json.loads((root / 'reports/market_research.json').read_text())
games3 = pd.read_csv(root / 'reports/market_games.csv', dtype={'arm': str})
effects3 = pd.read_csv(root / 'reports/market_effects.csv')
registry3 = pd.read_csv(root / 'reports/market_registry.csv')
assert len(games3) == markets['games'] == 48
assert games3.seed.nunique() == 6
assert set(games3.seed).isdisjoint(set(games2.seed))
assert not markets['validation_or_holdout_used']
assert markets['feature_completion_gate'] == 'closed'
display(pd.Series({
    'Games': len(games3), 'Fresh development seed clusters': games3.seed.nunique(),
    'Total candidate descriptors': len(registry3), 'New market/delivery descriptors': 315,
    'Profiled legal states': markets['screening']['sampled_development_observations'],
    'Features selected for final model': 0
}, name='Scope').to_frame())""",
        ),
        (
            "markdown",
            "outcomes",
            """### Does the additional structure actually help?

Win plus half a tie is the primary local outcome. Coin production, opponent-relative
margin, waste and cash diagnose mechanisms; more features or more coins do not by
themselves establish a stronger competitive agent. Each arm has 12 games but only
six independent seed clusters.""",
        ),
        (
            "code",
            "groups",
            """groups3 = games3.groupby('arm').agg(
    games=('match_score', 'size'), match_score=('match_score', 'mean'),
    coins=('coins', 'mean'), margin=('coin_margin', 'mean'),
    discarded=('discarded_units', 'mean'), terminal_unsold=('unsold_product_units', 'mean')
)
display(groups3.round(3))
fig = go.Figure(go.Bar(x=groups3.index, y=groups3.match_score))
fig.update_layout(title='Fresh-seed local match score against the frozen stronger opponent',
                  xaxis_title='Delivery / market timing', xaxis_type='category',
                  yaxis_title='Win + half a tie · mean over 12 games', yaxis_range=[0, 1])
show_figure(fig)""",
        ),
        (
            "markdown",
            "effects-note",
            """### Paired effects and interaction

Main effects average ON-minus-OFF over the other factor. The interaction is a
difference-in-differences. Intervals resample 4,000 sets of six whole seed clusters,
keeping both seats and all four arms together. These exploratory intervals do not
correct for all historical design choices or establish generalization to the field.""",
        ),
        (
            "code",
            "effects",
            """display(effects3[effects3.metric.isin(['match_score', 'coins', 'discarded_units'])][
    ['contrast', 'metric', 'effect', 'bootstrap_low', 'bootstrap_high', 'seed_clusters']
].round(3))""",
        ),
        (
            "markdown",
            "mechanisms-note",
            """### Activation and exact product accounting

The intervention counter records changed commands, not successful causal mechanisms.
Every crop product is accounted for as sold, discarded or held at termination. Negative
results and inactive components remain visible rather than being removed after testing.""",
        ),
        (
            "code",
            "mechanisms",
            """assert (games3.harvested_units == games3.sold_units + games3.discarded_units
        + games3.unsold_product_units).all()
display(games3.groupby('arm')[['interventions_delivery', 'interventions_market_timing',
    'harvested_units', 'sold_units', 'discarded_units', 'unsold_product_units',
    'ineffective_farm_actions', 'minimum_observed_cash']].mean().round(3))""",
        ),
        (
            "markdown",
            "coverage-note",
            """### Descriptive coverage, not a claim of exhaustive predictive selection

The 933-column bank adds 315 mechanistic market/delivery descriptors to the prior 618.
Counterfactual inputs use legal observations and known rules only. Supply waves assume
optimistic independent delivery and exclude hidden stocks, later growth, decay and
competition between jobs. Newly unlocked shops cannot be predicted from a game seed.

Livestock, fertilizer, land expansion, adaptive crop mix, richer routing and opponent
learning still need their own activated tests. See the coverage ledger for the explicit
remaining work. The feature-completion gate remains closed.""",
        ),
        (
            "code",
            "coverage",
            """display(registry3.assign(variable=lambda d: d.distinct_development_values > 1)
    .groupby('family').agg(generated=('feature', 'size'), varying=('variable', 'sum')))
display(pd.Series({
    'Constant coverage gaps': len(markets['screening']['constant_features']),
    'Exact duplicate groups': len(markets['screening']['exact_duplicate_groups']),
    'Highly correlated pairs': markets['screening']['high_spearman_pairs'],
    'Policy median ms': markets['policy_latency_ms']['median'],
    'Policy p95 ms': markets['policy_latency_ms']['p95'],
    'Feature-bank p95 ms': markets['sampled_feature_bank_latency_ms']['p95']
}, name='Diagnostics').to_frame())""",
        ),
    ]
    for kind, identifier, source in additions:
        maker = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cell = maker(source)
        cell.id = "markets-" + identifier
        notebook.cells.append(cell)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "check", str(path)], check=True)
    result = nbformat.read(path, as_version=4)
    if (
        digest(
            [
                c.source
                for c in result.cells
                if c.cell_type == "code" and not c.id.startswith("markets-")
            ]
        )
        != preserved
    ):
        raise ValueError("Earlier study code changed during regeneration")
    print(f"Appended study 3; preserved earlier code SHA256={preserved}")


if __name__ == "__main__":
    main()
