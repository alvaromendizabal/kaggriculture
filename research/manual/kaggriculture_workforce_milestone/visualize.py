"""Plot saved workforce outputs only; no fitting or game execution."""
from __future__ import annotations
from html import escape
from pathlib import Path
import json
import pandas as pd
import plotly.graph_objects as go


def build_figures(out: Path):
    report=json.loads((out/'report.json').read_text())
    frame=pd.read_csv(out/'state_features.csv')
    registry=pd.read_csv(out/'feature_registry.csv')
    mechanics=json.loads((out/'mechanics.json').read_text())
    figures=[]
    coverage=pd.DataFrame(mechanics['rows']).groupby('hired_hands')[['new_passed','old_rejected']].sum()
    fig=go.Figure()
    fig.add_bar(x=coverage.index,y=coverage.new_passed,name='New extractor: accepted views')
    fig.add_bar(x=coverage.index,y=coverage.old_rejected,name='Frozen validator: rejected views')
    fig.update_layout(title='1 · Workforce contract: both players and both observer views',
                      xaxis_title='Hired hands in the fixture',yaxis_title='Observation views',barmode='group',height=440)
    figures.append(('coverage',fig))
    fig=go.Figure()
    for name,group in frame.groupby('episode_id',sort=True):
        fig.add_scatter(x=group.step,y=group['own.worker_count'],mode='lines+markers',name=str(name)[:8])
    fig.update_layout(title='2 · Workforce actually encountered in saved development episodes',
                      xaxis_title='Decision step',yaxis_title='Own workers, including farmer',height=430)
    figures.append(('workforce_by_step',fig))
    chosen=['own.harvest.count','own.water.count','own.feed.count','own.care.count','own.weed.count',
            'own.harvest.independent_unreachable_today','own.harvest.manual_cash_reachable_units_bound',
            'own_inventory.carried_units','own_inventory.deposit_overflow_if_all_arrive']
    active=registry.set_index('feature').loc[chosen]
    fig=go.Figure(go.Bar(x=active.nonzero_fraction,y=chosen,orientation='h',
                        customdata=active[['minimum','maximum','episodes_with_variation']].to_numpy(),
                        hovertemplate='%{y}<br>Nonzero: %{x:.1%}<br>Min: %{customdata[0]}<br>Max: %{customdata[1]}<br>Varying episodes: %{customdata[2]}<extra></extra>'))
    fig.update_layout(title='3 · Feature activation is coverage—not predictive contribution',
                      xaxis_title='Fraction of saved observations with nonzero value',height=530,
                      margin=dict(l=390,r=30),yaxis=dict(autorange='reversed'))
    fig.update_xaxes(tickformat='.0%',range=[0,1]);figures.append(('activation',fig))
    fig=go.Figure(go.Box(y=frame.extractor_ms,boxpoints='all',jitter=.25,name='New extractor only'))
    fig.update_layout(title='4 · Measured extractor latency — full callback NOT tested',
                      yaxis_title='Milliseconds per saved observation',height=430)
    figures.append(('extractor_latency',fig))
    ex=json.loads((out/'example_state.json').read_text())
    workers=pd.DataFrame(ex['workers']);tasks=pd.DataFrame(ex['tasks'])
    fig=go.Figure()
    if not tasks.empty:
        for kind,group in tasks[tasks.side=='own'].groupby('kind'):
            fig.add_scatter(x=group.x,y=group.y,mode='markers',name=kind,
                            marker=dict(size=13,symbol='square'),text=group.task_id,
                            hovertemplate='%{text}<br>x=%{x}, y=%{y}<extra></extra>')
    own=workers[workers.side=='own']
    fig.add_scatter(x=own.x,y=own.y,mode='markers+text',text=own.worker_index,
                    textposition='top center',name='Worker action index',marker=dict(size=11,symbol='x'))
    fig.add_scatter(x=[4,4,5,5],y=[4,5,4,5],mode='markers',name='Shed access',marker=dict(size=23,symbol='square-open'))
    fig.update_layout(title='5 · Visible tasks and worker identities: one saved state',
                      xaxis_title='Board x',yaxis_title='Board y',height=580)
    fig.update_xaxes(range=[-.5,9.5],dtick=1);fig.update_yaxes(range=[9.5,-.5],dtick=1,scaleanchor='x')
    figures.append(('board',fig))
    return figures


def export_dashboard(out: Path, figures, mode='AWS SAVED-OBSERVATION AUDIT'):
    report=json.loads((out/'report.json').read_text())
    parts=["<!doctype html><html><head><meta charset='utf-8'><title>Kaggriculture workforce research</title>",
           "<style>body{font-family:system-ui,sans-serif;max-width:1160px;margin:36px auto;padding:0 24px;line-height:1.6}h1{line-height:1.15}table{border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}</style></head><body>",
           f'<h1>Kaggriculture · Workforce feature coverage</h1><p><strong>{escape(mode)}</strong></p>',
           '<p>New aggregate candidates and worker-indexed observations. Zero full games, zero model fits, no policy promotion, and no leaderboard improvement claim. Feature engineering remains open.</p>',
           f'<p>Source: <code>{escape(report["source_commit"])}</code></p>',
           pd.DataFrame([{'Saved observations':report['saved_observations'],'Candidate state features':report['aggregate_candidate_features'],
                          'Varying candidates':report['varying_features'],'Worker rows':report['worker_rows'],
                          'Full callback':'NOT RUN'}]).to_html(index=False)]
    for i,(_,fig) in enumerate(figures):parts.append(fig.to_html(full_html=False,include_plotlyjs=(True if i==0 else False)))
    parts.append('<h2>Interpretation and next decision</h2><p>Independent task reachability ignores coupled schedules and resource conflicts. An activated or varying feature is not proven useful. Frozen policies are unchanged. The next gate is action-path integration and bounded full-callback testing before any paired new-game ablation.</p></body></html>')
    path=out/'workforce_dashboard.html';path.write_text('\n'.join(parts));return path
