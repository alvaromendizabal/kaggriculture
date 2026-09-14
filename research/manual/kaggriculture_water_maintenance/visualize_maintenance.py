"""Plotly diagnostics; activation and scenario value are not feature importance."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

def tidy(fig, title):
    fig.update_layout(title=title, height=440, margin=dict(t=75, l=65, r=40, b=70), font=dict(size=14), legend_title_text='', hovermode='closest')
    for axis in (fig.layout.xaxis, fig.layout.yaxis):
        if axis.title.text:
            axis.title.text = axis.title.text.replace('_', ' ').capitalize()
    return fig

def empty(title, message):
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False)
    return tidy(fig, title)

def prior_figure(reference):
    df = pd.read_csv(Path(reference) / 'notebook11_pairs.csv')
    r = df.loc[df.role == 'primary'].iloc[0]
    frame = pd.DataFrame({'metric': ['Own final cash', 'Opponent final cash', 'Coin margin'], 'difference': [r.coins_delta, r.opponent_coins_delta, r.coin_margin_delta]})
    return tidy(px.bar(frame, x='metric', y='difference', text='difference'), 'Notebook 11: −2 own coins, +1 margin, unchanged win')

def screen_figures(out):
    root = Path(out)
    states = pd.read_csv(root / 'screen/states.csv')
    plants = pd.read_csv(root / 'screen/crop_features.csv.gz')
    a = states.groupby(['day', 'seed'], as_index=False).agg(action_changes=('action_changed_in_window', 'sum'))
    f1 = tidy(px.bar(a, x='day', y='action_changes', color=a.seed.astype(str)), 'Action changes are permitted only on game days 20 and 21 (zero-indexed)')
    if plants.empty:
        f2 = empty('Crop deferral opportunities', 'No plants in the sampled states')
        f3 = empty('Immediate benefit versus maintenance debt', 'No plant rows')
    else:
        p = plants.groupby('crop', as_index=False).agg(defer_fraction=('defer_eligible', 'mean'), survival_critical_fraction=('survival_gain', 'mean'), rows=('crop', 'size'))
        f2 = tidy(px.bar(p, x='crop', y='defer_fraction', hover_data=['rows', 'survival_critical_fraction']), 'Candidate deferral fraction by crop — coverage, not independence')
        f3 = tidy(px.scatter(plants, x='water_bonus_now', y='next_units_delta', color='crop', size=plants['next_day_maintenance_debt'] + 1, opacity=0.55, hover_data=['seed', 'seat', 'day', 'hour', 'dry_streak', 'defer_eligible']), 'WATER now: immediate units, next-refresh units, and deferred work')
    debt = states.groupby(['day', 'seed'], as_index=False).agg(deferred_tasks=('deferred_next_day_tasks', 'mean'), unwatered=('unwatered_plants', 'mean'))
    f4 = tidy(px.line(debt, x='day', y='deferred_tasks', color=debt.seed.astype(str), markers=True), 'Postponement transfers work to tomorrow — it does not erase it')
    f5 = tidy(px.scatter(states, x='step', y='candidate_callback_ms', color=states.seed.astype(str), hover_data=['seat', 'plant_count', 'defer_eligible_plants']), 'Complete candidate callback time on sampled observations')
    return [f1, f2, f3, f4, f5]

def pilot_figures(out):
    out = Path(out)
    r = json.loads((out / 'pilot/report.json').read_text())
    if not r.get('completed_pairs'):
        return [empty('Endpoint feature ablation', 'Pilot skipped: no action activation'), empty('Linked cash trajectories', 'No new continuation was run')]
    df = pd.read_csv(out / 'pilot/paired_results.csv')
    row = df.iloc[0]
    effects = pd.DataFrame({'metric': ['Own coins', 'Coin margin', 'Residual product units'], 'difference': [row.coins_delta, row.coin_margin_delta, row.residual_product_units_delta]})
    first = tidy(px.bar(effects, x='metric', y='difference', text='difference'), 'One development pair: endpoint differences (not a leaderboard rating)')
    trace = pd.read_csv(out / 'pilot/trajectories.csv')
    second = tidy(px.line(trace, x='step', y='own_cash', color='mode', hover_data=['day', 'water_commands']), 'Reactive continuation: banked cash through the final legal decision')
    return [first, second]

def dashboard(figures, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = '<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture · Maintenance research</title>\n    <style>body{font-family:system-ui;margin:32px auto;max-width:1150px;padding:0 20px}section{margin:28px 0}p{line-height:1.6}</style>\n    </head><body><h1>Crop maintenance · controlled feature research</h1>\n    <p>Current-observation scenarios, real action checks, and a bounded endpoint test. Development evidence only; no official leaderboard score.</p>'
    html = [header]
    for i, fig in enumerate(figures):
        html.append('<section>' + pio.to_html(fig, full_html=False, include_plotlyjs=True if i == 0 else False) + '</section>')
    html.append('</body></html>')
    path.write_text('\n'.join(html))
