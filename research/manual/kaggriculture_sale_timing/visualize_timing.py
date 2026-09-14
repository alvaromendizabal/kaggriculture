"""Plotly evidence views. Never substitute synthetic outcomes into a live report."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


def diagnosis_figures(reference):
    reference=Path(reference)
    diagnosis=json.loads((reference/'diagnosis.json').read_text())
    trajectory=pd.read_csv(reference/'notebook09_trajectory.csv')
    trajectory['Cash gain since final-day start']=trajectory.groupby('variant')['own_cash_after'].transform(lambda s:s-s.iloc[0])
    a=px.line(trajectory,x='step',y='own_cash_after',color='variant',markers=True,
              title='Notebook 09: an early cash lead ended 3 coins behind',labels={'own_cash_after':'Actual banked coins','step':'Decision step'})
    ledger=pd.DataFrame(diagnosis['ledger'])
    b=px.bar(ledger[ledger['product']=='TOMATO'],x='step',y='coins',color='variant',barmode='group',
             title='Reconciled tomato sales: 332 earlier versus 335 later',labels={'coins':'Realized sale revenue','step':'Decision step'})
    return [a,b]


def experiment_figures(out):
    out=Path(out);r=json.loads((out/'report.json').read_text())
    table=pd.read_csv(out/'final_comparisons.csv');lat=pd.read_csv(out/'latency.csv')
    f=pd.read_csv(out/'timing_features.csv');registry=pd.read_csv(out/'feature_registry.csv')
    table['source']=table['seed'].astype(str)+' / seat '+table['seat'].astype(str)+' / '+table['arm']
    a=px.bar(table,x='source',y='coins_delta',color='role',title='Final-decision gate: endpoint coin differences',
             hover_data=['coin_margin_delta','local_match_score_delta','final_market_changed'],labels={'coins_delta':'Guarded minus control coins'})
    b=px.bar(table,x='source',y='local_match_score_delta',color='role',title='Local match change (not a leaderboard rating)',
             labels={'local_match_score_delta':'Win/tie/loss indicator difference'})
    fields=[c for c in f if c.endswith('h1.conditional_holding_premium')]
    long=f.melt(id_vars=['seed','seat','arm','step'],value_vars=fields,var_name='product',value_name='premium')
    long['product']=long['product'].str.split('.').str[1]
    grouped=long.groupby(['product','step'],as_index=False)['premium'].mean()
    pivot=grouped.pivot(index='product',columns='step',values='premium')
    c=go.Figure(go.Heatmap(z=pivot.to_numpy(),x=pivot.columns,y=pivot.index,
                          colorbar={'title':'Scenario coins'}))
    c.update_layout(title='Known-demand-only one-step holding premium: descriptive mean',xaxis_title='Decision step',yaxis_title='Product')
    d=px.scatter(lat,x='step',y='callback_ms',color='actor',hover_data=['seed','seat','arm'],
                 title='Measured complete callbacks (500 ms acceptance gate)',labels={'callback_ms':'Wall time (ms)'})
    d.add_hline(y=500,line_dash='dash')
    activation=registry.groupby('distinct_values').size().reset_index(name='features')
    e=px.bar(activation,x='distinct_values',y='features',title='Candidate activation, not feature importance',
             labels={'distinct_values':'Distinct observed values','features':'Candidate count'})
    return [a,b,c,d,e]


def style(figures):
    for fig in figures:fig.update_layout(height=440,margin=dict(l=60,r=30,t=80,b=70),font=dict(size=13))
    return figures

def save_dashboard(figures,path,heading='Sale-timing feature research'):
    import html
    blocks=[f'<html><head><meta charset="utf-8"><title>{html.escape(heading)}</title></head><body>',
            f'<h1>{html.escape(heading)}</h1><p>Development evidence only. Conditional values are not forecasts. Local scores are not leaderboard ratings.</p>']
    for i,fig in enumerate(figures):blocks.append(pio.to_html(fig,full_html=False,include_plotlyjs=True if i==0 else False))
    blocks.append('</body></html>');Path(path).write_text('\n'.join(blocks),encoding='utf-8')
