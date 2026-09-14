"""Plotly views distinguish observed outcomes, conditional features and local latency."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def decorate(fig,subtitle=''):
    if subtitle:
        old=fig.layout.title.text or ''
        fig.update_layout(title={'text':old+'<br><sup>'+subtitle+'</sup>'})
    fig.update_layout(height=450,margin=dict(l=65,r=35,t=90,b=65),font=dict(size=13),legend_title_text='')
    return fig


def reference_figures(base):
    d=pd.read_csv(Path(base)/'reference/notebook13_cash_decomposition.csv')
    d=d[d.player==0].copy();d['component']=d.operation+' / '+d.item
    f1=decorate(px.bar(d,x='component',y='cash_delta',title='Notebook 13 | Reconciled −396-coin difference'),
      'Recorded rejected WATER-deferral trajectory. Accounting components are not independent causal effects.')
    m=d[d.operation=='SELL'].copy();m['average_control']=m.cash_control/m.units_control;m['average_defer']=m.cash_defer/m.units_defer
    long=m.melt(id_vars=['item','units_control','units_defer'],value_vars=['average_control','average_defer'],var_name='branch',value_name='average_realized_price')
    f2=decorate(px.bar(long,x='item',y='average_realized_price',color='branch',barmode='group',title='Notebook 13 | Realized price versus sold quantity',hover_data=['units_control','units_defer']),
      'Milk: 28 units in both branches; 142.71 versus 126.11 average coins per unit. No new experiment result.')
    return [f1,f2]


def screen_figures(base):
    out=Path(base)/'outputs/screen'
    states=pd.read_csv(out/'states.csv');tasks=pd.read_csv(out/'task_features.csv.gz');reg=pd.read_csv(out/'feature_registry.csv')
    states['group']=states.seed.astype(str)+'/seat '+states.seat.astype(str)
    counts=states.groupby('group',as_index=False).action_changed_in_window.sum()
    f1=decorate(px.bar(counts,x='group',y='action_changed_in_window',title='Harvest-value screen | First-action activation'),
      'Previously examined development groups. Both seats of a seed are not independent samples.')
    if len(tasks):
        f2=decorate(px.scatter(tasks,x='headline_value',y='marginal_value_after_shed',color='item',hover_data=['seed','seat','step','quantity','shed_units_ahead'],title='Harvest-value screen | Quote value versus marginal liquidation'),
          'One-sided current-market scenario; not a forecast of actual future sale price.')
        f3=decorate(px.scatter(tasks,x='within_lot_price_impact',y='backlog_price_impact',color='item',hover_data=['quantity','shed_units_ahead'],title='Harvest-value screen | Two sources of quote overstatement'),
          'Within-lot slippage and existing shed stock. These are not realized losses.')
    else:
        f2=go.Figure();f2.add_annotation(text='No eligible harvest tasks',showarrow=False);f3=go.Figure(f2)
    f4=decorate(px.bar(reg,x='feature',y='nonzero_fraction',title='Harvest-value screen | Candidate activation'),
      'Nonzero frequency, not feature importance. No fitted feature selector.')
    latent=states.melt(id_vars=['step','group'],value_vars=['candidate_callback_ms','reference_callback_ms','null_callback_ms'],var_name='callback',value_name='milliseconds')
    f5=decorate(px.scatter(latent,x='step',y='milliseconds',color='callback',hover_data=['group'],title='Harvest-value screen | Complete callback timings'),
      'Local sampled callbacks only; gate is 500 ms. Not Kaggle hosted-runtime certification.')
    f5.add_hline(y=500,line_dash='dash',annotation_text='500 ms acceptance limit')
    return [f1,f2,f3,f4,f5]


def pilot_figures(base):
    out=Path(base)/'outputs/pilot';r=json.loads((out/'report.json').read_text())
    if not r.get('completed_pairs'):
        f=go.Figure();f.add_annotation(text='Pilot skipped: no action activation.<br>No endpoint effect measured.',showarrow=False);f.update_layout(title='Harvest-value pilot | Not run',height=320)
        return [f]
    rows=pd.read_csv(out/'paired_results.csv')
    vals=[{'metric':k,'difference':float(rows.iloc[0][k+'_delta'])} for k in ['coins','coin_margin']]
    f1=decorate(px.bar(pd.DataFrame(vals),x='metric',y='difference',title='Harvest-value pilot | Paired endpoint differences'),
      f"One selected development pair. Local match change: {rows.iloc[0]['local_match_score_delta']:+.1f}. Not a leaderboard score.")
    t=pd.read_csv(out/'trajectories.csv')
    f2=decorate(px.line(t,x='step',y='own_cash',color='mode',title='Harvest-value pilot | Continuous cash trajectories'),
      'Recorded prefix, then reactive policies. Intermediate cash is not the endpoint metric.')
    prices=[]
    for row in t.to_dict('records'):
        # CSV stores dicts via repr; literal_eval accepts data only (never eval).
        import ast
        pr=ast.literal_eval(row['market_prices']);shops=ast.literal_eval(row['public_shops'])
        prices.append({'step':row['step'],'branch':row['mode'],'milk_price':pr['MILK'],'visible_shops':', '.join(shops)})
    f3=decorate(px.line(pd.DataFrame(prices),x='step',y='milk_price',color='branch',hover_data=['visible_shops'],title='Harvest-value pilot | Observable milk-market paths'),
      'Public context logged for explanation; no future shop list was supplied to the policy.')
    return [f1,f2,f3]


def dashboard(figures,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture — Harvest Value Research</title></head><body style="font-family:Arial;margin:32px;max-width:1300px"><h1>Kaggriculture | Harvest-value research</h1><p>Observed results, conditional scenarios and endpoint tests are labeled separately.</p>']
    for i,f in enumerate(figures):parts.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>');path.write_text('\n'.join(parts))
    return path
