"""Plotly evidence views: prior results, candidate activation, and paired outcomes."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def decorate(f,caption):
    title=f.layout.title.text or ''
    f.update_layout(title=title+'<br><sup>'+caption+'</sup>',height=460,
        margin=dict(l=65,r=30,t=95,b=80),font=dict(size=13),legend_title_text='')
    return f

def reference_figures(base):
    d=pd.read_csv(Path(base)/'reference/notebook14_task_features.csv.gz')
    d['quote_overstatement_percent']=100*(1-d.marginal_to_headline_ratio)
    f1=decorate(px.box(d,x='item',y='quote_overstatement_percent',points='all',title='Notebook 14 | Small price adjustments, unchanged actions'),
        'Actual prior evidence: 287 task rows, 156 sampled states, zero action changes. No endpoint experiment.')
    g=d.groupby('item',as_index=False).agg(tasks=('quantity','size'),max_quote_gap=('total_quote_overstatement','max'))
    f2=decorate(px.bar(g,x='item',y='max_quote_gap',hover_data=['tasks'],title='Notebook 14 | Largest conditional value correction by product'),
        'Coins in a hypothetical liquidation calculation, not realized gains or losses.')
    return [f1,f2]

def screen_figures(base):
    folder=Path(base)/'outputs/screen';s=pd.read_csv(folder/'states.csv');p=pd.read_csv(folder/'task_features.csv.gz');r=pd.read_csv(folder/'feature_registry.csv')
    s['source']=s.seed.astype(str)+'/seat '+s.seat.astype(str)
    g=s.groupby('source',as_index=False)[['retire_action_changed','renew_action_changed','renew_vs_retire_changed']].sum().melt(id_vars='source',var_name='contrast',value_name='changed_actions')
    f1=decorate(px.bar(g,x='source',y='changed_actions',color='contrast',barmode='group',title='Lifecycle screen | Component action activation'),
        'Retirement, renewal package, and added clearing. Three sources, two already-examined seeds.')
    f2=decorate(px.scatter(p,x='age_days',y='scheduled_events_remaining',color='crop',hover_data=['seed','seat','step','held_units','empty_exhausted'],title='Lifecycle screen | Remaining nominal production'),
        'Conditional on survival. Zero refresh events for single-yield crops does not mean they are worthless.')
    g2=p.groupby(['day','crop'],as_index=False)[['empty_exhausted','renewal_eligible']].sum().melt(id_vars=['day','crop'],var_name='condition',value_name='observed_plant_rows')
    f3=decorate(px.line(g2,x='day',y='observed_plant_rows',color='crop',line_dash='condition',title='Lifecycle screen | Empty spent plants and feasible renewal windows'),
        'Repeated snapshots of the same plants; these are not independent experiments.')
    f4=decorate(px.bar(r,x='feature',y='nonzero_fraction',title='Lifecycle screen | Feature activation, not importance'),
        'No fitted selector or target encoding. Time and identity fields are not outcome labels.')
    lat=s.melt(id_vars=['step','source'],value_vars=['candidate_callback_ms','retire_callback_ms','reference_callback_ms','null_callback_ms'],var_name='callback',value_name='milliseconds')
    f5=decorate(px.scatter(lat,x='step',y='milliseconds',color='callback',hover_data=['source'],title='Lifecycle screen | Complete local callback timing'),
        '500 ms gate. Sampled AWS callbacks are not hosted Kaggle-runtime certification.')
    f5.add_hline(y=500,line_dash='dash',annotation_text='500 ms cap')
    return [f1,f2,f3,f4,f5]

def pilot_figures(base):
    folder=Path(base)/'outputs/pilot';report=json.loads((folder/'report.json').read_text())
    if report['completed_branches']==0:
        f=go.Figure();f.add_annotation(text='No action activation: all continuations skipped.<br>No endpoint improvement measured.',showarrow=False)
        f.update_layout(title='Lifecycle pilot | Not run',height=300)
        return [f]
    r=pd.read_csv(folder/'paired_results.csv');t=pd.read_csv(folder/'trajectories.csv')
    x=r.melt(id_vars=['contrast','decision'],value_vars=['coins_delta','coin_margin_delta'],var_name='endpoint',value_name='change')
    f1=decorate(px.bar(x,x='contrast',y='change',color='endpoint',barmode='group',hover_data=['decision'],title='Lifecycle pilot | Endpoint differences versus common control'),
        'One development block. Comparisons share a control; no significance or leaderboard claim.')
    f2=decorate(px.line(t,x='step',y='own_cash',color='mode',title='Lifecycle pilot | Continuous own-cash trajectories'),
        '192 recorded prefix transitions followed by 527 responsive decisions per branch.')
    f3=decorate(px.bar(t.groupby('mode',as_index=False)[['water_commands','dig_commands','plant_commands']].sum().melt(id_vars='mode',var_name='command',value_name='requests'),x='mode',y='requests',color='command',barmode='group',title='Lifecycle pilot | Requested maintenance and renewal actions'),
        'Command requests, not automatically successful operations or independently attributable revenue.')
    return [f1,f2,f3]

def dashboard(figs,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture | Crop lifecycle</title></head><body style="font-family:Arial;margin:32px;max-width:1300px"><h1>Kaggriculture | Crop lifecycle feature research</h1><p>Known development evidence. Candidates remain provisional; no official submission score.</p>']
    for i,f in enumerate(figs):parts.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>');path.write_text('\n'.join(parts));return path
