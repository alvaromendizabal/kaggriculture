"""Plotly evidence views. Missing outcomes are shown as not run, never as zero."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io_utils import atomic,read

def empty(title,why):
    f=go.Figure();f.add_annotation(text=why,x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    f.update_layout(title=title,height=400,xaxis={'visible':False},yaxis={'visible':False});return f
def frame(p):
    if not p.exists() or p.stat().st_size<3:return pd.DataFrame()
    try:return pd.read_csv(p)
    except pd.errors.EmptyDataError:return pd.DataFrame()
def figures(base,rid):
    base=Path(base);r=base/'outputs'/f'round{rid}';s=frame(r/'screen/states.csv');t=frame(r/'screen/task_features.csv.gz');registry=frame(r/'screen/feature_registry.csv')
    prior=frame(base/'reference/notebook16_endpoints.csv');fs=[]
    fs.append(px.bar(prior,x='mode',y='coin_margin',title='Previous evidence: notebook 16 margin, not leaderboard rating') if not prior.empty else empty('Previous evidence','No input data'))
    if not s.empty:
        a=s.groupby(['seed','seat'],as_index=False)['changed'].sum();a['block']=a['seed'].astype(str)+' / seat '+a['seat'].astype(str)
        fs.append(px.bar(a,x='block',y='changed',title='Archived development screen: changed first actions'))
    else:fs.append(empty('Action activation','Screen not run'))
    field='lost_quote_value' if rid=='17' else 'released_quote_value';mechanism='lost_units_on_route' if rid=='17' else 'released_production_units'
    x='travel_actions' if rid=='17' else 'current_headroom'
    fs.append(px.box(t,x='crop',y=field,points=False,title='Conditional feature adjustment by crop — not realized profit') if not t.empty else empty('Feature adjustments','No eligible crop task rows'))
    fs.append(px.scatter(t,x=x,y=mechanism,color='crop',hover_data=['current_units','step','worker'],title='Mechanism activation in recorded current states',opacity=.6) if not t.empty else empty('Mechanism','No task rows'))
    if not registry.empty:
        rr=registry.sort_values('distinct_values',ascending=False).head(16)
        fs.append(px.bar(rr,x='distinct_values',y='feature',orientation='h',title='Descriptor variation — not feature importance'))
    else:fs.append(empty('Descriptor variation','No registry'))
    if not s.empty:
        f=px.scatter(s,x='step',y='candidate_ms',color='seed',title='Screen callback wall time, including feature use');f.add_hline(y=500,line_dash='dash',annotation_text='500 ms acceptance limit');fs.append(f)
    else:fs.append(empty('Callback runtime','Screen not run'))
    comps=[];traces=[];state_parts=[]
    for i in range(1,5):
        folder=r/f'pair{i}';c=frame(folder/'comparison.csv');tr=frame(folder/'trajectories.csv');st=frame(folder/'states.csv')
        if not c.empty:comps.append(c)
        if not tr.empty:tr['block']=f'b{i}';traces.append(tr)
        if not st.empty:st['block']=f'b{i}';state_parts.append(st)
    c=pd.concat(comps,ignore_index=True) if comps else pd.DataFrame()
    if not c.empty:
        fs.append(px.bar(c,x='block',y='coins_delta',hover_data=['seed','seat','opponent'],title='Fresh paired endpoint: candidate minus control own cash'))
        fs.append(px.bar(c,x='block',y='coin_margin_delta',hover_data=['local_match_score_delta','opponent'],title='Fresh paired endpoint: coin margin; hover for match change'))
    else:
        fs.extend([empty('Paired final cash','No completed endpoint comparisons; not a zero effect'),empty('Paired margin / match','No completed comparisons')])
    if traces:
        tr=pd.concat(traces);p=tr.pivot(index=['block','step'],columns='mode',values='own_cash').reset_index();p['cash_difference']=p['candidate']-p['control']
        fs.append(px.line(p,x='step',y='cash_difference',color='block',title='Continuously evolving cash difference — not summed one-step effects'))
    else:fs.append(empty('Cash trajectories','No completed fresh games'))
    if state_parts:
        st=pd.concat(state_parts);col='max_value_loss' if rid=='17' else 'max_release_value';p=st.groupby(['block','mode'],as_index=False)[col].mean()
        fs.append(px.bar(p,x='block',y=col,color='mode',barmode='group',title='Feature activation across fresh matched blocks — descriptive only'))
    else:fs.append(empty('Fresh-block feature activation','Only archived screen is currently available'))
    for f in fs:f.update_layout(height=460,margin=dict(l=65,r=35,t=85,b=90),legend_title_text='')
    return fs

def dashboard(base,rid,fs):
    base=Path(base);out=base/'outputs'/f'round{rid}'/'dashboard.html'
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture research</title></head><body>',
       f'<h1>Kaggriculture • feature round {rid}</h1><p>Development evidence only. Not an official submission score. Conditional values are not realized cash.</p>']
    for i,f in enumerate(fs):parts.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>');atomic(out,'\n'.join(parts).encode());return out
