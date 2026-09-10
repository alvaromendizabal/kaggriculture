"""Append six study-4 cells; migrate only study 1's private-artifact receipt check."""

import subprocess
import sys
from pathlib import Path

import nbformat
from notebook_provenance import archived_study_sources, migrate_study1_provenance


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith("supply-")]
    migrate_study1_provenance([c for c in notebook.cells if c.cell_type == "code"])
    additions = [
        (
            "markdown",
            "intro",
            """## Study 4 · Does tighter rival-stock information help decisions?

The public market can hide sales at the one-coin floor. We combine public inventory
flows with the rival's public cash change and visible minimum spending. These are
**conservative bounds**, not calibrated forecasts or access to private opponent data.
The [research report](../docs/supply_research.md) derives the accounting constraints,
documents buy/sell ambiguity, and links the domain and methodological sources.

Four fixed arms (`bank`, `visible`, `history`, `cash`) face two frozen crop opponents
on development seeds 1301–1304 in both seats: 64 games. Production/delivery rules,
four-action holding limit, and 0.5 scenario weight are frozen. Validation and holdout
remain untouched. This is feature research, not final training or a Kaggle rating.""",
        ),
        (
            "code",
            "load",
            """supply = json.loads((root / 'reports/supply_research.json').read_text())
games4 = pd.read_csv(root / 'reports/supply_games.csv')
effects4 = pd.read_csv(root / 'reports/supply_effects.csv')
registry4 = pd.read_csv(root / 'reports/supply_registry.csv')
bounds4 = pd.read_csv(root / 'reports/supply_bound_diagnostics.csv')
actions4 = pd.read_csv(root / 'reports/supply_action_identities.csv')
audit4 = json.loads((root / 'reports/supply_integrity.json').read_text())
assert len(games4) == supply['games'] == 64
assert games4.seed.nunique() == 4 and set(games4.seed).isdisjoint(games3.seed)
assert not supply['validation_or_holdout_used']
assert supply['feature_completion_gate'] == 'closed'
display(pd.Series({'Games': 64, 'Fresh seed clusters': 4, 'Frozen opponents': 2,
    'Joint provisional features': len(registry4), 'New cash features': 42,
    'Features selected for final model': 0}, name='Scope').to_frame())""",
        ),
        (
            "markdown",
            "outcomes-note",
            """### Primary outcome: wins and ties, not coin production alone

Each opponent/arm group has eight games but only four independent seed clusters.
The full 0–1 vertical scale is preserved in both interactive and static figures.
Opponent families share crop-policy ancestry; this is not a population-wide ranking.
History/cash scored 0.625 pooled versus bank's 0.375. The gain consists entirely of
eight mirror-match ties becoming narrow wins; score against relationship101 did
not improve. This does not justify a general competitive-performance claim.""",
        ),
        (
            "code",
            "outcomes",
            """import sys

sys.path.insert(0, str(root / 'scripts'))
from supply_plots import show_match_scores

groups4 = games4.groupby(['opponent', 'arm']).agg(
    games=('match_score', 'size'), wins=('match_score', lambda s: (s == 1).sum()),
    ties=('match_score', lambda s: (s == 0.5).sum()),
    score=('match_score', 'mean'), coins=('coins', 'mean'), margin=('coin_margin', 'mean'))
display(groups4.round(3))
score_table4 = groups4.score.unstack('opponent').reindex(['bank', 'visible', 'history', 'cash'])
show_match_scores(score_table4)""",
        ),
        (
            "markdown",
            "paired-note",
            """### Registered paired contrasts

Visible−bank tests the existing holding rule. History−visible tests stored-supply
information. Cash−history tests tighter cash constraints. Cash−bank tests the overall
practical change. Bootstrap intervals resample four **whole seed clusters**, retaining
seats and opponents together. They are descriptive, not confirmatory significance tests.
All seed differences remain available in the linked outcome files. Every cash-bank
seed mean had the same +0.25 score contrast, so its bootstrap interval collapses;
that does not establish zero population uncertainty. Cash/history produced identical
complete action sequences in all 16 matched games: no incremental decision gain.""",
        ),
        (
            "code",
            "paired",
            """display(effects4[(effects4.opponent == 'pooled') &
    effects4.metric.isin(['match_score', 'coins', 'coin_margin'])][
    ['contrast', 'metric', 'effect', 'bootstrap_low', 'bootstrap_high', 'seed_clusters']].round(3))
display(games4.groupby(['opponent', 'arm'])[
    ['interventions_market_timing', 'supply_activations', 'cash_extra_sale_units',
     'harvested_units', 'sold_units', 'discarded_units',
     'unsold_product_units']].mean().round(3))
action_identity4 = actions4.pivot(index=['seed', 'seat', 'opponent'],
    columns='arm', values='candidate_actions_sha256')
display(pd.DataFrame([{'contrast': treatment + '-' + control,
    'identical_full_action_sequences': int((action_identity4[treatment]
        == action_identity4[control]).sum()), 'paired_games': len(action_identity4)}
    for treatment, control in [('visible', 'bank'), ('history', 'visible'),
        ('cash', 'history'), ('cash', 'bank')]]))""",
        ),
        (
            "markdown",
            "bounds-note",
            """### Identification quality is distinct from decision quality

Only the post-run auditor reads rival private inventory. A useful bound must contain
the truth, but excessive width or persistent false alarms can still make it a poor
forecast. Report both containment and conservatism; do not call every tighter bound
a predictive win. Cash constraints reduced accumulated excess melon-stock bounds
by 13.19%, but empty-stock warnings did not decrease. Zero livestock stock here is
a coverage gap, not a rejection.""",
        ),
        (
            "code",
            "bounds",
            """display(bounds4.groupby('product')[['callbacks', 'actual_stock_positive',
    'strictly_tighter', 'loose_excess', 'cash_excess', 'loose_false_positive',
    'cash_false_positive', 'sale_units', 'loose_sale_lower', 'cash_sale_lower']].sum())
assert audit4['bound_violations'] == 0
assert audit4['policy_action_mismatches'] == 0
assert (bounds4.cash_excess <= bounds4.loose_excess).all()""",
        ),
        (
            "markdown",
            "screen-note",
            """### Joint feature screening, without premature selection

All 1,308 columns are screened together: 933 earlier descriptors, 333 history
descriptors and 42 cash descriptors. Constants and duplicates are coverage/redundancy
flags. They are not automatically rejected or represented as validated predictors.""",
        ),
        (
            "code",
            "screen",
            """display(registry4.assign(varying=lambda d: d.distinct_development_values > 1)
    .groupby('family').agg(generated=('feature', 'size'), varying=('varying', 'sum')))
display(pd.Series({'Constant columns': len(supply['screening']['constant_features']),
    'Exact duplicate groups': len(supply['screening']['exact_duplicate_groups']),
    'High-correlation pairs': supply['screening']['high_spearman_pairs'],
    'Sampled legal observations': supply['screening']['sampled_development_observations'],
    'Policy p95 milliseconds': supply['policy_latency_ms']['p95']}, name='Screen').to_frame())""",
        ),
        (
            "markdown",
            "audit-note",
            """### Restartable evidence and an open research gate

Completed episodes are checksummed and uploaded to private versioned S3. Source,
engine and protocol hashes must match before reuse. The policy is serialized and
restored 31 times in every game. The independent replay recomputes all sampled
features, checks every candidate action and verifies product conservation.

See the [coverage ledger](../docs/feature_coverage.md) for remaining livestock/feed,
fertilizer, land, crop-mix, routing and opponent-belief research. No final model is
trained or promoted here. No top-score guarantee follows from this experiment.""",
        ),
        (
            "code",
            "audit",
            """assert audit4['games_verified'] == 64
assert audit4['candidate_callbacks_verified'] == 64 * 719
assert audit4['sampled_feature_vectors_recomputed'] == 64 * 181
assert (games4.harvested_units == games4.sold_units + games4.discarded_units
    + games4.unsold_product_units).all()
display(pd.Series({key: audit4[key] for key in ['games_verified',
    'candidate_callbacks_verified', 'sampled_feature_vectors_recomputed',
    'stock_containment_checks', 'sale_containment_checks', 'bound_violations',
    'policy_action_mismatches', 'state_roundtrips', 'feature_completion_gate']},
    name='Verified evidence').to_frame())""",
        ),
    ]
    for kind, identifier, source in additions:
        make = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cell = make(source)
        cell.id = "supply-" + identifier
        notebook.cells.append(cell)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], check=True)
    updated = nbformat.read(path, as_version=4)
    earlier = [c for c in updated.cells if c.cell_type == "code" and not c.id.startswith("supply-")]
    archived_study_sources(earlier, require_migration=True)
    print("Appended six study-4 cells; 16 earlier cells unchanged, one receipt-only adapter.")


if __name__ == "__main__":
    main()
