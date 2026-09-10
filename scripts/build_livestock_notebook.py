"""Extend the canonical notebook while preserving the 23 earlier code cells."""

import subprocess
import sys
from pathlib import Path

import nbformat

from kaggriculture_research.artifacts import digest

PRIOR_SOURCE = "aaf0381fa1aa2f9a216bbe49e5f1b7348a304fd612ba73ef28301473ba7a3d0a"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith("livestock-")]
    if digest([c.source for c in notebook.cells if c.cell_type == "code"]) != PRIOR_SOURCE:
        raise ValueError("Earlier study source changed")
    additions = [
        (
            "markdown",
            "intro",
            """## Study 5 · Livestock, feed and fertilizer resource loops

The preceding crop-only study left all 78 animal state/feed-care descriptors
constant. This study adds 234 descriptors and a fixed mixed farm to test resource
coupling directly. The [registered protocol](../docs/livestock_protocol.md) maps
the official mechanisms and research literature to testable interventions.
The [findings](../docs/livestock_research.md) report effects and remaining gaps.

Animals may produce a base unit while unfed. Feeding prevents escape and protects
care bonuses; today's CARE enters the bank **after** tonight's production. Manure
is a renewable one-unit slot. Fertilizer therefore competes with its sale price,
collection/transport work and watering deadlines. These relationships motivate
the features; crop names alone do not establish useful real-world agronomy.

Four fresh seeds × two seats × two opponents × four sequential arms = 64 games.
All prior engine/feature sources are preserved. The 42 previous cash bounds are
excluded from this study because its own policy buys wheat. The supported active
bank is 1,500 descriptors; the project union is 1,542 provisional candidates.""",
        ),
        (
            "code",
            "load",
            """livestock = json.loads((root / 'reports/livestock_research.json').read_text())
games5 = pd.read_csv(root / 'reports/livestock_games.csv')
effects5 = pd.read_csv(root / 'reports/livestock_effects.csv')
registry5 = pd.read_csv(root / 'reports/livestock_registry.csv')
audit5 = json.loads((root / 'reports/livestock_integrity.json').read_text())
actions5 = pd.read_csv(root / 'reports/livestock_action_identities.csv')
assert len(games5) == 64 and games5.seed.nunique() == 4
assert set(games5.seed).isdisjoint(games4.seed)
assert not livestock['validation_or_holdout_used']
assert livestock['feature_completion_gate'] == 'closed'
assert len(registry5) == 1500
assert not registry5.feature.str.startswith('cash_history.').any()
display(pd.Series({'Development games in study': 64, 'Whole seed clusters': 4,
    'Active supported descriptors': 1500, 'New resource descriptors': 234,
    'Final selected features': 0}, name='Study scope').to_frame())""",
        ),
        (
            "markdown",
            "scores-note",
            """### Primary outcome and opponent sensitivity

Each group has eight games but only four seed clusters. The full 0–1 score scale
is retained. The mixed-farm opponent adds a different production regime, but two
fixed opponents do not represent the competition population. Local match score
is not the official leaderboard rating. Care and fertilizer each won all 16
matches; selective feed alone lost every mixed-farm match. The saturated scores
cannot establish extra ranking benefit from fertilizer's higher coin margin.""",
        ),
        (
            "code",
            "scores",
            """from livestock_plots import show_livestock_scores, show_resource_work

groups5 = games5.groupby(['opponent', 'arm']).agg(
    games=('match_score', 'size'), wins=('match_score', lambda s: (s == 1).sum()),
    ties=('match_score', lambda s: (s == 0.5).sum()), score=('match_score', 'mean'),
    coins=('coins', 'mean'), margin=('coin_margin', 'mean'))
display(groups5.round(3))
show_livestock_scores(groups5.score.unstack('opponent').reindex(
    ['routine', 'feed', 'care', 'fertilizer']))""",
        ),
        (
            "markdown",
            "effects-note",
            """### Component effects and resource use

Feed−routine tests selective feeding; care−feed then tests selective care;
fertilizer−care tests net treatment allocation. Fertilizer−routine tests the whole
change. These are **conditional sequential effects**, not factorial main effects.
Bootstrap intervals resample four whole seed means, keeping seats and opponents
together. They are exploratory and do not establish broad competitive superiority.

The work charge of eight coins is fixed, not fitted. Fertilizer values use a
seven-day, single-tile continuation with current price curves and assumed water/
collection service. They expose feasible scenarios rather than calibrated future
prices or a globally feasible worker schedule. Zero optional action counters mean
no event; the reporting adapter normalizes absent Counter keys before grouping.

Post-registration mechanism diagnostics reveal about 52.75 care actions per game
without feeding in the feed-only arm. Those cannot create a banked bonus. Care
and fertilizer coordinate the two services. A remaining defect is explicit:
they still spend 3.000 and 2.875 feed units per game on the final day, when no
refresh remains. These observations motivate a new registered intervention;
the completed study and its frozen policies are unchanged.""",
        ),
        (
            "code",
            "effects",
            """display(effects5[(effects5.opponent == 'pooled') & effects5.metric.isin(
    ['match_score', 'coin_margin', 'fed_units', 'commands_CARE', 'applied_units'])][
    ['contrast', 'metric', 'effect', 'bootstrap_low', 'bootstrap_high', 'seed_clusters']].round(3))
display(games5.groupby(['opponent', 'arm'])[['escaped_animals',
    'lost_unfed_bonus_units', 'uncollected_manure_slots', 'overflow_production_units',
    'discarded_units', 'terminal_units']].mean().round(3))
show_resource_work(games5)
identity5 = actions5.pivot(index=['seed', 'seat', 'opponent'],
    columns='arm', values='actions_sha256')
display(pd.DataFrame([{'contrast': t + '-' + c,
    'identical_action_sequences': int((identity5[t] == identity5[c]).sum()),
    'paired_games': len(identity5)} for t, c in livestock['lineage']['protocol']['contrasts']]))
species5 = pd.read_csv(root / 'reports/livestock_species.csv')
display(species5.groupby(['arm', 'species'])[['care_without_feed',
    'care_bank_additions', 'care_units_realized', 'care_units_lost_capacity']].mean().round(3))
keys5 = ['seed', 'seat', 'opponent', 'arm']
nights5 = species5.groupby(keys5)[['fed_nights', 'care_actions_flagged']].sum().reset_index()
terminal5 = games5.merge(nights5, on=keys5, validate='one_to_one')
terminal5['final_day_feed'] = terminal5.fed_units - terminal5.fed_nights
terminal5['final_day_care'] = terminal5.commands_CARE - terminal5.care_actions_flagged
display(terminal5.groupby('arm')[['final_day_feed', 'final_day_care']].mean().round(3))""",
        ),
        (
            "markdown",
            "coverage-note",
            """### Coverage and redundancy are distinct from predictive value

All 1,500 supported features are screened together. We separately count formerly
constant animal descriptors, new resource descriptors, constants and duplicate
groups. Variation establishes trajectory coverage, not causal usefulness of each
column. No final model has selected or rejected any feature.""",
        ),
        (
            "code",
            "coverage",
            """families5 = registry5.assign(
    varying=lambda d: d.distinct_development_values > 1).groupby(
    'family').agg(generated=('feature', 'size'), varying=('varying', 'sum'))
display(families5)
previous_animals5 = registry5[registry5.family.isin(
    ['animal_state', 'animal_feed_care_interactions'])]
assert len(previous_animals5) == 78
display(previous_animals5.groupby('family').agg(generated=('feature', 'size'),
    varying=('distinct_development_values', lambda s: (s > 1).sum())))
runtime5 = json.loads((root / 'reports/livestock_runtime.json').read_text())
display(pd.Series({'Constants': len(livestock['screening']['constant_features']),
    'Exact duplicate groups': len(livestock['screening']['exact_duplicate_groups']),
    'High-correlation pairs': livestock['screening']['high_spearman_pairs'],
    'Sampled legal observations': livestock['screening']['sampled_development_observations'],
    'Policy p95 ms': livestock['policy_latency_ms']['p95'],
    'Full feature pipeline p95 ms, one saved trace':
        runtime5['full_sampled_feature_pipeline']['p95_ms']},
    name='Development screen').to_frame())""",
        ),
        (
            "markdown",
            "audit-note",
            """### Restartable and independently checked

Each game is stored atomically with engine, source, protocol and semantic hashes,
then saved to private versioned S3. Independent replay reconstructs every action,
all sampled vectors, and policy/history restores. Only the post-run auditor sees
paired private inventories. It checks actual farm/market transitions and balances
each product across harvest/collection, purchases, feed/application, sales, losses
and final stock. Both market bounds and resource accounting must pass.

The earlier 23 code cells are preserved exactly. This extended notebook has its
own execution receipt; the archived supply receipt is not relabeled as a receipt
for these new cells. See the [recovery runbook](../docs/livestock_recovery.md).
Feature research remains open: land, joint routing/assignment, alternative herd/
crop mixes, opponent response and continuation uncertainty still need evidence.""",
        ),
        (
            "code",
            "audit",
            """from verify_livestock_report import verify as verify_livestock_report

assert audit5['complete'] and audit5['games_audited'] == 64
assert audit5['mismatches'] == 0
assert audit5['counts']['feature_vectors'] == 64 * 181
assert audit5['counts']['private_transitions'] == 64 * 1438
assert (games5.harvested_units + games5.collected_units + games5.bought_units
    == games5.sold_units + games5.fed_units + games5.applied_units
    + games5.discarded_units + games5.terminal_units).all()
display(pd.Series(audit5['counts'], name='Independently verified').to_frame())
verify_livestock_report(root)
print('Registered evidence and remote-byte receipts match; feature research remains open.')""",
        ),
    ]
    for kind, identifier, source in additions:
        make = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cell = make(source)
        cell.id = "livestock-" + identifier
        notebook.cells.append(cell)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], check=True)
    cells = [c for c in nbformat.read(path, as_version=4).cells if c.cell_type == "code"]
    if digest([c.source for c in cells[:23]]) != PRIOR_SOURCE or len(cells) != 28:
        raise ValueError("Earlier source changed or extension has wrong size")
    print("Preserved 23 earlier code cells; appended five livestock study cells.")


if __name__ == "__main__":
    main()
