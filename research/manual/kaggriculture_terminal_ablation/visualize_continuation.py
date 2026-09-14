"""Seven Plotly views. Endpoint outcomes and candidate activation stay separate."""
from pathlib import Path
import html
import pandas as pd
import plotly.graph_objects as go


def labeled(frame):
    f=frame.copy()
    f['episode']=f['seed'].astype(str)+' / seat '+f['seat'].astype(str)+' / '+f['arm']
    return f


def figures(outputs,reference):
    out=Path(outputs);ref=Path(reference)
    pairs=labeled(pd.read_csv(out/'paired_results.csv'))
    trace=labeled(pd.read_csv(out/'trajectory.csv'))
    old=pd.read_csv(ref/'notebook08_one_step_effects.csv')
    registry=pd.read_csv(out/'feature_registry.csv')
    charts=[]
    f=go.Figure()
    for (seed,seat),g in old[old.source_arm=='coordinated'].groupby(['seed','seat']):
        f.add_scatter(x=g.step,y=g.own_cash_delta,mode='lines+markers',name=f'{seed} / seat {seat}')
    f.update_layout(title='08 evidence: isolated one-step cash changes—not cumulative profit',xaxis_title='Decision step',yaxis_title='One-step own-cash difference (coins)')
    charts.append(f)
    f=go.Figure()
    f.add_scatter(x=pairs.coins_control,y=pairs.episode,mode='markers',name='Control')
    f.add_scatter(x=pairs.coins_aligned,y=pairs.episode,mode='markers',name='Aligned SELL quantities')
    f.update_layout(title='09 endpoints: paired final cash from identical starting states',xaxis_title='Final banked coins',yaxis_title='Source episode / policy stratum')
    charts.append(f)
    f=go.Figure()
    for role,g in pairs.groupby('role'):
        f.add_bar(x=g.episode,y=g.coins_delta,name=role.replace('_',' '),
                  customdata=g[['coin_margin_delta','local_match_score_delta','residual_product_units_delta']].to_numpy(),
                  hovertemplate='%{x}<br>Coin delta: %{y}<br>Margin delta: %{customdata[0]}<br>Local match delta: %{customdata[1]}<br>Residual-unit delta: %{customdata[2]}<extra></extra>')
    f.add_hline(y=0)
    f.update_layout(title='Final effect: primary intervention versus no-change controls',xaxis_title='Source episode',yaxis_title='Aligned − control coins')
    charts.append(f)
    merged=trace.pivot(index=['episode_id','episode','step'],columns='variant',values='own_cash_after').reset_index()
    merged['cash_delta']=merged['aligned']-merged['control']
    f=go.Figure()
    for name,g in merged.groupby('episode'):
        f.add_scatter(x=g.step,y=g.cash_delta,mode='lines+markers',name=name)
    f.add_hline(y=0)
    f.update_layout(title='Cash difference along diverging trajectories—do not sum points',xaxis_title='Executed decision step',yaxis_title='Difference in current banked coins')
    charts.append(f)
    primary=pairs[pairs.role=='primary_intervention']
    matrix=primary.pivot(index='seed',columns='seat',values='coins_delta').reindex(columns=[0,1])
    f=go.Figure(go.Heatmap(z=matrix.to_numpy(),x=['Seat 0','Seat 1'],y=matrix.index.astype(str).tolist(),
                         hovertemplate='Seed %{y}, %{x}<br>Final coin delta: %{z}<extra></extra>',hoverongaps=False))
    f.update_layout(title='Primary stability by seed and seat; blank means unobserved',xaxis_title='Seat (may be symmetric)',yaxis_title='Development seed—not a held-out fold')
    charts.append(f)
    f=go.Figure()
    for variant,g in trace.groupby('variant'):
        f.add_box(y=g.candidate_callback_ms,name=f'{variant} candidate',boxpoints='outliers')
        f.add_box(y=g.opponent_callback_ms,name=f'{variant} opponent',boxpoints='outliers')
    f.add_hline(y=500,annotation_text='500 ms local acceptance limit')
    f.update_layout(title='Full callbacks on visited states—not hosted Kaggle timing',yaxis_title='Measured milliseconds')
    charts.append(f)
    context=registry[registry.feature.str.startswith('terminal_context.')].copy()
    context['label']=context.feature.str.replace('terminal_context.','',regex=False)
    f=go.Figure(go.Bar(x=context.label,y=context.distinct_values,
                      customdata=context[['minimum','maximum','nonzero_fraction']].to_numpy(),
                      hovertemplate='%{x}<br>Distinct: %{y}<br>Min: %{customdata[0]}<br>Max: %{customdata[1]}<br>Nonzero: %{customdata[2]}<extra></extra>'))
    f.update_layout(title='12 new terminal-exposure candidates: activation, not importance',xaxis_title='Current-observation descriptor',yaxis_title='Distinct observed values')
    charts.append(f)
    for f in charts:f.update_layout(height=460,margin=dict(l=65,r=25,t=85,b=105))
    return charts


def export_dashboard(charts,path,decision,mode):
    content=['<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture | Terminal feature ablation</title></head><body>',
        '<main style="max-width:1200px;margin:40px auto;font-family:system-ui;line-height:1.5">',
        '<h1>Kaggriculture · Terminal cash feature ablation</h1>',
        '<p><strong>'+html.escape(mode)+'</strong></p>',
        '<p>Decision: '+html.escape(decision)+'</p>',
        '<p>Exploratory final-day continuations. Not a leaderboard rating or independent validation. Negative controls are not efficacy trials.</p>']
    for i,f in enumerate(charts):content.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    content.append('</main></body></html>')
    Path(path).write_text('\n'.join(content))
